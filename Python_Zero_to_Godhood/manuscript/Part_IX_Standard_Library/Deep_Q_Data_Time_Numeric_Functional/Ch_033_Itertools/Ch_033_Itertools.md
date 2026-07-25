# Chapter 33: `itertools`

Chapter 9 established that a generator processes a billion items in constant memory where a list would
exhaust the machine. `itertools` is the toolkit that lets you *compose* that laziness into pipelines
without hand-writing a generator for each stage. A filter feeding a map feeding a running sum, over a
million-element source, can run in **548 bytes** of memory with `itertools`, versus **64 megabytes**
for the equivalent code that builds an intermediate list at each stage, a ratio of over 100,000x for
the same result.

That is the headline, but `itertools` is more than a memory optimization. It is a set of composable,
C-speed iterator building blocks, `chain`, `islice`, `groupby`, `accumulate`, `product`,
`combinations`, `tee`, that express common data-processing patterns as declarative pipelines rather than
nested loops with manual bookkeeping. This chapter, part of **Deep Q**, covers the toolkit and the
lazy-composition discipline that makes it powerful.

## Section index

- **33.1** The building blocks
- **33.2** Composition: pipelines that never materialize
- **33.3** Measurement: the memory of laziness
- **33.4** Edges and failure modes
- **33.5** Connections
- **33.6** Exercises
- **33.7** Summary and cross-references

Listings live under `code/ch033/` and are re-executed by `make verify` on both interpreters.

---

## 33.1 The building blocks

`itertools` functions consume iterators and produce iterators. They fall into a few families:

```python
# code/ch033/l01_itertools.py
import itertools as it
```

Verified output (CPython 3.13.5):

```text
--- infinite and slicing: count is unbounded, islice bounds it ---
  islice(count(10, 2), 4): [10, 12, 14, 16]
--- chaining and flattening ---
  chain([1,2],[3,4])      : [1, 2, 3, 4]
  chain.from_iterable     : [1, 2, 3, 4]
--- grouping runs of equal keys (input must be sorted by the key) ---
  groupby('aabbbc')       : [('a', 2), ('b', 3), ('c', 1)]
--- running results and windows ---
  accumulate([1,2,3,4])   : [1, 3, 6, 10]
  pairwise([1,2,3,4])     : [(1, 2), (2, 3), (3, 4)]
--- combinatorics ---
  product([1,2],['a','b']): [(1, 'a'), (1, 'b'), (2, 'a'), (2, 'b')]
  combinations([1,2,3], 2): [(1, 2), (1, 3), (2, 3)]
--- tee: the fix for the two-passes-over-one-iterator problem (Ch 9) ---
  tee gives two independent iterators: [10, 20, 30] [10, 20, 30]
```

The **infinite** iterators (`count`, `cycle`, `repeat`) produce values forever and are bounded by
`islice` or a condition. The **combining** functions (`chain`, `chain.from_iterable`, `zip_longest`)
join iterators. **`groupby`** groups *consecutive* runs of equal keys (so the input must be sorted by
the key first, the single most common `groupby` mistake). The **running** functions (`accumulate`,
`pairwise`) produce cumulative results and sliding windows. The **combinatoric** functions (`product`,
`combinations`, `permutations`) generate arrangements. And **`tee`** splits one iterator into several
independent ones, the fix for Chapter 9's single-pass-iterator problem (it buffers what one branch has
consumed that the others have not, so it trades memory for the second pass).

---

## 33.2 Composition: pipelines that never materialize

The power is in composition. Because each function takes and returns an iterator, you chain them into a
pipeline, and the pipeline is *lazy end to end*: no stage materializes its output, each value flows
through all stages one at a time, pulled by the final consumer. A filter feeding a map feeding a `sum`
holds exactly one value in flight, regardless of how many the source will produce.

This is the same laziness as a generator expression (Chapter 9), but `itertools` gives you named,
C-implemented, composable stages instead of hand-written generators. `chain.from_iterable(files)` flattens
a sequence of files into one stream of lines without concatenating them; `islice(source, start, stop)`
takes a slice of an infinite or expensive source without computing the rest; `groupby(sorted_records,
key)` groups without building a dict of lists. The result reads as a declarative description of the
transformation, and runs in constant memory. The §33.3 measurement is that constant memory made
visible.

---

## 33.3 Measurement: the memory of laziness

**Methodology.** `code/ch033/bench_lazy_pipeline.py`. A filter-map-sum over a million-element source,
computed lazily (`islice`/generator/`sum`, nothing materialized) versus eagerly (build the range list,
the filtered list, the squared list, then sum). Peak memory via `tracemalloc`, which is deterministic.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| pipeline (same result) | peak memory |
|---|---|
| lazy (itertools/generator) | **548 bytes** |
| eager (intermediate lists) | **64,326,184 bytes** |
| ratio | **~117,000x** |

Both compute the identical sum. The lazy pipeline holds **548 bytes**, one value in flight, because
each element is pulled through filter, map, and sum and discarded before the next is fetched. The eager
version holds **64 MB**, because it materializes three large lists: the range, the filtered evens, and
the squares. For a pipeline consumed *once*, the lazy form is strictly better, same result, constant
memory versus O(n).

The discipline this teaches: **build data pipelines lazily and materialize only at the end, and only if
you must.** `itertools` is how you compose the lazy stages without writing a generator for each, and
because the stages are C-implemented, the laziness costs little in speed. Reach for a list only when you
need multiple passes, random access, or a length, exactly Chapter 9's rule, now with a toolkit.

---

## 33.4 Edges and failure modes

**`groupby` on unsorted input.** §33.1. It groups *consecutive* equal keys, so unsorted input produces
fragmented groups. Sort by the key first, or you get one group per run, not one per distinct key.

**Consuming an iterator twice.** An `itertools` result is a single-pass iterator (Chapter 9). Iterating
it again yields nothing. Use `tee` for independent passes (at a memory cost) or materialize to a list.

**`tee`'s hidden memory.** `tee` buffers the values one branch has read that the others have not. If one
branch races far ahead, the buffer grows large. `tee` is not free; for widely-diverging consumers,
materialize instead.

**Infinite iterators without a bound.** `list(count())` never returns. Always bound `count`, `cycle`,
and `repeat` with `islice` or a `takewhile`.

**Eager materialization defeating the point.** Wrapping a lazy pipeline in `list()` when you only iterate
once discards the memory win (§33.3). Materialize only when you need a list's properties.

---

## 33.5 Connections

**Backward.** The iterator protocol and generator laziness `itertools` builds on are Chapter 9, whose
single-pass exhaustion `tee` addresses. The `collections` containers that pair with these pipelines are
Chapter 32. The generator-vs-list memory measurement `itertools` generalizes is Chapter 9's.

**Forward.** `functools` (`reduce`, `partial`, `cache`), the other half of the functional toolkit, is the
next Deep Q chapter. The C implementation that makes these stages fast is **Deep A**.

**Across books.** Lazy `itertools` pipelines are how Book II streams data into **Book III** without
materializing a corpus. A retrieval index build reads documents through `chain.from_iterable(shards)`,
windows them with a generator, and batches them with `islice`, all in constant memory regardless of
corpus size, so the same code builds an index over a thousand documents or a billion. The §33.3
constant-memory property is what makes that scale. **Deep U** owns the pipeline seam.

---

## 33.6 Exercises

**1. Reproduce the memory win.** Run §33.3's benchmark and confirm the lazy pipeline's constant memory
against the eager version's O(n). Then add a stage and show the lazy memory does not grow while the eager
memory does. Explain why.

**2. Group correctly.** Group a list of records by a category with `groupby`, first on unsorted input
(observe the fragmented groups) then on input sorted by the category. Explain the consecutive-runs
semantics.

**3. Split a stream.** Use `tee` to compute both the sum and the maximum of a one-pass iterator in a
single traversal-worth of code. Then measure `tee`'s memory when one branch is consumed fully before the
other, and explain the buffering.

**4. Build an infinite pipeline.** Use `count` and `islice` to produce the first N terms of a sequence
defined by `accumulate`, without ever building a list of all terms. Explain what bounds the otherwise-
infinite computation.

**5. The design question.** `itertools` provides C-implemented iterator combinators rather than leaving
users to write generators. Argue what this buys beyond convenience. Your answer must address the speed of
a C stage versus a Python generator, the composability of named combinators, and why laziness must be
end-to-end (one eager stage in the middle defeats the whole pipeline's memory profile).

---

## 33.7 Summary and cross-references

- **`itertools`** provides composable, C-speed, lazy iterator building blocks: infinite (`count`,
  `cycle`), combining (`chain`, `chain.from_iterable`), grouping (`groupby`, consecutive runs), running
  (`accumulate`, `pairwise`), combinatoric (`product`, `combinations`), and `tee` (independent passes).
- Composed into a **pipeline**, they are **lazy end to end**: no stage materializes, one value flows
  through all stages at a time.
- **Measured:** a lazy filter-map-sum over a million elements peaks at **548 bytes** versus **64 MB** for
  the eager list-building version, the same result at ~117,000x less memory. Build pipelines lazily;
  materialize only at the end.
- **Edges:** `groupby` needs sorted input, iterators are single-pass (use `tee`, which buffers),
  infinite iterators need a bound.

**Cross-references.** Iterators and generator laziness → Chapter 9. `collections` containers → Chapter 32.
`functools` → the next Deep Q chapter. The C implementation → Deep A. The streaming pipeline seam → Deep
U.
