# Chapter 51: Profiling

A developer profiles a slow request with `cProfile`, sees a function taking "45 ms," optimizes it down,
re-profiles, and reports a big win, but the production latency barely moves. The mistake is trusting
`cProfile`'s *absolute* numbers. `cProfile` is a **deterministic** profiler: it hooks every function call and
return to attribute time, and that per-call instrumentation adds substantial overhead, **4.3x** on a call-
heavy workload in this chapter's measurement (96 ms profiled versus 22 ms unprofiled). The "45 ms" was
inflated by the profiler and skewed toward call-heavy code. `cProfile` answers *where* time goes (which
functions dominate, relative to each other), which is exactly what you need to find a hotspot; it does not
answer *how fast* the code really is, for that you measure the hotspot with a benchmark whose timing the
profiler does not distort.

That division of labor, profile to locate, benchmark to measure, is this chapter's subject and the capstone
of the book's performance methodology. It continues **Deep S** with `cProfile`/`pstats`, pairing with `dis`
(Chapter 50, what runs) and the benchmark harness (how fast) to make performance work evidence-based rather
than guessed.

## Section index

- **51.1** What `cProfile` tells you (and what it does not)
- **51.2** Why deterministic profiling distorts time
- **51.3** Measurement: the profiler's overhead
- **51.4** Edges and failure modes
- **51.5** Connections
- **51.6** Exercises
- **51.7** Summary and cross-references

Listings live under `code/ch051/` and are re-executed by `make verify` on both interpreters.

---

## 51.1 What `cProfile` tells you (and what it does not)

```python
# code/ch051/l01_profile.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- cProfile attributes calls to functions (counts are deterministic) ---
  work called   :     1 time(s)
  middle called :  1000 time(s)  (1 per loop iteration)
  leaf called   :  2000 time(s)  (2 per middle call)
--- the hotspot is the most-called leaf function ---
  most-called function : leaf (2000 calls)
  this is where to focus a benchmark, not to trust cProfile's ms
```

`cProfile.Profile()` records, for every function, its **call count** and its time (total and cumulative), and
`pstats.Stats` lets you sort and print, most usefully `sort_stats('cumulative')` to see which functions
account for the most time including their callees, and `sort_stats('tottime')` for time excluding callees.
The listing prints the **call counts**, which are *deterministic*, `work` runs once, `middle` 1000 times (one
per loop iteration), `leaf` 2000 times (twice per `middle`), and identifies the most-called function. This is
`cProfile`'s real strength: it reconstructs the call structure and attributes work to functions, so you can
see that `leaf`, called 2000 times, is where the program spends itself, without reading the code.

What the listing deliberately does *not* print is the *times*, because they vary run to run and, worse, are
inflated by the profiler itself (§51.2). The deterministic call structure tells you where to look; the times
tell you the *relative* ranking (which function dominates) but not a trustworthy absolute. The workflow the
listing models: use `cProfile` to find the hot function, then measure *that function* properly.

---

## 51.2 Why deterministic profiling distorts time

`cProfile` is *deterministic* in the sense that it observes *every* call and return, via a C-level hook the
interpreter invokes on each. That gives complete, exact call counts, but it means every function call in the
program now also runs the profiler's bookkeeping (record the entry, start a timer, on return stop it and
attribute the elapsed time). For a function that does a lot of work per call, that fixed hook cost is
negligible. For a function that does *little* work per call but is called *often*, the hook cost can rival or
exceed the function's own work, so the profiler both slows the program overall and **over-attributes** time to
call-heavy code relative to compute-heavy code.

The consequence is twofold. The *absolute* times are inflated (the whole program runs several times slower
under the profiler), so a "45 ms" line is not 45 ms in production. And the *distribution* is skewed toward
functions with many small calls, which can make a frequently-called trivial helper look like a bigger
problem than a rarely-called expensive one. `cProfile`'s call counts and *relative* ranking survive this,
which is why they are what you trust; its millisecond figures do not, which is why you do not optimize
against them directly. To measure a hotspot's true cost you must take the profiler *out* and time the
function in isolation, which is what the benchmark harness (min-of-many, no per-call hook) does.

---

## 51.3 Measurement: the profiler's overhead

**Methodology.** `code/ch051/bench_profile_overhead.py`. The same call-heavy workload (20,000 calls to a
small `leaf`) run with and without `cProfile` enabled. `min` per run. CPython 3.13.5, Apple M3 Pro, macOS
27.0, arm64.

| call-heavy workload | min per run | ratio |
|---|---|---|
| unprofiled | **~22 ms** | 1.00x |
| under `cProfile` | **~96 ms** | **~4.3x** |

The profiled run is **~4.3x** slower for the same work, purely from the per-call hook, and this workload is
nearly all calls, which is the worst case (a compute-bound workload with few calls would show far less
overhead, which is itself the point: the overhead is *not uniform*, so it distorts the *shape* of the
profile). The ~4.3x is why `cProfile`'s absolute times cannot be read as the code's real speed.

The rule, and the book's performance method in one line: **profile to find *where*, benchmark to measure *how
fast*, and disassemble (Chapter 50) to understand *why*.** Use `cProfile` first to locate the hot function by
relative ranking and call counts; then measure that function with `timeit` or the harness, whose timing has no
per-call hook, to get its true cost and to validate any optimization; use `dis` to see what it compiles to.
Never optimize against a profiler's absolute milliseconds, and never conclude an optimization worked from a
re-profile alone, confirm it with an unprofiled benchmark. For low-overhead attribution on a live or
production system, a *statistical* (sampling) profiler or `sys.monitoring` (Chapter 22, PEP 669) trades exact
counts for much lower distortion.

---

## 51.4 Edges and failure modes

**Trusting `cProfile`'s absolute times.** §51.2. They are inflated (here ~4.3x) and skewed toward call-heavy
code. Use the relative ranking and call counts; measure real speed with a benchmark.

**Optimizing a function that is not actually hot.** The profiler's skew can make a frequently-called trivial
helper look dominant. Confirm with cumulative-time ranking and by benchmarking the candidate before investing
in it.

**Profiling too small a workload.** A profile of a single fast call is dominated by startup and noise. Profile
a representative workload (many iterations, realistic inputs) so the ranking is meaningful.

**Micro-optimizing under the profiler's distortion.** A change that reduces *calls* looks great under
`cProfile` (which taxes calls) even if it does not help unprofiled. Validate every change with an unprofiled
benchmark, not a re-profile.

**Deterministic profiler on I/O- or concurrency-bound code.** `cProfile` measures Python function time; time
spent blocked on I/O, in C extensions, or waiting on locks is attributed to the calling function without
detail. For I/O-bound or async code, wall-clock tracing (`sys.monitoring`, async-aware profilers) tells you
more than `cProfile`'s function times.

**Forgetting to sort/limit output.** Raw `pstats` output is huge. `sort_stats('cumulative').print_stats(20)`
(or `'tottime'`) focuses on the functions that matter; reading unsorted output wastes the profile.

---

## 51.5 Connections

**Backward.** `dis` (Chapter 50) is the *what runs* to this chapter's *where time goes*; together with the
benchmark harness (*how fast*) they are the book's full performance method. The `sys.monitoring`/`settrace`
hooks `cProfile` is built on are Chapter 22. Every measured finding in Book II, the `min`-of-many discipline,
the machine-quietness diagnostics, is the *benchmark* half this chapter pairs with the *profile* half.

**Forward.** Statistical/sampling profilers and `sys.monitoring`-based low-overhead tools are the
production-profiling material later in **Deep S**. Memory profiling (`tracemalloc`, used throughout the
book's memory benchmarks) is the space analogue. Flame graphs and continuous profiling in production are a
**Deep U** operational topic.

**Across books.** Profile-then-benchmark is how Book II and **Book III** find and fix real hotspots rather
than guessed ones. A **Book III** serving path is profiled to locate the dominant stage (tokenization,
retrieval, inference glue), then that stage is benchmarked and optimized and re-benchmarked unprofiled to
confirm, exactly the §51.3 discipline. Optimizing against a profiler's absolute numbers, or shipping an
"optimization" validated only by a re-profile, is the classic performance-work error **Deep U** guards
against. **Deep T** applies the same method to numeric hot paths.

---

## 51.6 Exercises

**1. Locate a hotspot.** Profile a small program with a clear hot function and use `pstats` cumulative and
total-time rankings to identify it. Confirm the call counts match the code's structure (as in §51.1).

**2. Measure the overhead.** Run §51.3's benchmark and confirm `cProfile` slows a call-heavy workload
several-fold. Then profile a *compute-heavy* workload with few calls and show the overhead is much smaller.
Explain why the overhead is not uniform.

**3. Catch the distortion.** Construct a program with one rarely-called expensive function and one often-
called trivial one, profile it, and observe how the profiler's per-call cost affects their apparent weights.
Explain which ranking (cumulative, tottime, ncalls) is most trustworthy.

**4. Validate an optimization honestly.** "Optimize" the hot function, re-profile (it looks faster), then
benchmark it unprofiled. Report whether the unprofiled benchmark agrees. Explain why the benchmark is the
verdict, not the re-profile.

**5. The design question.** `cProfile` gives exact call attribution at the cost of large, non-uniform
overhead; a sampling profiler gives low overhead at the cost of exactness. Argue when each is the right tool.
Your answer must use the §51.3 overhead, explain what "profile to find, benchmark to measure" means
operationally, and say why absolute profiler times must never be the optimization target.

---

## 51.7 Summary and cross-references

- **`cProfile`** is a deterministic profiler: it hooks every call/return to attribute time. Its **call counts
  and relative ranking** are trustworthy and tell you *where* time goes; its **absolute times are not** the
  code's real speed.
- **Measured:** `cProfile` slows a call-heavy workload **~4.3x** (per-call hook), and the overhead is non-
  uniform, over-weighting call-heavy code and distorting the profile's shape.
- **The method:** **profile to find *where*** (`cProfile`), **benchmark to measure *how fast*** (`timeit`/
  harness, no per-call hook), **disassemble to understand *why*** (`dis`, Chapter 50). Never optimize against
  a profiler's absolute ms; validate every change with an unprofiled benchmark.
- **For production/low-overhead attribution,** use a statistical profiler or `sys.monitoring` (Chapter 22).

**Cross-references.** `dis` → Chapter 50. `sys.monitoring`/`settrace` → Chapter 22. The benchmark harness and
`min`-of-many → the book's measurement method throughout. `tracemalloc` memory profiling → the memory
benchmarks. Production profiling → Deep S and Deep U. Numeric hot paths → Deep T.
