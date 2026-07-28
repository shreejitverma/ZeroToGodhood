# Chapter 85: The Honest Benchmark

Deep H established what the interpreter costs. This volume is about deciding what to do with that knowledge, and it has to begin here, because **a benchmark that produces a number is not a benchmark that produced a measurement**.

There are five ways a Python microbenchmark can measure nothing at all while returning a confident, reproducible, entirely meaningless figure. The clock can be coarser than the operation. The compiler can have evaluated the expression before the timer started. The expression can be lazy and do nothing until consumed. The operation can cache its own result, so runs two through *n* time a dictionary lookup. Or the input can already be in the state the operation produces, so the fast path runs.

None of these requires statistics to detect. Each is a question about **what actually executed**, answerable by counting calls or reading a code object, and this chapter answers all five deterministically.

Then two methodology decisions this book's harness makes, with the evidence rather than the assertion: why the headline statistic is the **minimum**, and why a batch of one operation reports **41 nanoseconds** no matter what the operation is.

**This opens Deep K.**
The volume's subject is the discipline of performance work: measure honestly, find the hot path, prefer the exponent to the constant, and know when to stop.

## Section index

- **85.1** Five ways to measure nothing
- **85.2** What a microbenchmark cannot tell you
- **85.3** Measurement: why min, and why batching
- **85.4** Edges and failure modes
- **85.5** Connections
- **85.6** Exercises
- **85.7** Summary and cross-references

Listings live under `code/ch166/` and are re-executed by `make verify` on both verification interpreters.

---

## 85.1 Five ways to measure nothing

```python
# code/ch166/l01_honest_benchmark.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- 1. the clock is coarser than most single operations ---
  timeit's default timer is perf_counter : True
  its resolution                         : 41.7 ns
  it is monotonic                        : True
  so timing ONE 3 ns operation is noise  : True
  the fix is batching: time N operations and divide, never time one
--- 2. the compiler may have evaluated it already ---
  1024 is a constant of compiled_away    : True
  not_folded has no such constant        : True
  timing `2 ** 10` measures LOAD_CONST, not exponentiation
--- 3. a lazy object does no work until consumed ---
  calls after building map(...)          : 0
  calls after list(...)                  : 5
  the result, for the record             : [0, 2, 4, 6, 8]
--- 4. an operation that caches measures its cache after the first run ---
  bodies executed for 100 calls          : 1
  hits / misses                          : 99 / 1
  a loop of 100 timed calls measured 1 computation and 99 dict lookups
--- 5. the input's state decides which path runs ---
  comparisons to sort already-sorted     : 63
  comparisons to sort shuffled           : 302
  Timsort detects the run and returns early; benchmark the input you have
--- and one thing timeit does FOR you, which is also a distortion ---
  cyclic collector enabled inside timeit : False
  and restored afterwards                : True
  so timed code never pays for a collection your production code will
```

**1. The clock.**
`perf_counter`'s resolution on this platform is **41.7 ns**. An operation costing 3 nanoseconds cannot be timed once; the answer will be the clock. §85.3 shows exactly how that failure looks. The fix is to time `N` operations and divide, which is what `timeit` exists for.

**2. Constant folding.**
`2 ** 10` never runs. The compiler evaluated it and stored `1024` in `co_consts` (Chapter 56), so timing that expression times a `LOAD_CONST`. The check is one line and it is the check to run first on any benchmark whose operands are literals: is the answer already a constant of the code object?

**3. Laziness.**
`map(counted, range(5))` executes the function **zero** times. Only `list(...)` executes it, and then five. Every `map`, `filter`, `zip`, generator expression, `pathlib.Path.glob`, and database cursor has this shape. A benchmark that builds one and does not consume it measures object construction, and reports a spectacular speedup for code that has not run.

**4. Self-caching.**
A hundred calls to an `lru_cache`-wrapped function execute the body **once**. The remaining 99 are dictionary lookups, and the `cache_info()` line proves it: 99 hits, 1 miss. This applies far beyond `functools`: compiled regular expressions are cached by pattern, `str` methods memoise nothing but `re.compile` does, ORMs cache queries, and any object with a `@cached_property` will do this to you silently.

**5. The input decides the path.**
Sorting an already-sorted 64-element list takes **63 comparisons**; sorting a shuffled one takes **302**, nearly five times as many. Timsort detects the existing run and stops. Benchmarking sort with `list(range(n))` measures the detector, not the sort. The general form is that many algorithms have input-dependent fast paths, and a benchmark's input is part of its methodology, not a detail.

**And the distortion `timeit` introduces on your behalf.**
`timeit` disables the cyclic garbage collector while timing and restores it afterwards. This is defensible, a collection landing inside one batch and not another is noise, and it is still a distortion: your production code pays for collections and the benchmark does not. For code that allocates heavily, that gap is not small, and the honest response is to measure with the collector enabled *as well*, not to pretend the number transfers.

---

## 85.2 What a microbenchmark cannot tell you

Even a microbenchmark with none of §85.1's flaws answers a narrower question than people ask of it.

**It cannot tell you whether the code matters.**
A 3x speedup on 0.5% of runtime is a 0.3% program. This is Amdahl's law, and the microbenchmark is structurally incapable of raising it, because it has removed the program. Profiling comes first, which is Chapter 86, and it comes first *for this reason* rather than as a matter of taste.

**It cannot tell you what happens under a real cache and a real allocator.**
A benchmark that touches the same 64 elements 20,000 times runs entirely in L1. The same code in a program that walks a 400 MB working set does not. Microbenchmarks systematically flatter code with poor locality, because they hand it perfect locality for free.

**It cannot tell you about the tail.**
The minimum is the right statistic for "what does this work cost", and it is the wrong statistic for "what will my p99 latency be". Those are different questions with different methodologies: the first wants a quiet machine and a floor, the second wants a loaded machine and a histogram.

**It cannot tell you about warm-up you did not create.**
The interpreter specializes hot call sites (Chapter 76), the allocator's free lists fill, and the branch predictor learns. All of that happens in the first fraction of a benchmark and is deliberately discarded, but a production process that handles one request per second may never reach that state.

**So the useful framing is comparative, not absolute.**
A microbenchmark's honest output is "A is 2.6x B, measured within one interpreter on one machine at one input size". That form transfers. "This takes 34 nanoseconds" does not transfer at all, and this book quotes absolute figures only where they are the point, as in Chapter 78's per-instruction cost, and always with the machine attached.

---

## 85.3 Measurement: why min, and why batching

**Methodology.** `code/ch166/bench_noise_and_warmup.py`.
The first table times one operation in 40 batches of 20,000 and reports every statistic as a multiple of the minimum. The second times the same operation in batches of different sizes and reports how many clock ticks each batch actually spanned.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**The distribution has a floor.**

| statistic | ns/op | x min |
|---|---|---|
| min | 32.8 | 1.00x |
| p25 | 34.3 | 1.04x |
| median | 35.1 | 1.07x |
| mean | 34.8 | 1.06x |
| p90 | 35.8 | 1.09x |
| max | 36.0 | 1.10x |
| RSD | 2.5% | |

Every statistic is at or above the minimum, by construction: none of the things that perturb a measurement, a scheduler preemption, an interrupt, a migration between cores, a competing process, can make work finish *sooner* than it does. So the minimum estimates the work and the mean estimates the work plus the machine.

On this quiet machine the spread is 10% and the choice of statistic barely matters. That is exactly why the harness reports **RSD as a diagnostic rather than as the answer**: a 2.5% RSD says the machine was quiet and the number is trustworthy. On a busy machine the mean drifts upward and the minimum does not, which is precisely when the rule earns its keep, and precisely when a benchmark that quoted a mean would report that your code got slower because someone started a build.

**A small batch reports the clock, and the tick count proves it.**

| ops/batch | ns/op | batch ns | clock ticks |
|---|---|---|---|
| 1 | 41.0 | 41 | **1.0** |
| 3 | 41.7 | 125 | **3.0** |
| 10 | 33.3 | 333 | 8.0 |
| 100 | 32.9 | 3,292 | 79.0 |
| 1,000 | 34.7 | 34,750 | 834.0 |
| 20,000 | 34.3 | 685,250 | 16,446.0 |
| 200,000 | 34.5 | 6,896,334 | 165,512.0 |

The tick counts are **integers**, and that is the whole argument. A batch of one operation always spans exactly one tick, so it reports 41 nanoseconds and would report 41 nanoseconds for *any* operation faster than the clock's resolution. A batch of three spans two or three ticks depending on where it lands relative to the timer's edge, which is why that row moves between runs while the work does not; repeated runs of this benchmark give 27.7 ns/op (two ticks) or 41.7 (three) for the same code.

Only once a batch spans hundreds of ticks does the quantisation become a rounding error and the number start describing the code. The true cost here is about 34 nanoseconds, and it is visible from 10 operations per batch upward and invisible below.

**A null result, reported as one.**
A warm-up effect from the specializing interpreter was looked for and not found at these batch sizes. Specialization completes within the first few dozen executions out of 20,000, and no systematic difference between the first batch and later ones survived measurement. The harness still discards a warm-up batch, because it is nearly free and because it *would* matter at `number=10`, but this book will not claim a correction it could not measure.

---

## 85.4 Edges and failure modes

**`timeit`'s `setup` runs once per repeat, not once per operation.**
State mutated by the timed statement persists across the operations within a batch. Timing `lst.pop()` on a 100-element list with `number=20000` empties the list on operation 100 and times an exception for the rest. If the operation mutates, the setup has to be inside the timed statement, and then you are timing the setup too.

**Do not compare across interpreters or builds.**
This book's two verification interpreters differ in optimisation level and computed gotos (Chapter 78). A ratio drawn across them measures the build. Every table here is within one interpreter.

**Beware the operand that is a constant.** §85.1.
`timeit("x in s")` where `s` is a `frozenset` literal in the setup is fine. `timeit("1 in (1, 2, 3)")` is not: the tuple is a constant and 3.11+ may fold the containment test as well.

**`repeat` is not `number`, and the difference is the point.**
`number` is operations per batch, and it fights the clock's resolution. `repeat` is batches, and it estimates the noise. Increasing `number` makes a single figure more accurate; increasing `repeat` makes it more likely you found the floor. Both are needed.

**A benchmark that allocates is affected by the disabled collector.** §85.1.
`timeit` turns off the cyclic collector. For allocation-heavy code, re-run with `gc.enable()` inside the setup and compare; if the two disagree materially, the collector is part of your workload and the default figure is optimistic.

**Reordering rows can change them.**
Later rows run on a warmer machine, a fuller free list, and sometimes a differently specialized interpreter. If two rows are within a few percent, shuffle their order and re-run before believing the ordering.

**The `min` rule does not apply to latency work.** §85.2.
For a service's p99 you want the tail, and the tail is the thing this methodology deliberately discards. Use the right tool for the question: histograms and load, not `timeit`.

---

## 85.5 Connections

**Backward.**
The per-instruction cost these measurements are made of is Chapter 78. Constant folding, which is failure mode 2, is Chapter 56. Laziness, which is failure mode 3, is Chapters 76 and 91. The specializing interpreter's warm-up is Chapter 76 and Volume 15. `timeit` as a module, and `perf_counter` as a clock, are Deep S.

**Forward.**
Finding out whether the code you are about to microbenchmark matters at all is Chapter 86. Measuring the exponent instead of the constant is Chapter 87. `cProfile`'s mechanics and its own distortion are Chapter 51 (Deep S). `tracemalloc` for the memory dimension is Chapter 85 (Deep O). The decision about when to stop optimising is Chapter 92.

**Across books.**
The harness in `code/_harness/bench.py` is shared in spirit with **Book I**'s, and the methodology arguments are identical because the failure modes are: a C++ microbenchmark is destroyed by the optimiser eliminating unused results exactly as a Python one is destroyed by constant folding, and both are detected the same way, by asking what actually executed. The difference is that Book I's escape hatch is `benchmark::DoNotOptimize` and Python's is consuming the iterator.

---

## 85.6 Exercises

**1. Fall into all five.** Write five benchmarks, one per failure mode in §85.1, each of which reports an impressive and meaningless number. Then write the one-line check that detects each.

**2. Read the code object first.** Take three expressions you would benchmark and check `co_consts` for each before timing. Report any that were already folded.

**3. Find your clock.** Print `time.get_clock_info("perf_counter")` on your machine, then reproduce §85.3's second table. Confirm the tick counts are integers at small batch sizes and explain the row that moves between runs.

**4. Make the collector matter.** Write an allocation-heavy benchmark and time it with `timeit`'s default and with `gc.enable()` in the setup. Report the gap and say which figure you would quote in a design document.

**5. Break the setup.** Write a benchmark of a mutating operation that silently measures the wrong thing after the first few iterations. Show how you would detect it, then fix it, and say what the fix costs in measurement accuracy.

**6. The design question.** `timeit` disables the cyclic collector by default. Argue both sides: what enabling it would do to the reproducibility of every benchmark in this book, what disabling it hides about allocation-heavy code, and what a third option (report both, always) would cost in time and clarity.

---

## 85.7 Summary and cross-references

- **A number is not a measurement.** Five ways a microbenchmark measures nothing, all detectable by asking what executed: the **clock** is coarser than the operation (41.7 ns resolution here); the **compiler** already evaluated it (`1024` is in `co_consts`); the expression is **lazy** (`map` ran the function 0 times until consumed); the operation **caches** (100 calls, 1 body execution, 99 hits); the **input** selects a fast path (63 comparisons sorted, 302 shuffled).
- **`timeit` disables the cyclic collector** while timing and restores it after. Defensible for reproducibility, and a distortion for allocation-heavy code.
- **Noise is one-sided, so the minimum is the headline statistic.** Measured: every statistic is at or above the min, spread 10% on a quiet machine, RSD 2.5%. RSD is a machine-quietness diagnostic, not a speed figure.
- **A small batch reports the clock, and clock ticks prove it.** A batch of one operation spans exactly **1 tick** and reports 41 ns for anything faster than the resolution; a batch of three spans 2 or 3 ticks and moves between runs. The true cost, about 34 ns, is only visible once a batch spans hundreds of ticks.
- **A warm-up effect was looked for and not found** at these batch sizes; the null is reported rather than a correction claimed.
- **What a microbenchmark cannot tell you:** whether the code matters (Amdahl), how it behaves under a real working set, anything about the tail, or what a cold process does. Its honest output is **comparative** ("A is 2.6x B, one interpreter, one machine, one input size"), not absolute.
- **Edges:** `setup` runs per repeat, so mutating operations corrupt later iterations; never compare across builds; `number` fights the clock and `repeat` estimates the noise; reordering rows can change them; the `min` rule is wrong for latency percentiles.

**Cross-references.** Per-instruction cost → Chapter 78. Constant folding → Chapter 56. Laziness → Chapters 76, 91. Specialization warm-up → Chapter 76, Volume 15. `timeit` and `perf_counter` → Deep S. Profiling → Chapter 86 and Chapter 51. Complexity over constants → Chapter 87. `tracemalloc` → Chapter 85. When to stop → Chapter 92.
