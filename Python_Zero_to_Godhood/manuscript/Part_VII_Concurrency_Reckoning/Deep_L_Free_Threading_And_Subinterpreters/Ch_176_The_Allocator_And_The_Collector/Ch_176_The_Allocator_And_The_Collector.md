# Chapter 95: The Allocator and the Collector

Chapter 93's table listed "make the allocator and GC safe" as the second of the GIL's jobs. This chapter is what took the job: pymalloc, whose arenas and pools Deep B mapped, was replaced on the free-threaded build by a per-thread-heap allocator built on mimalloc, and the cyclic collector became a **stop-the-world** event that must halt every thread before it can scan.

Both changes are invisible in the API and enormous in the measurements. The allocator's half is the good news: four threads churning allocations scale to **3.4x** once the collector steps aside, because each thread allocates from its own heap with no shared lock, and the old GC pre-header is gone (Chapter 94 measured GC-tracked objects breaking even on size). The collector's half is the bill: with default settings the same threaded workload manages only **1.8x**, because the young-generation threshold of 2,000 allocations turns allocation-heavy parallel code into a drumbeat of pauses, and **a pause now costs its duration multiplied by the threads it stops**. The collector's share of this workload grew from 26% of serial runtime to 62% of threaded runtime without a single line of code changing.

There is also a confession in this chapter's methodology, kept deliberately: the first draft of its benchmark reported the collector as free, because `timeit` **silently disables garbage collection** around whatever it measures. Chapter 85's rule, know what your harness does to the machine, applies to this book's own harness.

**This is a Deep L chapter.**
Deep B owns pymalloc, refcount-driven deallocation, and the cyclic algorithm; Chapter 94 owns the redesigned refcount that decides *when* the collector is needed. This chapter owns what allocation and collection cost on the free-threaded build, and the dials that move those costs.

## Section index

- **95.1** Same API, different deaths, counted
- **95.2** The machinery: per-thread heaps, absorbed headers, a world that stops
- **95.3** Measurement: the allocator against the collector
- **95.4** Edges and failure modes
- **95.5** Connections
- **95.6** Exercises
- **95.7** Summary and cross-references

Listings live under `code/ch176/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 95.1 Same API, different deaths, counted

```python
# code/ch176/l01_when_things_die.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- the collector's dials are unchanged ---
  gc.get_threshold() : (2000, 10, 10)
  generations reported by get_stats() : 3
  same dials on every build; what turns beneath them differs
--- when things die, probed with weakrefs ---
  instance dead at last reference : True
  local function dead at last ref : True
  MODULE-level function, at del   : True
  class dead at last reference    : False
  module function after collect   : True
  class dead after gc.collect()   : True
```

On the free-threaded build one line changes, and it is the seam this chapter shares with Chapter 94. Verified output (CPython 3.14t):

```text
  MODULE-level function, at del   : False
```

**The dials block is API compatibility over a different machine.**
`(2000, 10, 10)` and three generations are reported on every build. On the GIL builds they mean what Deep B taught. On the free-threaded build the collector runs as a single generation (PEP 703; the generational dials remain for compatibility, and this is sourced to the design documents rather than measured, since generation boundaries are not observable from Python). The practical consequence *is* measured, in §95.3: every collection visits the whole tracked heap, so collection cost tracks the live set, not the garbage.

**The deaths table is the chapter's precision instrument.**
Instances die at their last reference on every build: refcount-driven deallocation, the promptness that RAII-style Python has always leaned on, survives free-threading intact. Classes have *never* died promptly, on any build, because a class is born in a cycle with its own `__dict__` and waits for the collector; nothing changed, and code discovering this "on the new build" is discovering Deep B. The build seam is exactly one row wide: a **module-level function** dies promptly on GIL builds and at the next collection on the free-threaded build, because deferred reference counting (Chapter 94) targets top-level functions, the objects every thread touches. A *local* lambda is not deferred and dies promptly everywhere, which is why the probe distinguishes the two.

**And the 100 cycles come back 200 for 200 on every build.**
The cyclic algorithm is unchanged and exact. What changed is its execution context: on the free-threaded build, running it means stopping every thread, and that sentence is the entire next section.

---

## 95.2 The machinery: per-thread heaps, absorbed headers, a world that stops

**The allocator: from one heap with one guard to a heap per thread.**
pymalloc was never thread-safe; the GIL was its lock. Rather than bolt a lock onto its arenas (which would have made every allocation a contention point, Chapter 94's shared-refcount row shows what that costs), the free-threaded build adopted **mimalloc**, whose design gives each thread its own segments and pages: allocation is a bump in thread-local state, no atomics on the fast path. This is why §95.3's gc-off row scales to 3.4x, and it is the same "allocate where you use" locality that biased refcounting bets on, applied one layer down.

**The header: the GC's bookkeeping moved inside.**
On GIL builds every GC-tracked object carries a 16-byte `PyGC_Head` *outside* the object, forming the doubly linked generation lists Deep B drew. The free-threaded build deletes it: tracking state lives in `ob_gc_bits` inside the header (Chapter 94's struct), and the collector finds objects by walking the allocator's own page metadata instead of chasing list links. That is the accounting behind Chapter 94's measurement, `object()` doubles but a list does not, and it quietly removes the linked-list surgery from every allocation and collection.

**The collector: correct first, concurrent later.**
A collector racing live mutator threads needs either fine-grained synchronisation on every pointer write (a write barrier) or the threads not running. CPython chose the second: collection **stops the world**, waiting for every thread to reach a safe point, scanning with the same mark-alive/subtract-refs algorithm as ever, then releasing. Safe reclamation of memory that lock-free readers might still be touching (Chapter 96's containers) uses quiescent-state-based reclamation, QSBR: a page is only returned once every thread has passed a point where it provably holds no stale reference. The result is Deep B's semantics at a new price: `pause cost x threads stopped`, and §95.3 shows that product dominating a parallel workload.

**The dials that move the price** are the ones the listing showed unchanged: `gc.set_threshold` (raise the first number and allocation-heavy phases pause less often), `gc.freeze` (move the long-lived startup heap out of scanning entirely), and `gc.disable` for bounded critical sections that manage their own cycles. On GIL builds these were memory-tuning knobs; on the free-threaded build they are **parallelism** knobs, which is this chapter's one-sentence takeaway.

---

## 95.3 Measurement: the allocator against the collector

**Methodology.** `code/ch176/bench_allocation_and_pauses.py`.
Four workers, each building and discarding a 200,000-tuple list five times; sequential vs 4 threads, collector on vs off. Timed with `perf_counter` around whole runs, min of 5, **not** `timeit`, which disables the collector and silently erases the effect under measurement (an early draft did exactly that; the failure is preserved in the benchmark's docstring). Within-build ratios only.
CPython 3.14.6, both builds; Apple M3 Pro, macOS 27.0, arm64.

**The free-threaded build.**

| allocation churn | time | scaling |
|---|---|---|
| sequential, gc on | 140.8 ms | — |
| 4 threads, gc on | 79.2 ms | **1.8x** |
| sequential, gc off | 103.8 ms | — |
| 4 threads, gc off | 30.2 ms | **3.4x** |

**The GIL build, same program.**

| allocation churn | time | scaling |
|---|---|---|
| sequential, gc on | 126.0 ms | — |
| 4 threads, gc on | 131.2 ms | 0.96x |
| sequential, gc off | 125.7 ms | — |
| 4 threads, gc off | 134.1 ms | 0.94x |

**Read the GIL table first, because it calibrates.**
Threads buy nothing (Chapter 93), and the collector costs almost nothing serial: the generational design scans only recent allocations, and most of this garbage already died by refcount before any scan. One lock, one story.

**The free-threaded table splits twice, and each split is one mechanism.**
Down the columns: disabling the collector takes the serial run from 140.8 to 103.8 ms, so collection is ~26% of serial runtime here, the single-generation collector rescanning the live list on a 2,000-allocation cadence. Across the rows: with the collector off, threads scale 3.4x, the per-thread heaps running independently; with it on, 1.8x, because each pause stops all four threads, so the collector's share of *threaded* runtime is ~62%. **The same collector, the same workload, went from a fifth of the bill to two thirds of it, purely because pauses now multiply by the threads they stop.** The gc-on rows also carry visibly higher run-to-run spread (RSD 7 to 10% against 2 to 4% with it off); pause placement is jittery, and that jitter is part of what a latency-sensitive service inherits.

**Book I**'s hot path allocates from arenas it never frees mid-session and runs no collector at all, which is the limiting case of this table: the fastest pause is the one the design made impossible. The Python side of the shared system adopts the bounded version of the same idea, `gc.freeze()` after warm-up and thresholds raised through the trading window, and Chapter 100 folds that into the architecture choice.

---

## 95.4 Edges and failure modes

**`timeit` disables the collector.** §95.3's methodology, promoted to an edge because it bites silently: any GC-sensitive measurement made with `timeit`, including this book's own `measure()` harness, reports the collector as free. Time whole runs with `perf_counter` and state the collector's state explicitly.

**Deferred objects hold what they close over.**
A module-level function that captures a large object in a default argument or closure keeps it alive until the next collection on the free-threaded build (§95.1). The leak-shaped symptom is memory that drops on `gc.collect()` but not on `del`; the fix is the same as ever, do not park big data on code objects.

**`__del__` timing moved for exactly the objects that hold resources.**
Deep B's warning, finalizers run "eventually", was survivable when refcounting made "eventually" mean "now" for most objects. On the free-threaded build, top-level functions and anything in their closure graphs die at collection time, so a finalizer-based resource release can outlive its function by a full GC cycle. Context managers; the advice has now been load-bearing in three volumes.

**Raising thresholds trades pause frequency for pause size.**
The single-generation collector's pause tracks the live set, so deferring collection while the live set grows makes each pause longer. For steady-state services, the tuning target is pause *frequency* during hot phases with a bounded live set; for batch work, one `gc.collect()` at a phase boundary beats many mid-phase pauses.

**`gc.freeze` is powerful and one-way per epoch.**
Frozen objects are never scanned again until `unfreeze`, which also means cycles among them are never reclaimed. Freeze the startup heap, import graph, config, compiled templates, not the working set.

**Stop-the-world includes threads that allocate nothing.**
A pure-compute thread with zero allocations still halts at every collection triggered by its neighbours, which is how one allocation-heavy thread taxes an entire process. Chapter 100's architecture answer, isolate allocation-heavy stages into their own processes or interpreters, starts from this fact.

**And the process's RSS still does not shrink on demand.**
mimalloc returns memory to the OS by its own policy, QSBR delays some reclamation by design, and Deep B's lesson that "freed" is not "returned" carries over unchanged. Measure with `tracemalloc` for Python-level truth and the OS for process truth (Chapter 89), on this build as on every other.

---

## 95.5 Connections

**Backward.**
pymalloc's arenas, the GC pre-header, the cyclic algorithm, and finalizer discipline are Deep B (Chapters 28 to 31); this chapter is that machinery's free-threaded successor. The absorbed header and deferred reference counting are Chapter 94. The honest-measurement rule the `timeit` confession illustrates is Chapter 85; memory measured as a cost model is Chapter 89. The volume map is Chapter 93.

**Forward.**
The per-object locks that make container operations safe between pauses are Chapter 96. What the allocator and collector changes cost the single-threaded interpreter is part of Chapter 97's accounting. Subinterpreters, which keep a *generational* collector per interpreter by keeping a GIL per interpreter, are Chapter 98's counterpoint. The correctness chapter leans on death-timing (§95.1) for its resource rules, Chapter 99, and Chapter 100 turns this chapter's dials into architecture.

**Across books.**
Every trade here has a C++ name: per-thread heaps are tcmalloc/jemalloc/mimalloc practice; stop-the-world versus write barriers is the oldest argument in GC literature; QSBR is RCU's reclamation discipline; and `gc.freeze` is the arena allocator's "never free mid-session" worn as a runtime flag. **Book I** solves the chapter by not playing, no tracing collector at all, and the shared system's seam splits exactly along that line: deterministic memory on the C++ side, tuned pauses on the Python side.

---

## 95.6 Exercises

**1. Reproduce the split.** Run the benchmark on both builds. Then raise `gc.set_threshold(100_000)` and produce the intermediate row: how much of the 3.4x does tuning recover without disabling anything?

**2. Find the pause.** Instrument the workload with `gc.callbacks` to timestamp each collection on the free-threaded build. Report pause count, total pause time, and the longest single pause, and reconcile the total against §95.3's 26%.

**3. Freeze the right things.** Build a program with a 1M-object startup graph and a small working set. Measure threaded churn with and without `gc.freeze()` after startup, and report the pause-time difference.

**4. Chase a deferred leak.** Park a 100 MB `bytes` in a module-level function's default argument, delete the function, and show memory falling only at `gc.collect()` on the free-threaded build. State the `tracemalloc` signature that distinguishes this from a true leak.

**5. The jitter budget.** For a synthetic 1 ms-per-request service on the free-threaded build, measure p50/p99 latency with default thresholds, raised thresholds, and a background thread doing allocation churn. Report what the collector does to p99 in each configuration.

**6. The design question.** CPython chose stop-the-world over a concurrent collector with write barriers. Argue the choice: what a write barrier would cost on every pointer store (against Chapter 78's 3.4 ns budget), what it would do to every C extension's compiled stores (the Chapter 94 wheel problem, squared), and why single-generation-with-QSBR is the conservative first step. Then state the workload class that will eventually force incremental or concurrent collection on the t-build, and which of this chapter's measurements you would re-run to detect that the trade had flipped.

---

## 95.7 Summary and cross-references

- **The allocator scales; the collector stops the world.** Measured on 3.14t: allocation churn threads at **3.4x** with the collector off, **1.8x** with it on; the collector's share grew from 26% of serial to **62% of threaded** runtime because a pause costs its duration times the threads it stops.
- **The GIL build is flat everywhere** (threads 0.96x, collector ~free): one lock, one story, and generational scanning that rarely touches the mostly-refcount-dead garbage.
- **pymalloc gave way to per-thread heaps (mimalloc)**; the `PyGC_Head` pre-header is gone, absorbed into the header's `ob_gc_bits`, which is why GC-tracked objects did not grow (Chapter 94).
- **The free-threaded collector is single-generation and stop-the-world**, with QSBR deferring reclamation under lock-free readers; the generational dials survive as API only.
- **Deaths moved for exactly one row of the table**: module-level functions (deferred refcounting) die at the next collection on the t-build; instances and local functions stay prompt everywhere; classes never were prompt.
- **The GC dials are now parallelism dials**: `set_threshold` for hot phases, `freeze` for the startup heap, phase-boundary `collect()` for batch work; and the gc-on rows' extra jitter is part of the price.
- **`timeit` disables the collector**, including in this book's harness; GC measurements need whole-run timing with the collector's state stated.

**Cross-references.** pymalloc, `PyGC_Head`, the cyclic algorithm, finalizers → Deep B (Chapters 28 to 31). The header and deferred counting → Chapter 94. Honest measurement → Chapter 85. Memory as a cost model → Chapter 89. The volume map → Chapter 93. Container locks → Chapter 96. Single-threaded cost → Chapter 97. Subinterpreters → Chapter 98. Correctness → Chapter 99. Architecture → Chapter 100.
