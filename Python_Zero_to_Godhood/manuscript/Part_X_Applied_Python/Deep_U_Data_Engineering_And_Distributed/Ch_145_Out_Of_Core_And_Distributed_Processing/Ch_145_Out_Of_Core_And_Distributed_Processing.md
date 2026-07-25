# Chapter 64: Out-of-Core and Distributed Processing

Deep U's chapters so far assumed the data fits in memory: load the DataFrame, operate on its columns.
This closing chapter removes that assumption.
When data is **larger than RAM**, a dataset too big to load, a file that would exhaust memory, the answer is **chunking**: stream the data in pieces, process each piece, and combine the partial results, so that peak memory scales with the *chunk* size, not the *dataset* size.
Measured, aggregating a million-row file in 100,000-row chunks peaks at **10x less** memory than loading it whole, and produces the identical result.

The idea is small and profound, and it is the same idea that scales from one machine to a thousand.
Many computations are **decomposable**: a sum is a sum of partial sums, a count of partial counts, a groupby of combined per-chunk groups.
So you can split the data, aggregate each split independently, and combine, which is exactly what **chunked** processing does across pieces on one machine, and what **distributed** frameworks (Dask, Spark) do across machines.
This chapter is the **Book III seam**: it is where data engineering meets scale, and it closes Deep U by showing that the tools you have learned (groupby, aggregation) extend, unchanged in principle, to data of any size.

**This closes Deep U.**
It builds on chunked/streaming IO, the decomposability of aggregations (Chapter 58), memory-mapped larger-than-RAM arrays (Chapter 103), and columnar formats (Chapter 60, Parquet row groups enable piecewise reads). It is the gateway to the distributed data platforms of **Book III**.

## Section index

- **64.1** Chunked processing: aggregate larger than RAM
- **64.2** Decomposability, and the path to distributed
- **64.3** Measurement: chunked versus whole-file memory
- **64.4** Edges and failure modes
- **64.5** Connections
- **64.6** Exercises
- **64.7** Summary and cross-references

Listings live under `code/ch145/` and are re-executed by `make verify` on both verification interpreters.

---

## 64.1 Chunked processing: aggregate larger than RAM

```python
# code/ch145/l01_chunked.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- whole-file: load everything, then aggregate ---
  whole-file sum per key : {0: 120, 1: 150, 2: 90}
--- chunked: process 3 rows at a time, combine partial sums ---
  number of chunks read  : 3
  chunked sum per key    : {0: 120, 1: 150, 2: 90}
--- the chunked result MATCHES the whole-file result ---
  results identical : True
--- why: a sum is associative, so partial sums combine correctly ---
  key 0: 10+40+70 = 120   (across chunks, summed)
--- the rule ---
  process data larger than RAM in chunks: stream, aggregate each chunk,
  combine partials; peak memory scales with chunk size, not dataset size
```

The **whole-file** approach loads everything (`pd.read_csv(path)`) and aggregates, `sum per key` is `{0: 120, 1: 150, 2: 90}`. It needs enough memory to hold the *entire* dataset.

The **chunked** approach never holds the whole dataset.
`pd.read_csv(path, chunksize=3)` returns an *iterator* of DataFrames, each at most 3 rows, so the 8-row file arrives in 3 chunks (3 + 3 + 2).
For each chunk, compute the per-chunk group sum, and **combine** it into a running partial (`partial.add(chunk_sum, fill_value=0)`).
At no point is more than one chunk in memory, yet the final result, `{0: 120, 1: 150, 2: 90}`, is **identical** to the whole-file result.

The reason it works is stated in the last block: **a sum is associative.**
`key 0` appears in different chunks with values 10, 40, 70; summing them *per chunk* and then adding the partials (`10 + 40 + 70`) gives the same 120 as summing them all at once.
The computation *decomposes*: the whole-dataset sum equals the sum of the per-chunk sums.
So you can process the data in pieces, holding only one piece, and reassemble the exact answer.

This is the fundamental technique for **data larger than RAM**: stream it in chunks, aggregate each chunk, combine the partials.
Peak memory is set by the chunk size (which you choose), not the dataset size (which may be unbounded), so a dataset of *any* size can be aggregated on a machine with *fixed* RAM, as long as the computation decomposes and the *result* fits.

---

## 64.2 Decomposability, and the path to distributed

The chunking technique works for computations that **decompose**, and understanding which do, and how, is the key to scaling.

**Decomposable aggregations** (combine partials trivially):

- **Sum:** add partial sums. **Count:** add partial counts. **Min/Max:** min/max of partial min/maxes.
- **Mean:** *not* directly combinable (you cannot average averages), but decomposable *via* sum and count: keep partial sums and counts, combine each, divide at the end.
- **Groupby aggregations:** combine per-chunk group results (as §64.1 does), because each group's aggregate decomposes.
- **Approximate distinct, quantiles:** decomposable with special data structures (HyperLogLog, t-digest).

**Not (easily) decomposable:**

- **Exact median/quantiles:** need the whole distribution (approximations decompose).
- **Sort:** needs all the data (external merge sort chunks it, but it is not a simple combine).
- **Operations needing global context:** a computation where each row depends on all others (some window functions, global ranks) does not chunk trivially.

The **path to distributed** is the same decomposition, one step further.
Chunked processing splits data into pieces and processes them *sequentially* on one machine.
**Distributed** processing (Dask, Spark) splits data into partitions and processes them *in parallel* across many machines, then combines, the identical split-aggregate-combine, but the pieces run *concurrently* on different nodes.
This is **MapReduce**: *map* an operation over partitions (per-partition aggregates), *reduce* the partial results into the final answer (combine).
So the mental model scales seamlessly: a decomposable computation runs chunked on one machine (memory-bounded) or distributed across many (scale-bounded), with the same structure, split, aggregate each part, combine.

The tools embody this:

- **pandas `chunksize`:** sequential chunks on one machine (this chapter).
- **Parquet row groups** (Chapter 60): a file is stored in row groups you can read and process one at a time, chunking built into the format.
- **Dask:** a pandas-like API that runs partitioned operations lazily, on one machine's cores or a cluster, out-of-core and parallel.
- **Polars:** a fast DataFrame with streaming (out-of-core) execution.
- **Spark:** distributed DataFrames across a cluster, for data far beyond one machine.

The rule: **for data larger than RAM, decompose the computation, chunk on one machine, and distribute across many when needed, all the same split-aggregate-combine.** Recognizing whether your computation decomposes (and how, sum/count for mean, special structures for distinct) is the skill that makes data scale.

---

## 64.3 Measurement: chunked versus whole-file memory

**Methodology.** `code/ch145/bench_chunked.py`.
Aggregating (group sum) a 1,000,000-row CSV whole-file versus in 100,000-row chunks, comparing peak memory (`tracemalloc`).
CPython 3.13.5, pandas 2.2.3.

| aggregate 1,000,000 rows | peak memory | |
|---|---|---|
| whole-file | 55 MB | 1x |
| chunked (100,000-row chunks) | 5 MB | **10x less** |

Chunked processing peaks at **10x less** memory (11x on 3.14.6), and produces the *same* result.
The whole-file load holds all 1,000,000 rows; the chunked version holds at most 100,000 (one chunk) at a time, so its peak is set by the chunk size, and 100,000 is a tenth of 1,000,000, hence ~10x less.
Make the chunk smaller and the peak drops further (at the cost of more per-chunk overhead); the point is that **peak memory is decoupled from dataset size**.

This is the measurement that makes data scale, and it closes Deep U's arc.
The whole volume has been about processing data *in memory* with the DataFrame's columnar, vectorized operations, and the recurring lesson was "vectorize, never loop" (Chapters 57-63).
This chapter adds the orthogonal scaling dimension: when the data does not *fit* in memory, chunk it, and the *same* vectorized operations (groupby, aggregation) run on each chunk, with the partials combined.
So the two techniques compose: within a chunk, use vectorized operations (fast); across chunks, decompose and combine (memory-bounded).
And the same decomposition scales out to distributed processing (§64.2), so a computation written as chunked split-aggregate-combine runs unchanged in principle from a laptop to a cluster.

This is the **Book III seam**.
**Book III**'s data volumes are large, years of tick data, feature matrices over millions of samples, and they are processed with exactly this pattern: vectorized operations within partitions, decomposed aggregations across them, chunked on one machine and distributed across many.
The order-book system's analytics process data larger than any one machine's RAM by chunking (and distributing) decomposable aggregations, reading Parquet row groups piece by piece, combining partial per-symbol and per-interval results, so a query over the full history runs in bounded memory on one machine or in parallel on a cluster, the §64.1 technique as the foundation of a data platform that scales past RAM.
Deep U's toolkit, DataFrame, groupby, merge, columnar IO, time series, missing data, reshaping, and now chunking/distribution, is the complete grammar of data engineering, and its two governing principles are *vectorize* (within memory) and *decompose* (beyond it).

---

## 64.4 Edges and failure modes

**Only decomposable computations chunk trivially.** §64.2.
Sum, count, min/max, and groupby aggregates combine easily; mean needs sum + count; exact median/quantiles and sort do not decompose simply (use approximations or external algorithms). Know whether your computation decomposes before chunking.

**The result must fit in memory.** §64.1.
Chunking bounds the *input* memory, but the *combined result* (the aggregate) must still fit. A groupby with billions of distinct keys produces a huge result that chunking does not help; the result, not just the input, must be bounded.

**Chunk size trades memory against overhead.** §64.3.
Smaller chunks use less peak memory but incur more per-chunk overhead (more iterations, more partial combines). Tune to the memory budget; there is no universally right size.

**Combining partials must be correct.**
The combine step must match the aggregation's algebra: sums add, counts add, means combine via sum/count (not by averaging averages), maxes take the max. A wrong combine gives a wrong result silently. This is the most common chunking bug.

**Mean of means is wrong.**
Averaging per-chunk means (unless chunks are equal-sized) gives the wrong overall mean. Combine sums and counts, then divide. This is the canonical decomposition mistake.

**Prefer purpose-built tools for real scale.** §64.2.
Hand-rolled chunking is fine for simple aggregations, but for complex out-of-core or distributed work, use Dask, Polars, or Spark, which handle partitioning, spilling, parallelism, and fault tolerance correctly. Do not reimplement a distributed engine.

**Streaming formats help.**
Reading a whole CSV to chunk it still parses text; Parquet row groups (Chapter 60) let you read and process natural chunks efficiently, and columnar formats support reading only needed columns per chunk. Prefer chunk-friendly formats for large data.

**State across chunks needs care.**
A computation that carries state between chunks (a running total, a time-series window spanning chunk boundaries) must thread that state correctly, and window operations at chunk edges are a classic source of bugs (a rolling window that resets at each chunk boundary is wrong).

---

## 64.5 Connections

**Backward.**
Chunked aggregation relies on the decomposability of groupby aggregations (Chapter 58). It is the out-of-core counterpart to memory-mapped larger-than-RAM arrays (Chapter 103, the same "data bigger than RAM" problem, solved by mapping vs chunking). Parquet row groups (Chapter 60) are chunking built into the format. Within a chunk, vectorized operations (Chapters 57-63) apply. The associativity of sum is the algebra of reductions (Chapter 101).

**Forward.**
Dask (out-of-core/parallel pandas), Polars (streaming), and Spark (distributed) are the tools that scale this pattern, the rest of **Deep U** / distributed. MapReduce and the split-aggregate-combine model are distributed-computing foundations. Approximate aggregations (HyperLogLog, t-digest) decompose non-trivial computations. This is the seam to **Book III**'s data-at-scale platform.

**Across books.**
Out-of-core and distributed processing are how **Book III** handles data that dwarfs one machine's RAM: historical market data spanning years, feature computations over billions of rows, model training data. The pattern, decompose, chunk on one machine or partition across a cluster, aggregate each piece, combine, is the architecture of the data platform, and it is *continuous* with the in-memory DataFrame work of the rest of Deep U (the same vectorized operations run within each chunk/partition). The order-book system processes its full history by chunking and distributing decomposable aggregations, reading Parquet piece by piece, and reaches for Dask/Spark when the scale demands a cluster, so no computation is bounded by a single machine's memory, the §64.3 technique scaled from chunk to cluster. Deep U closes here, at the seam where **Book II**'s data engineering becomes **Book III**'s data platform.

---

## 64.6 Exercises

**1. Chunk an aggregation.** Reproduce §64.1: aggregate a file whole and in chunks, and confirm the results match. Explain why the sum decomposes (associativity) and how the partials combine.

**2. Measure the memory.** Reproduce §64.3. Confirm chunked processing uses far less peak memory. Vary the chunk size and show the peak scaling with it. Explain the memory/overhead trade.

**3. Decompose a mean.** Compute a mean over chunks *incorrectly* (average of per-chunk means) and *correctly* (combine sums and counts, then divide). Show they differ for unequal chunks. Explain why mean-of-means is wrong.

**4. What does not chunk.** Identify a computation that does *not* decompose simply (an exact median, a global rank) and explain why. Then describe how an approximation or external algorithm chunks it.

**5. The design question.** Chunked (one machine) and distributed (many machines) processing are the same split-aggregate-combine on decomposable computations. Argue why this decomposition is the foundation of data-at-scale, using §64.3, and how it connects the in-memory DataFrame work (Chapters 57-63) to distributed platforms. What makes a computation scalable?

---

## 64.7 Summary and cross-references

- **Data larger than RAM** is processed by **chunking**: stream it in pieces (`pd.read_csv(chunksize=...)`), aggregate each chunk, and **combine** the partial results. Peak memory scales with the **chunk** size, not the **dataset** size.
- This works for **decomposable** computations: **sum** (add partials), **count** (add), **min/max**, **groupby** aggregates (combine per-chunk groups), and **mean** *via* sum and count. Exact median/quantiles and sort do not decompose simply.
- **Measured:** aggregating 1,000,000 rows in 100,000-row chunks peaks at **10x less** memory than whole-file, with the identical result.
- **Chunking scales to distributed:** the same split-aggregate-combine runs sequentially in chunks on one machine or in parallel across many (Dask, Spark, MapReduce). The two techniques compose: vectorize within a chunk, decompose across chunks.
- **Edges:** the *result* must fit in memory (not just the input); combine correctly (mean-of-means is wrong); tune chunk size; use Dask/Polars/Spark for real scale; Parquet row groups enable efficient chunking; cross-chunk state (windows) needs care.

**Cross-references.** Decomposable groupby aggregations → Chapter 58. Larger-than-RAM arrays (memmap) → Chapter 103. Parquet row groups (chunking in the format) → Chapter 60. Vectorized within-chunk operations → Chapters 57-63. Reduction algebra (associativity) → Chapter 101. Dask/Polars/Spark, MapReduce, approximate aggregations → the rest of Deep U / distributed. Book III data platform → Deep U / Book III. This closes Deep U (Data Engineering and Distributed).
