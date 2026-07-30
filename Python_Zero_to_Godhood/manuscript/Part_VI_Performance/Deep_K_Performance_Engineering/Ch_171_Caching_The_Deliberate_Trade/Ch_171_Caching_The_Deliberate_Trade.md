# Chapter 90: Caching: The Deliberate Trade

Chapter 89 measured the trade Python makes accidentally: memory spent on object headers nobody asked for. This chapter is the same trade made **on purpose**. A cache spends memory to buy back repeated work, and it is the only optimisation in this volume that changes a cost model rather than a constant: a recursive function that revisits its own subproblems drops from **1,028,457 calls to 29** when the revisits stop being paid for.

It is also the optimisation most often applied without measurement, and the numbers cut both ways. A cache hit replaces 23.5 us of computation with **19.6 ns** of lookup, a factor of about **1,200**. The same machinery applied to a trivial function makes it **1.35x slower**, and applied to a workload that never repeats itself it is pure overhead, measured at 3% below.

The governing quantity is not in the function at all. It is the **hit rate**, a property of the access pattern, and it caps the win by simple arithmetic: at 50% hits no cache on earth beats 2x, however expensive the miss.

**This is a Deep K chapter.**
Chapter 34 (Deep Q) owns `functools.cache` and `lru_cache` as tools, and Chapter 13 owns `cached_property`. This chapter owns the decision: when a cache pays, what it costs in memory and staleness, and the ledger to read before believing in one.

## Section index

- **90.1** What a cache changes, counted
- **90.2** The decision: two questions and a place to put it
- **90.3** Measurement: the win, the loss, and the sweep between them
- **90.4** Edges and failure modes
- **90.5** Connections
- **90.6** Exercises
- **90.7** Summary and cross-references

Listings live under `code/ch171/` and are re-executed by `make verify` on both verification interpreters.

---

## 90.1 What a cache changes, counted

```python
# code/ch171/l01_what_a_cache_changes.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- the same function, counted, with and without a cache ---
     n   naive calls   cached computations
    18         8,361                    19
    23        92,735                    24   x11.1 for +5
    28     1,028,457                    29   x11.1 for +5
  each +5 multiplies the naive count by ~11; the cached count is n + 1.
  the cache did not shave the constant, it CHANGED THE EXPONENT
--- cache_info: the ledger a caching decision is read from ---
  after fib(28)      : CacheInfo(hits=26, misses=29, maxsize=None, currsize=29)
  after fib(33) next : CacheInfo(hits=32, misses=34, maxsize=None, currsize=34)
  the second call cost 5 new computations, not 33: the cache is doing
  cross-call work, which no other optimisation in this volume does
--- the break-even, as arithmetic ---
  model: compute costs 1000 ns, a hit costs 50 ns
   hit rate  effective ns/call   speedup
         0%               1000      1.0x
        50%                525      1.9x
        90%                145      6.9x
        99%                 60     16.8x
  the speedup is capped by the hit rate, not by the cost ratio: at 50%
  hits no cache can beat 2x, however expensive the miss
--- eviction: one entry over the bound, counted ---
  8 keys, maxsize=8 : CacheInfo(hits=72, misses=8, maxsize=8, currsize=8)
  9 keys, maxsize=8 : CacheInfo(hits=0, misses=90, maxsize=8, currsize=8)
  one extra key took the hit rate from 90% to ZERO: a cyclic scan is LRU's
  worst case, because the entry evicted is always the next one needed
```

**Everything here is counted, not timed, because caching's claims are structural.**
The naive count multiplies by ~11 for every +5 of input, which is Chapter 87's exponential signature; the cached count is `n + 1`, one computation per distinct argument. This fulfils Chapter 87's promise exactly: caching changes the exponent **by removing repeated work**, and where there is no repeated work it changes nothing.

**`cache_info()` is the ledger, and reading it is the discipline.**
Hits, misses, bound, and occupancy, maintained for free. A cache that is believed in rather than read is the performance equivalent of an unverified benchmark (Chapter 85): the second block shows the read that justifies the cache in one line, five new computations for a call that naively costs 33.

**The cross-call property is what makes caching different in kind.**
Every other optimisation in this volume makes one pass cheaper. A cache moves cost **between** calls, which is why it is also the only optimisation with state, and therefore the only one with staleness, growth, and eviction as correctness concerns. The rest of the chapter is about exactly those.

**And the eviction block is the sharpest edge in the chapter.**
Ten rounds over eight keys under `maxsize=8`: 90% hits. The same rounds over **nine** keys: zero. A cyclic scan one entry over the bound is LRU's worst case, because the entry just evicted is always the next one needed. Hit rate is not a smooth function of cache size; it can fall off a cliff.

---

## 90.2 The decision: two questions and a place to put it

Chapter 88 chose a container by asking what you do to it most often. A cache is a container decision by another name, a `dict` keyed by arguments, and its two questions are:

**1. Will the same question be asked again, with the same answer?** That is the hit rate, and it is a property of the **workload**, not the function.
**2. Can you afford to keep the answers?** That is §90.3's 134 bytes per entry, held for the cache's lifetime, win or lose.

Three preconditions gate the whole discussion: the function must be **deterministic in its arguments** (a cache elides calls, so anything else changes behaviour), the arguments must be **hashable**, and the key space must be **bounded**, either naturally or by `maxsize`.

Then the choice is where to put it, and the options form a ladder of lifetimes:

| where | tool | lives for | invalidation |
|---|---|---|---|
| before the loop | a `dict` built once | the loop | rebuild it |
| function boundary | `functools.cache` / `lru_cache` | the process | `cache_clear()`, all or nothing |
| per instance | `functools.cached_property` | the instance | `del obj.attr`, per instance |
| outside the process | Redis, files, a CDN | your policy | **the hard problem** |

**The first row is underrated and the last is out of scope.**
Hoisting a computation out of a loop into a prebuilt dict is caching without a single caching tool, and it should be the first thing tried: the lifetime is obvious, the invalidation is free, and the memory is released when the loop ends. The last row is where invalidation becomes a distributed-systems problem, and this book stops at the process boundary.

**`lru_cache(maxsize=N)` against `cache`: the bound is the decision.**
`cache` is `lru_cache(maxsize=None)`: a plain dict, cheapest per hit, and it grows for the life of the process. The bounded form adds eviction bookkeeping per entry and an answer to "how big can this get". §90.1's eviction block is the caveat: a bound just below the working set is worse than no cache at all, so the bound must come from the access pattern, not from a round number.

**And staleness is the price that is not in any table.**
A cache is a bet that the answer has not changed. `lru_cache` offers no TTL and no per-key invalidation, deliberately (§90.6, exercise 6), so the standard-library tools are for answers that **cannot** go stale: pure functions of their arguments. The moment the answer depends on anything else, time, a file, a market, the invalidation policy is the design, and the cache is the easy part.

---

## 90.3 Measurement: the win, the loss, and the sweep between them

**Methodology.** `code/ch171/bench_caching.py`.
`min` of 7 batches (15 for the fast rows, 5 for the workloads).
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**The win: an expensive pure function.**

| `curve(1000)`, ~23.5 us of arithmetic | time | ratio |
|---|---|---|
| recompute | 23,532 ns | 1.00x |
| cache hit | 19.6 ns | **~1/1,200** |

A hit costs what a C-implemented call plus a dict probe costs, about 20 ns, and that figure is the **floor for every cache hit** regardless of what was cached. The ratio is therefore not a property of the cache; it is the cost of the miss divided by a constant. Caching 23.5 us of work returns 1,200x. Caching 100 ns of work would return 5x. And caching work cheaper than the floor returns a loss, which is the next table.

**The loss: a trivial function.**

| `double(21)` | time | vs direct |
|---|---|---|
| direct call | 12.1 ns | 1.00x |
| via cache hit | 16.4 ns | **1.35x** |

The cache made the function slower, on a **hit**. Key construction, a hash, and a probe cost more than doubling an integer, and Chapter 55's call overhead is paid either way. This is Chapter 85's lesson wearing a new costume: an optimisation is a measurement, not a vibe, and the same decorator is a 1,200x win on one function and a 1.35x loss on another.

**The sweep: the same function, the same cache, four workloads.**

| 10,000 calls of ~3.9 us each | workload time | vs no cache | speedup cap (1/(1-h)) |
|---|---|---|---|
| no cache | 39.4 ms | 1.00x | — |
| cached, 0% hits | 40.5 ms | **1.03x slower** | 1x |
| cached, 50% hits | 20.0 ms | 1.97x faster | 2x |
| cached, 90% hits | 4.3 ms | 9.2x faster | 10x |
| cached, 99% hits | 0.58 ms | 67x faster | 100x |

Nothing about the function changed between rows; only the key sequence did. The measured speedups sit just under the arithmetic cap from §90.1's model, 1.97 under 2, 9.2 under 10, 67 under 100, with the gap being the per-call machinery. And the first row is the one to memorise: **a cache on a workload that never repeats is a measured 3% loss**, every call paying the probe, the compute, and the store.

**The stake: what the entries cost.**

| `functools.cache`, int keys and int results | bytes |
|---|---|
| 100,000 entries, `tracemalloc` peak | 13,448,624 |
| per entry | **134** |

This is the memory side of the deliberate trade, and it is held for as long as the cache lives. A hundred thousand entries is 13 MB; ten million is over a gigabyte, which is Chapter 89's arithmetic arriving at a decorator. An unbounded cache's ceiling is the number of distinct keys the workload can produce, and if you cannot state that number, the cache needs a `maxsize`.

**Book I**'s side of the shared system caches derived analytics, per-symbol volatility over a fixed window, keyed by `(symbol, bar)`, because the backtester asks for the same bar thousands of times: a 99%-row workload. It never caches anything keyed by the tick stream, because ticks do not repeat: that is the 0%-hits row, and the packed tick buffer (Chapter 89) is already the right representation for data that is seen once. Same system, both rows of the sweep, chosen by access pattern.

---

## 90.4 Edges and failure modes

**An unbounded cache is a leak wearing a decorator.** §90.3.
`functools.cache` grows with every distinct argument for the life of the process. Either the key space is provably bounded, or the cache gets a `maxsize`, or the growth is someone's pager.

**`lru_cache` on a method keeps every instance alive.**
`self` is part of the key, so the cache holds a strong reference to every instance ever called. The instance-lifetime tool is `cached_property` (Chapter 13); the function-lifetime tool is a module-level function taking the *values* the method used.

**Cached results are shared, not copied.**
A cached function that returns a list returns **the same list** to every caller. One caller's `append` is now in everyone's result, and the corruption is invisible at the cache. Cache immutable values, or treat every cached result as frozen.

**A cache elides calls, so side effects happen once.**
Logging, counters, network requests inside a cached function occur on misses only. If the function has any observable effect beyond its return value, caching it changes the program's behaviour, not just its speed.

**Keys are equality-based, and equality crosses types.**
With the default `typed=False`, arguments that compare equal can share an entry: measured on 3.13.5, after `g(1.0)` populates the cache, `g(True)` returns the value computed for `1.0`, because `hash(True) == hash(1.0)` and they compare equal. Whether `1` also collapses into that entry depends on an internal fast path for exact `int` keys, which is precisely the kind of detail not to rely on: if argument **type** matters to the result, pass `typed=True`. Call shape matters too: `f(1, 2)`, `f(1, b=2)`, and `f(b=2, a=1)` are three distinct keys, so a mixed call style quietly multiplies the entries and divides the hit rate.

**A miss does not lock the key.**
The cache's internal state is thread-safe, but two threads missing the same key both compute it, and one result replaces the other. For idempotent pure functions that is wasted work; behind it lies the general dogpile problem, which the stdlib cache deliberately does not solve.

**The bound has a cliff, not a slope.** §90.1.
A cyclic access pattern one key wider than `maxsize` yields a 0% hit rate. If the working set is near the bound, measure `cache_info()` under the real access pattern before trusting the cache at all.

**And the hit has a floor.** §90.3.
About 20 ns of call-plus-probe on this machine. Functions cheaper than the floor get slower when cached, which rules out most attribute access, arithmetic, and formatting, exactly the things that look temptingly hot in a profile (Chapter 86).

---

## 90.5 Connections

**Backward.**
The exponent that caching removes is Chapter 87's subject, and the counting method in §90.1 is its doubling method applied to call counts. The cache-as-container framing is Chapter 88; the memory the entries cost is Chapter 89's arithmetic. The hit's floor is Chapter 55's call overhead plus Deep Q's dict probe. The tools themselves, `cache`, `lru_cache`, `partial`, are Chapter 34 (Deep Q); `cached_property` and its measured 462x are Chapter 13; decorators as a mechanism are Chapter 5.

**Forward.**
Streaming, the refusal to hold data that caching's memory bill might force, is Chapter 91. When neither caching nor streaming closes the gap and the answer is leaving Python, that decision is Chapter 92. Caches under concurrency, and why per-key locking is genuinely hard, return in Deep H's structured-concurrency chapters and Deep L's free-threading treatment.

**Across books.**
The shared system's caching policy was written once and implemented twice: **Book I** memoises the same per-`(symbol, bar)` analytics with a flat array indexed by bar number, which is what a cache becomes when the key space is dense integers, and Book II uses a keyed cache because its key space is sparse. The policy, cache what repeats, never cache the stream, is identical, and it was set by measuring the workload's hit rate, not by preference. The exponent is portable; even the caching decision turns out to be.

---

## 90.6 Exercises

**1. Read a ledger.** Wrap a function from your own code in `lru_cache` and drive it with production-shaped input. Report `cache_info()`, compute the hit rate, and use §90.1's arithmetic to predict the speedup before timing it. Compare.

**2. Find the floor.** Reproduce §90.3's trivial-function loss, then binary-search the compute cost at which caching breaks even on your machine. State the result as "cache nothing cheaper than X ns".

**3. Break the bound.** Reproduce the eviction cliff with a working set of `maxsize + 1`, then show that `maxsize + 1` as the bound restores the hit rate. Plot hit rate against bound for a fixed cyclic workload.

**4. Leak an instance.** Demonstrate that an `lru_cache`-decorated method keeps a deleted instance alive, using `weakref` to observe it, then fix it with `cached_property` and show the weakref dies.

**5. Corrupt a result.** Cache a function returning a list, mutate the result at one call site, and show the mutation appearing at another. Fix it two ways, returning a tuple, and returning a copy, and measure what the copy costs per hit.

**6. The design question.** `lru_cache` offers no TTL, no per-key invalidation, and no size-in-bytes bound, only `maxsize` in entries. Argue why: what a TTL needs that a pure-function cache does not have (a clock is an input, so the function is no longer pure), why per-key invalidation implies the caller can name keys the cache derived internally, and why entry count rather than bytes is the only bound the cache can enforce without walking every stored object (Chapter 89's `getsizeof` problem). Conclude with where each declined feature properly lives.

---

## 90.7 Summary and cross-references

- **A cache spends memory and staleness to buy back repeated work**, and it is the only optimisation in this volume that changes the cost model rather than a constant: fib(28) falls from **1,028,457 calls to 29**, because caching removes repeated work, and where nothing repeats it removes nothing.
- **The hit rate caps the win by arithmetic**: effective cost is `h*hit + (1-h)*miss`, so 50% hits cannot beat 2x regardless of the cost ratio. The hit rate belongs to the workload, not the function.
- **Measured: a hit costs ~20 ns**, the floor for every cache. Against 23.5 us of compute that is ~1,200x; against `double(21)` it is a **1.35x loss on a hit**; against a never-repeating workload it is a measured **3% loss** overall.
- **The sweep confirms the model**: 1.97x at 50% hits, 9.2x at 90%, 67x at 99%, each just under its `1/(1-h)` cap.
- **The stake is 134 bytes per entry** (`int` keys and results), held for the cache's lifetime. State the key space's bound or set `maxsize`.
- **Eviction has a cliff**: a cyclic scan one key over `maxsize` measured a **0% hit rate** where one key fewer measured 90%.
- **The preconditions are absolute**: deterministic in its arguments, hashable arguments, bounded keys. Results are shared, not copied; side effects happen once; `self` in the key pins instances; equal-comparing arguments can share an entry unless `typed=True`.
- **The ladder of lifetimes**: a prebuilt dict for a loop, `cache`/`lru_cache` for a process, `cached_property` for an instance, and outside the process the invalidation policy is the design.

**Cross-references.** The exponent → Chapter 87. Container choice → Chapter 88. Memory arithmetic → Chapter 89. Call overhead → Chapter 55. The tools → Chapter 34. `cached_property` → Chapter 13. Decorators → Chapter 5. Honest measurement → Chapter 85. Streaming → Chapter 91. The escape decision → Chapter 92.
