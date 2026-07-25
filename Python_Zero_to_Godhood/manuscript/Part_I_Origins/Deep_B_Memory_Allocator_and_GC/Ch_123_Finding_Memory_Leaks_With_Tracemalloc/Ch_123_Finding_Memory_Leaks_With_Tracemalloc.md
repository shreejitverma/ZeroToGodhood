# Chapter 34: Finding Memory Leaks with `tracemalloc`

The whole point of reference counting (Chapter 31) and the cyclic collector (Chapter 30) is that memory manages itself, so how does a Python program leak?
It leaks the way this volume has hinted at repeatedly: a **reference you did not mean to keep.**
An object appended to a module-level list, cached in a dict that never evicts, captured in a closure, held by an event handler that was never unsubscribed, is *reachable*, so refcounting correctly keeps it alive, forever.
This is not a garbage-collector bug; it is a logic bug, and the collector cannot help you, because from its point of view the memory is legitimately in use.

Finding such a leak means answering one question, "where was this ever-growing memory allocated?", and `tracemalloc` (Python 3.4) is the standard-library tool that answers it.
Its workflow is a diff: take a snapshot, run the suspect code, take another snapshot, and ask `compare_to` which *source lines* grew.
The top entry points straight at the allocation site, and from there you trace back to the stray reference and remove it.
This chapter closes Deep B by turning the volume's memory model into a debugging skill, and the measurement establishes the one operational caveat: `tracemalloc` is a **diagnostic** with real overhead (~**7.7x** while tracing), used to hunt a leak and then turned off, not left running in production.

**This is the canonical home for memory-leak diagnosis.**
It applies Chapter 31 (a leak is a kept reference), Chapter 19 (`tracemalloc` is the deep memory accounting `sys.getsizeof` cannot give), and Chapter 32 (`gc.get_objects`/`get_referrers` are companion tools). It is the practical capstone of the memory volume.

## Section index

- **34.1** The leak-hunting workflow: snapshot, run, compare
- **34.2** Reading the result, and fixing the leak
- **34.3** Measurement: the cost of tracing
- **34.4** Edges and failure modes
- **34.5** Connections
- **34.6** Exercises
- **34.7** Summary and cross-references

Listings live under `code/ch123/` and are re-executed by `make verify` on both verification interpreters.

---

## 34.1 The leak-hunting workflow: snapshot, run, compare

```python
# code/ch123/l01_tracemalloc.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- snapshot, run suspect code, snapshot again ---
--- compare_to shows which LINES grew, biggest first ---
  memory grew at the top line     : True
  the top growth is in THIS file   : True
  new allocation blocks there >= 100 : True
--- get_traced_memory reports current and peak ---
  current <= peak (both tracked)   : True
  peak is positive                 : True
--- the rule ---
  snapshot -> run -> snapshot -> compare_to('lineno'); the top entry is
  the allocation site of the growth. The fix is dropping the stray reference
```

The workflow is a five-step diff, and the listing performs it against a planted leak (a module-level `_LEAK` list that `leaky()` keeps appending to):

1. **`tracemalloc.start()`** begins tracing; every subsequent allocation records where it happened.
2. **`take_snapshot()`** captures the current allocation state, the *before*.
3. **Run the suspect code**, here 100 calls to `leaky()`.
4. **`take_snapshot()`** again, the *after*.
5. **`after.compare_to(before, "lineno")`** returns per-source-line statistics of the *change*, sorted largest-growth-first.

The top result (`growth[0]`) is the single source line that grew the most, and it points straight at `leaky()`'s `append`: memory grew there (`size_diff > 0`), it is in this file (`traceback[0].filename == __file__`), and at least 100 new blocks were allocated at that line (one per call).
`get_traced_memory()` separately reports `(current, peak)` bytes, useful for "how much are we using now, and what was the high-water mark."

The output is reported as **booleans** deliberately: the exact byte counts, block counts, and file paths are machine- and run-specific (a path depends on where the repo lives; a count includes `tracemalloc`'s own bookkeeping), so the *portable, deterministic* facts are "did it grow, is it our line, are there many new blocks", which is exactly what a leak hunt needs to confirm.
This is the same discipline the whole book uses for non-deterministic measurements (Chapter 19's sentinel, Chapter 31's refcount deltas): assert the stable qualitative fact, not the fragile absolute.

---

## 34.2 Reading the result, and fixing the leak

Locating the allocation site is half the job; the other half is understanding that the allocation site is usually *not* the bug.

`tracemalloc` tells you **where the leaked memory was allocated**, `leaky()`'s `append`.
But the allocation itself is innocent, creating a list is not a leak.
The leak is the **reference that keeps it alive**: `_LEAK` is a module-level list, so every list appended to it is reachable for the life of the program, and refcounting (correctly) never frees them.
So the fix is never "allocate less at the hot line"; it is **find and remove the stray reference** that the allocated objects hang from.

This is why the leak-hunting mindset is about *references*, not allocations:

- **The allocation site (from `tracemalloc`) is the clue; the retaining reference is the bug.** After `tracemalloc` points you at `leaky()`, you ask "what keeps these alive?" and find `_LEAK`.
- **Common retaining references:** a module- or class-level container that only grows; a cache with no eviction; a closure or default argument capturing state; a registry/observer list that objects are added to but never removed from; an exception or traceback holding a frame (holding its locals).
- **The fix matches the cause:** evict from the cache (or use a `weakref.WeakValueDictionary`, Chapter 29, so entries do not keep values alive); unsubscribe the handler; clear the container; drop the closure.

`tracemalloc` has companions for the reference-hunting half.
`gc.get_referrers(obj)` (Chapter 32) tells you *what points at* a suspected object, walking you from the leaked object back to the container holding it.
`gc.get_objects()` enumerates all tracked objects (useful for "how many `Foo` instances exist, and is that number growing?").
Together, `tracemalloc` finds *where memory grows* and `gc.get_referrers` finds *what holds it*, and the intersection is the leak.
The rule: **`tracemalloc` locates the growth; then hunt the reference that retains it, and remove that.**

---

## 34.3 Measurement: the cost of tracing

`tracemalloc` earns its precision by intercepting every allocation, and that is not free.

**Methodology.** `code/ch123/bench_tracemalloc_overhead.py`.
An allocation loop (2,000,000 tuples appended to a list) run with `tracemalloc` off versus on.
Wall-clock, `perf_counter`.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| allocation loop | time | vs off |
|---|---|---|
| `tracemalloc` off | 74 ms | 1.0x |
| `tracemalloc` on | 575 ms | **7.7x** |

Tracing makes the allocation-heavy loop **7.7x** slower (10.5x on 3.14.6).
The reason is exactly what makes it useful: while tracing, *every* allocation is intercepted to record a traceback of where it happened, so a workload dominated by allocation pays that interception on every object.

This fixes how to *use* the tool.
`tracemalloc` is a **diagnostic**, turned on to hunt a leak and turned off afterward:

- **Reproduce the leak in development or staging** with `tracemalloc` on, run the workflow (§34.1), find the site, fix the reference, verify the growth is gone.
- **Do not leave it enabled in a production hot path**, the 7.7x is a real slowdown on allocation-heavy code.
- For **always-on** memory awareness, use *coarse* signals instead: `get_traced_memory()` sampled occasionally (still needs tracing on, so use sparingly), or, better, OS-level resident-set-size (RSS) sampled from outside the hot path, which has near-zero in-process cost.

You can also reduce `tracemalloc`'s cost when you do use it: `tracemalloc.start(nframes)` with a small frame count records shorter tracebacks (cheaper, less context), and filtering snapshots narrows what you analyze.
But the headline stands: full per-allocation tracing is a debugging mode, and the 7.7x is the price of the precision it gives, precision you want while hunting a leak and do not want in steady state.
This closes Deep B on a practical note: the memory model this volume built, refcounting, cycles, the collector, allocation, is not just theory but the mental model you debug *with*, and `tracemalloc` is the instrument that turns "memory is growing" into "line 42 allocates it and `_LEAK` retains it."

---

## 34.4 Edges and failure modes

**A leak is a kept reference, not an allocator bug.** §34.2.
`tracemalloc` shows where memory was allocated; the fix is finding what *retains* it. Do not optimize the allocation site; remove the stray reference.

**Absolute counts and paths are non-portable.** §34.1.
Byte counts include `tracemalloc`'s own bookkeeping; paths are machine-specific. Reason about growth (deltas, booleans), not absolute numbers, and never assert on exact bytes.

**Tracing has ~7.7x overhead.** §34.3.
Use `tracemalloc` to hunt leaks in dev/staging, not in production hot paths. Sample RSS from outside the process for always-on monitoring.

**`compare_to('lineno')` versus `'traceback'`.**
`'lineno'` groups by the final source line (concise); `'traceback'` groups by the full call stack (shows *how* the leaking line was reached, essential when a helper is called from many places). Start with `'lineno'`, switch to `'traceback'` when the site is shared.

**Snapshots themselves cost memory.**
A snapshot records every tracked allocation; on a large heap a snapshot is large. Take few, compare, and discard them; do not accumulate snapshots.

**tracemalloc must be started before the allocations you want to see.**
It only records allocations made *while* tracing. A leak that accumulated before `tracemalloc.start()` is invisible to it (though it will show *further* growth). Start tracing early enough to capture the growth window.

**Not all growth is a leak.**
A cache filling to its bound, a buffer sized to a workload, or lazy initialization all grow memory legitimately. `tracemalloc` shows growth; *you* decide whether it is unbounded (a leak) or bounded (expected).

**Cycles with `__del__` and uncollected garbage are separate diagnostics.**
`gc.garbage` (objects the collector could not reclaim) and `gc.get_stats` (Chapter 32) diagnose *collector* problems; `tracemalloc` diagnoses *retention* problems. Use the right tool for the symptom.

---

## 34.5 Connections

**Backward.**
The leak this tool finds is Chapter 31's "a stray reference keeps an object alive forever." `tracemalloc` is the deep, allocation-tracing accounting that Chapter 19 contrasted with shallow `sys.getsizeof`. `gc.get_referrers`/`get_objects` (the reference-hunting companions) are Chapter 32. `weakref` (Chapter 29) is the structural fix for cache-retention leaks.

**Forward.**
Production memory monitoring (RSS sampling, `resource.getrusage`, external profilers like `memray`, `objgraph` for reference-graph visualization) are ecosystem and observability topics. The allocator's own statistics (`sys._debugmallocstats`, arena/pool behaviour) are Chapter 28. Profiling *time* rather than memory is the performance volume.

**Across books.**
Leak-hunting with `tracemalloc` is an operational skill for **Book I**: a long-running trading or data system that slowly grows memory over hours is almost always retaining references, an unbounded cache, an accumulating log buffer, a subscription list, and the snapshot-diff workflow is how you localize it before it forces a restart. The order-book system runs periodic `tracemalloc` snapshots in staging to catch retention regressions (a new feature that forgets to evict), fixes them by bounding caches and using `weakref` for back-references (Chapter 29), and in production samples RSS externally rather than paying the §34.3 tracing overhead on its latency-critical path, the exact diagnostic-versus-production discipline this chapter prescribes.

---

## 34.6 Exercises

**1. Find the planted leak.** Reproduce §34.1: a function that appends to a module-level list, traced with the snapshot-compare workflow. Confirm the top growth line is the append. Explain each of the five steps.

**2. Fix it two ways.** Take the leak from Exercise 1 and fix it (a) by bounding the list and (b) by using a `weakref.WeakValueDictionary` where appropriate. Re-run `tracemalloc` and confirm the growth is gone. Explain why the fix is about the *reference*, not the allocation.

**3. Hunt the referrer.** For a suspected leaked object, use `gc.get_referrers` to walk back to what retains it. Combine with `tracemalloc` (where it was allocated) to identify the leak fully. Explain how the two tools complement each other.

**4. Measure the overhead.** Reproduce §34.3. Confirm tracing slows an allocation loop several-fold. Then use `tracemalloc.start(1)` (one frame) and show the overhead drops but the traceback shortens. Explain the trade and when to use each.

**5. The design question.** `tracemalloc` records a traceback per allocation, paying ~7.7x, rather than sampling. Argue why per-allocation precision is the right design for a leak *hunter* (versus a sampling profiler), and what that implies about when to enable it. Then argue what production always-on memory monitoring should use instead, and why.

---

## 34.7 Summary and cross-references

- A Python **leak is a reference you did not mean to keep** (Chapter 31): the object is reachable, so refcounting correctly keeps it alive. The collector cannot help; the fix is removing the stray reference.
- **`tracemalloc` finds where growth was allocated**, via the workflow **`start` -> snapshot -> run -> snapshot -> `compare_to('lineno')`**, whose top entry is the allocation site. `get_traced_memory()` reports `(current, peak)`.
- **The allocation site is the clue; the retaining reference is the bug.** Pair `tracemalloc` (where memory grows) with `gc.get_referrers`/`get_objects` (what holds it). Common causes: unbounded caches, module/class containers, closures, unremoved handlers.
- **Measured:** tracing makes allocation-heavy code **7.7x** slower, because every allocation records a traceback. `tracemalloc` is a **diagnostic** (dev/staging leak hunt, then off), not a production hot-path setting; sample RSS externally for always-on monitoring.
- **Edges:** reason about deltas/booleans, not non-portable absolutes; use `'traceback'` grouping for shared sites; start tracing before the growth window; not all growth is a leak.

**Cross-references.** A leak as a kept reference → Chapter 31. Deep accounting vs `getsizeof` → Chapter 19. `gc.get_referrers`/`get_objects` → Chapter 32. `weakref` (fixing retention) → Chapter 29. Allocator statistics → Chapter 28. This closes Deep B (Memory: Allocator and GC).
