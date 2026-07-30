# Chapter 91: Streaming: The Data You Never Hold

Chapter 89 priced every representation that holds the data; Chapter 90 spent memory to buy time. This chapter is the remaining move: **refuse to hold the data at all**. A generator produces each value on demand and forgets it as the next is requested, so the same reduction that peaks at **40,448,200 bytes** over a list peaks at **464** over a generator expression, at any `n`, forever.

That is not a smaller constant. It is a different exponent: O(n) memory became O(1), which fulfils Chapter 87's promise that streaming changes the **memory** exponent rather than the time one. And it composes with laziness: a pipeline over a billion potential items produced exactly **13** of them below, because demand flows backwards and the answer only needed five.

The honest half is that streaming is not free where Chapter 90's cache was not free: each element of each Python-level stage costs a frame resume, measured at about **16 ns** per element per stage, and the generator form of a hot reduction is **1.16x slower** than the list comprehension it replaces. Memory and time trade in both directions, and this chapter is the other direction.

**This is a Deep K chapter.**
Deep F owns what a generator *is*, frames, `yield`, and the iterator protocol; Chapter 33 owns the `itertools` toolbox. This chapter owns the decision: when the container should not exist, what the answer's state actually bounds, and what the per-stage tax costs.

## Section index

- **91.1** What streaming changes, counted
- **91.2** The decision: size the state to the answer
- **91.3** Measurement: the saving, the tax, and the depth
- **91.4** Edges and failure modes
- **91.5** Connections
- **91.6** Exercises
- **91.7** Summary and cross-references

Listings live under `code/ch172/` and are re-executed by `make verify` on both verification interpreters.

---

## 91.1 What streaming changes, counted

```python
# code/ch172/l01_streaming_counted.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- the memory exponent, measured at two sizes ---
  sum over a LIST of squares      : peak grows 2.0x when n doubles
  sum over a GENERATOR of squares : peak grows 1.0x when n doubles
  generator peak is under 1% of the list's at n=100,000 : True
  the list's memory is O(n); the generator's is O(1). streaming changes
  the MEMORY exponent, and no time optimisation in this volume does that
--- a generator's size does not depend on what it will yield ---
  getsizeof(generator over 10 items) == getsizeof(over 10**9) : True
  the generator stores a frame and a position, never the data
--- laziness, counted at the source ---
  pipeline: source(10**9) -> keep multiples of 3 -> first 5
  result           : [0, 3, 6, 9, 12]
  items the source produced : 13  (of 1,000,000,000 possible)
  demand flows backwards: nothing is computed until something downstream
  asks, so an early exit is a free optimisation over the whole pipeline
--- the price: one pass, then nothing, silently ---
  first pass  : [0, 1, 4, 9, 16]
  second pass : []   <- not an error
  len(generator) : TypeError: object of type 'generator' has no len()
  a stream is a position, not a container: no len, no indexing, no
  second pass, and exhaustion is SILENT, which is a real bug class
--- the schedule: item at a time, not stage at a time ---
  execution order : parse 0, keep  0, parse 1, keep  1, parse 2, keep  2
  each item runs the WHOLE pipeline before the next is produced, so the
  data in flight is one item per stage, however long the input
```

**The first block is the exponent claim, measured by the doubling method.**
Chapter 87 measured time at two sizes and read off the exponent; this block does the same to peak allocation. The list's peak doubles when `n` doubles; the generator's does not move. This is the measurement Chapter 89 conceded it could not show in a table of materialised representations, because a generator has no size that depends on the data, which the second block confirms directly: the generator over `10**9` items is exactly as large as the one over 10.

**The laziness block is why streaming composes with early exit.**
Thirteen items produced, out of a possible billion. Each stage pulls from the one before it only when pulled from, so `islice`'s decision to stop propagates backwards through the whole pipeline without any stage being told. An unbounded source is not a special case in this model; it is the ordinary case, and every finite bound in the pipeline is downstream of it.

**The price block is the correctness half of the trade.**
A stream is a position, not a container. The second pass is empty **and not an error**, which converts a performance decision into a bug class (§91.4). `len` fails loudly, which is the polite failure; exhaustion fails silently, which is the one that ships.

**And the schedule block is the fact that makes constant memory possible.**
`parse 0, keep 0, parse 1, keep 1`: the pipeline is depth-first per item, not breadth-first per stage. At no point does a stage's full output exist; what exists is one item per stage. That schedule is also why the per-stage tax in §91.3 is paid per element, and why exceptions surface at the consumer rather than the producer (§91.4).

---

## 91.2 The decision: size the state to the answer

Chapter 88 chose the container from the access pattern. This chapter's decision is prior to that one: **whether there should be a container at all**, and the criterion is how much state the *answer* needs, not how much data the *input* has.

| the answer needs | state | tool |
|---|---|---|
| a reduction: sum, count, min, `any` | O(1) | genexp into a builtin |
| the most recent N | O(N) | `deque(maxlen=N)` |
| the top K | O(K) | `heapq.nlargest(K, stream)` |
| the distinct values | O(distinct) | `set` |
| counts per key | O(keys) | `collections.Counter` |
| a sorted result | O(n) | `sorted()`, materialise |
| more than one pass | O(n), or re-read | `list()`, or reopen the source |

**The table's shape is the argument.**
Most useful answers are far smaller than their inputs: an average is one number, the top ten is ten, the distinct-user count is the user count and not the event count. Streaming works whenever the state column is bounded, and the input's size, even its finiteness, never appears in the decision. The rows that force materialisation are the ones whose *answer* is as large as the data, a sort, or a second pass over the same values.

**The second question is whether the source comes back.**
A list can be iterated again; a file can be reopened; a socket, a subprocess pipe, and this morning's market cannot. When the source is re-iterable, materialising is an optimisation you can decline and later revisit. When it is not, the O(n) rows of the table are not options at scale, and the design question becomes which O(K) summary to keep, which is exactly how **Book I**'s side of the shared system treats the tick stream: the stream never becomes a list in either language, and everything that persists, bars, book snapshots, running risk, is a bounded aggregate the stream flowed through.

**Fusion is part of the decision, not a separate trick.**
Stages exist for the reader; the machine pays per stage (§91.3). The working shape is: compose freely at the boundaries of a program where clarity is worth nanoseconds, and in the measured hot path (Chapter 86) collapse the chain into one comprehension or loop, which keeps the O(1) memory and drops the stacked resumes.

---

## 91.3 Measurement: the saving, the tax, and the depth

**Methodology.** `code/ch172/bench_streaming.py`.
`min` of 7 batches. Memory by `tracemalloc` peak.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**The saving: one reduction over a million squares.**

| form | peak bytes |
|---|---|
| `sum([i*i for i in range(N)])` | 40,448,200 |
| `sum(i*i for i in range(N))` | **464** |
| three-stage generator pipeline | 856 |

The list's peak is Chapter 89's arithmetic arriving all at once, a million boxed results plus the container. The generator's 464 bytes are a frame and a position, and the three-stage pipeline's 856 are three of them. The gap is about **87,000x**, it widens with `n`, and it is the entire reason this chapter exists.

**The tax: the same reduction, timed.**

| 100,000 elements | time | vs list comp |
|---|---|---|
| `sum([x*x for x in data])` | 1.89 ms | 1.00x |
| `sum(x*x for x in data)` | 2.20 ms | **1.16x** |
| explicit `for` loop | 2.08 ms | 1.10x |

The genexp avoids a 4 MB allocation and still loses, because every element pays a generator resume where the list comprehension pays an append into Chapter 77's inlined frame. Streaming trades time for memory, the mirror image of Chapter 90's cache, and at this size the right side of the trade is decided by whether 4 MB matters more than 0.3 ms. At a hundred times this size, the list's side of the ledger is 400 MB, and it usually does.

**The depth: where the tax accrues.**

| pipeline shape, 100,000 elements | time | vs fused |
|---|---|---|
| fused: `sum(x + 3 for x in data)` | 1.98 ms | 1.00x |
| 1 generator stage | 2.00 ms | 1.01x |
| 3 generator stages | 5.16 ms | **2.61x** |
| 6 generator stages | 10.7 ms | **5.39x** |
| 3 `map`(C callable) stages | 5.67 ms | 2.87x |

The tax is linear in depth, about **16 ns per element per stage** on this machine, and the `map` row is the measurement that kills a folk theorem: replacing generator stages with `map` and a C-implemented callable does not remove the tax, because a call per element is a call per element (Chapter 55). What removes it is **fusion**, the first row: the same three operations in one stage cost a third of three stages. The escape that removes the per-element cost entirely, handing the whole stream to code that consumes buffers, is Chapter 92's subject.

---

## 91.4 Edges and failure modes

**Exhaustion is silent.** §91.1.
A function handed an iterator that consumes it twice gets a full first pass and an empty second one, no exception. The same function works when tests pass it a list. Accept an iterable and iterate once; if two passes are needed, materialise explicitly at the boundary.

**`bool()` of a generator is always true.**
`if items:` on a generator takes the branch even when the generator will yield nothing, because truthiness falls back to existence. The emptiness of a stream is unknowable without consuming its first element, which is what `next(it, sentinel)` is for.

**A generator body does not run at call time.**
Arguments are validated, files are opened, and exceptions are raised at the first `next()`, not at the call. An API that should fail fast needs an eager wrapper that validates and returns an inner generator, or the error surfaces far from its cause.

**Cleanup happens at exhaustion or at collection, whichever comes first.**
A `with` block inside a generator releases its resource when the generator is exhausted, explicitly `close()`d, or garbage-collected. An abandoned, half-consumed generator holds its file open until the collector finds it, which is prompt under refcounting and not prompt in a cycle (Deep B). Own the lifetime: `close()` it, or drive it with `contextlib.closing`.

**`itertools.tee` is not a free second pass.**
`tee` buffers the gap between its consumers. Two consumers that diverge by the whole stream have built the list anyway, in a costume. `tee` is for consumers that stay close; for a true second pass, re-read the source or materialise deliberately.

**`groupby` groups adjacent runs only.**
`itertools.groupby` on an unsorted stream returns a *wrong answer*, not a slow one, one group per run of equal keys. Sorting first materialises (§91.2's table, last rows); for unsorted streams the O(keys) answer is a `Counter` or a dict of accumulators.

**One accumulating stage repeals the whole guarantee.**
A `set`, `Counter`, or `sorted` in the middle of a pipeline holds state proportional to the data, and the pipeline's memory is its **widest stage**. The O(1) claim is a claim about every stage, and it is worth stating which stage is the widest in a comment, because the next edit will not know.

**Exceptions surface at the consumer.**
The schedule that gives constant memory (§91.1) also means a producer's exception is raised mid-`sum`, three stages away from its cause, with generator frames interleaved in the traceback. Laziness moves failures in time and place; that is a debugging cost, and it is the streaming analogue of Chapter 90's staleness.

**And the tax is real.** §91.3.
Sixteen nanoseconds per element per stage buys nothing when the data already fits comfortably in memory and is consumed twice. A list is not a defeat; it is the right call whenever the O(n) is cheap and re-iteration or indexing is wanted. Stream because the state table says you can, not as a style.

---

## 91.5 Connections

**Backward.**
The memory arithmetic that makes the list's column grow is Chapter 89; the doubling method reading the exponent off two peaks is Chapter 87. The per-stage tax is Chapter 55's call overhead and Deep F's frame-resume mechanics; the inlined comprehension frame it competes with is Chapter 77. The `itertools` tools, `islice`, `tee`, `groupby`, `chain`, are Chapter 33 (Deep Q); `heapq.nlargest` and `deque(maxlen)` as bounded aggregates are Chapter 88's containers doing streaming duty. Laziness as an interpreter property was first measured in Chapter 85's benchmark traps.

**Forward.**
When even the fused per-element cost is the bottleneck, handing the stream to a consumer of buffers, NumPy, a C routine, a socket, is Chapter 92, the volume's closing decision. Generators as *coroutines*, streaming in time rather than in space, are Deep F's second half and the foundation of Deep H's `asyncio`. File iteration, the most-used stream in Python, is Deep R.

**Across books.**
The shared system's data plane is a stream in both languages: **Book I** pulls ticks through a ring buffer sized in kilobytes while Book II pulls bars through generators sized in one frame each, and neither side ever holds the day in memory. The persistent artifacts, bars, snapshots, risk, are all rows from §91.2's table with K small. The two implementations disagree about the cost of a stage, nanoseconds in C++, tens of nanoseconds in Python, and agree completely about the shape, which is this volume's recurring lesson: the exponent, this time the memory exponent, is the portable part.

---

## 91.6 Exercises

**1. Measure a conversion.** Take a batch script you own that builds a list it consumes once, convert it to a generator pipeline, and report `tracemalloc` peak before and after, and wall time before and after. State which side of the trade you took and why.

**2. Price your stages.** Reproduce §91.3's depth table and estimate your machine's per-element per-stage tax in nanoseconds. Then fuse the six-stage pipeline into one stage and confirm the prediction.

**3. Top-K two ways.** Find the ten largest of ten million streamed values with `sorted(...)[-10:]` and with `heapq.nlargest(10, ...)`. Report peak memory and time for both, and relate the results to §91.2's state column.

**4. Break `groupby`.** Group an unsorted stream of keys with `itertools.groupby` and show the wrong answer. Fix it twice: by sorting (report the memory bill) and by a dict of accumulators (report the bill in `O(keys)`).

**5. The tee trap.** Feed one generator to two consumers via `itertools.tee`, force them to diverge by `d` items, and measure `tee`'s buffer at `d = 10`, `10,000`, and the full stream. Find the divergence at which re-reading the file would have been cheaper.

**6. The design question.** `range` is lazy but is not a generator: it supports `len`, indexing, `in`, and repeated iteration, all in O(1) memory. Dict views re-iterate; file objects do not. Build the taxonomy: what a lazy *sequence* must be able to do that a lazy *stream* cannot (recompute any element from its position), why files fail that test and `range` passes it, and where `memoryview` (Chapter 79) sits. Conclude with why "iterable" is the correct public-API type and "iterator" almost never is.

---

## 91.7 Summary and cross-references

- **Streaming changes the memory exponent**: the same reduction peaks at 40,448,200 bytes over a list and **464 bytes** over a generator, a gap that grows with `n`. Measured by the doubling method: the list's peak scales 2.0x when `n` doubles, the generator's 1.0x.
- **Demand flows backwards**: a pipeline over `10**9` potential items produced **13** because the answer needed five. Early exit propagates through every stage for free, and unbounded sources are the ordinary case, not a special one.
- **The decision is the state table**: size the state to the **answer**, O(1) for reductions, O(K) for top-K, O(keys) for counts, and only a sort or a second pass needs O(n). The second question is whether the source can be read again.
- **The price is semantic**: one pass, no `len`, `bool` always true, silent exhaustion, deferred errors, cleanup at collection, and exceptions surfacing at the consumer. Every one of these is a shipped-bug class, not a footnote.
- **The tax is measured**: ~16 ns per element per Python stage; the genexp form of a hot reduction is 1.16x the list comprehension; six stages are 5.4x one. `map` with a C callable does not remove it; **fusion** does.
- **`tee` buffers the divergence, `groupby` needs adjacency, and one accumulating stage repeals the O(1) guarantee**: a pipeline's memory is its widest stage.
- **A list is not a defeat.** Stream when the state table allows it and the data is large or unbounded; materialise when O(n) is cheap and re-use is wanted.

**Cross-references.** Memory arithmetic → Chapter 89. The doubling method → Chapter 87. Caching, the opposite trade → Chapter 90. Call overhead → Chapter 55. Comprehension frames → Chapter 77. Generator mechanics → Deep F. `itertools` → Chapter 33. Bounded aggregates → Chapter 88. Buffers → Chapter 79. The escape decision → Chapter 92.
