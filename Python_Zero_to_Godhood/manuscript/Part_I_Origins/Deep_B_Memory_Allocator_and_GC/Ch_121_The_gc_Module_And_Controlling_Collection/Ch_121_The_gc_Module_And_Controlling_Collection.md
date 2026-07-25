# Chapter 32: The `gc` Module and Controlling Collection

Chapter 31 showed reference counting's blind spot, cycles, and named the cyclic collector as the fix.
Chapter 30 covered how that collector *works*.
This chapter is about *controlling* it: the `gc` module, the knobs it exposes, and the one situation where reaching for those knobs is genuinely worth it.
The headline is counterintuitive and famous: for building a large, long-lived data structure, **disabling the garbage collector makes the build several times faster** (measured **4.5x**), and doing so is safe if you scope it correctly.

The reason is structural.
The cyclic collector is *generational*: it runs often on young objects and rarely on old ones, on the theory that most objects die young.
But a full (oldest-generation) collection **scans every surviving tracked object**, and it is triggered by allocation counts, so while you are allocating millions of objects that will all *survive* (a big structure you are building), the collector keeps firing and keeps rescanning the ever-growing pile, redoing O(live) work that finds no garbage.
Turn it off for the duration of the build and you skip all of that.

But the knobs cut both ways, and the chapter's discipline matters as much as its trick.
With the collector off, any cycle you create **leaks** (Chapter 31), so `gc.disable()` is a *scoped* optimization for a known bulk operation, not a blanket setting.
The `gc` module also gives you visibility, what is tracked, what was collected, the generation statistics, that is invaluable for diagnosing memory behaviour.

**This is the canonical home for controlling the collector.**
It builds on Chapter 30 (the algorithm it tunes) and Chapter 31 (reference counting, which keeps running whether or not `gc` is enabled), and it connects to `gc.freeze()` and process startup (`fork`, Deep E) and to leak diagnosis (the next chapter, `tracemalloc`).

## Section index

- **32.1** The `gc` module: collect, track, generations, disable
- **32.2** When to touch the knobs (and when not to)
- **32.3** Measurement: disabling gc for a bulk build
- **32.4** Edges and failure modes
- **32.5** Connections
- **32.6** Exercises
- **32.7** Summary and cross-references

Listings live under `code/ch121/` and are re-executed by `make verify` on both verification interpreters.

---

## 32.1 The `gc` module: collect, track, generations, disable

```python
# code/ch121/l01_gc_control.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- gc.collect() reclaims cycles and returns how many objects it freed ---
  gc.collect() reclaimed : 2   (the two cycle nodes)
--- the collector tracks only CONTAINER objects (potential cycle members) ---
  gc.is_tracked([1])      : True   (a list can hold references)
  gc.is_tracked({'k': []}) : True   (a dict can)
  gc.is_tracked(1)        : False   (an int cannot form a cycle)
  gc.is_tracked('s')      : False   (nor a str)
--- three generations underpin the generational algorithm ---
  number of generations : 3
--- disable/enable the collector (reference counting is unaffected) ---
  after gc.disable() : gc.isenabled() = False
  after gc.enable()  : gc.isenabled() = True
--- the rule ---
  gc controls the CYCLIC collector: collect() reclaims cycles, it tracks
  only containers, uses 3 generations, and can be disabled independently
```

The `gc` module's core surface:

- **`gc.collect()`** forces a full collection and returns the number of unreachable objects it reclaimed, here `2`, the cycle from §31.1 that reference counting could not free. This is the manual trigger, useful after you know you have created and dropped a cyclic structure.
- **`gc.is_tracked(obj)`** reveals what the collector even *considers*. It tracks only **container** objects, things that can hold references and therefore participate in cycles: lists, dicts, tuples-of-containers, instances. **Atomic** objects (`int`, `str`, `float`, `bytes`) are *never tracked*, because they cannot reference anything and so cannot be part of a cycle. This is a real optimization: the collector never wastes time on the numbers and strings that dominate most heaps. (A subtlety: *empty* containers may be untracked as a further optimization, and whether they are differs across versions, which is why this listing uses non-empty containers.)
- **Three generations** underpin the *generational* algorithm (Chapter 30): new objects start in generation 0, survivors are promoted to 1 then 2, and older generations are collected less often. `gc.get_stats()` reports per-generation statistics.
- **`gc.disable()`/`gc.enable()`** turn the *cyclic collector* off and on. Reference counting (Chapter 31) is **unaffected**, it always runs, so with `gc` disabled, acyclic garbage is still reclaimed promptly; only cycle-detection stops.

The mental model to carry: `gc` controls the *supplementary* cyclic collector, not memory management as a whole. Disabling it does not turn off reclamation; it turns off *cycle* reclamation, leaving the prompt refcounting of Chapter 31 fully in force.

---

## 32.2 When to touch the knobs (and when not to)

The default collector settings are well-tuned, and the overwhelmingly correct choice is to **leave them alone**. There are a few specific situations where intervening pays.

**Disable during a large bulk build.** §32.3.
When you allocate a very large, long-lived structure (loading a big dataset into memory, building an index at startup), the collector fires repeatedly and rescans the growing survivor set for no benefit. Wrapping the build in `gc.disable()` / `gc.enable()` skips the wasted scans. This is the famous optimization, deployed at scale for load-time structure building, and it is real (the measurement below).

**`gc.freeze()` before `fork`.**
`gc.freeze()` (Python 3.7) moves all current objects to a permanent generation the collector ignores. Called before forking worker processes, it means the child's collector never scans the large shared parent heap, and, more importantly, never *writes* to those objects' GC headers, preserving copy-on-write sharing (a child that touches the header of every shared object un-shares the page). This is a key optimization for pre-fork server models (Deep E).

**Tune thresholds only with evidence.**
`gc.get_threshold()`/`gc.set_threshold()` control how often each generation is collected. Raising them collects less often (less CPU, more peak memory); the defaults are environment-tuned and *raising them blindly trades memory for a speedup you should measure first*. This is a last-resort knob.

**When *not* to touch them.**
Do not `gc.disable()` globally "for performance" in a long-running program: with it off, every cycle you create leaks (Chapter 31), and real programs create cycles constantly (a parent-child back-reference, a cache holding a closure, an exception traceback referencing a frame that references the exception). A globally-disabled collector turns those into an unbounded leak. The knob is for *scoped* bulk operations, not a global default.

The rule: **leave the collector on and default; disable it only around a known, cycle-free bulk build, and re-enable it immediately after.**

---

## 32.3 Measurement: disabling gc for a bulk build

**Methodology.** `code/ch121/bench_gc_build.py`.
Building a list of 2,000,000 dicts (all long-lived, all tracked), with `gc` enabled versus disabled.
Wall-clock, `perf_counter`.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| build 2,000,000 dicts | time | vs disabled |
|---|---|---|
| `gc` enabled (default) | 507 ms | **4.5x** |
| `gc` disabled | 112 ms | 1.0x |

Disabling the collector makes the build **4.5x** faster (4.6x on 3.14.6).
The mechanism is exactly §32.1's generational algorithm working against you in this atypical case.
As the list grows, allocation counts keep crossing the collector's thresholds, triggering collections; each full collection **scans all surviving tracked objects**, and because *every* object built so far survives (the structure is long-lived), the scan finds no garbage and simply re-walks the entire growing pile.
By the end, the collector has rescanned large fractions of two million objects many times over, all wasted work.
`gc.disable()` skips it; reference counting still reclaims any genuine acyclic garbage promptly, so nothing leaks *during* the cycle-free build.

The lesson is precise and bounded.
This is a **targeted** optimization for a **known bulk build of long-lived data**, wrap the build in `gc.disable()`/`gc.enable()`, and re-enable immediately after.
It is *not* a licence to disable `gc` globally: the moment normal operation resumes (creating and dropping cyclic structures), the collector must be back on or those cycles leak (Chapter 31, §31.3's 30,000x).
The generational collector's default behaviour is right for normal churn (lots of short-lived garbage, occasional survivors); it is wrong only for the specific pattern of "allocate millions of objects that all survive", and that is the exact and only case where turning it off is the correct call.
Measure, scope tightly, re-enable, this is a scalpel, not a switch.

---

## 32.4 Edges and failure modes

**`gc.disable()` leaks cycles.** §32.2, §31.3.
With the collector off, any reference cycle created leaks. Only disable it around code you *know* creates no cycles, and re-enable immediately. Never leave it globally disabled in a long-running program.

**Reference counting still runs when `gc` is disabled.** §32.1.
`gc.disable()` stops only cycle detection; acyclic garbage is still reclaimed promptly. Disabling `gc` does not turn off memory reclamation.

**Thresholds are environment-specific; do not hardcode them.**
`gc.get_threshold()` returns values that differ across builds and versions. Tune with `set_threshold` only against measured evidence, and never assert on a specific threshold value.

**`gc.collect()` in a hot loop is a pessimization.**
Forcing a full collection is expensive (it scans survivors). Call it deliberately, after a known cycle-creating operation, not routinely, and never per iteration of a hot loop.

**Empty-container tracking varies.** §32.1.
Whether an *empty* list/dict is tracked is a version-specific optimization. Reason about tracking with non-empty containers, and never depend on the empty-case behaviour.

**`gc.freeze()` must precede `fork`, and un-freezing has costs.**
`freeze()` before forking preserves copy-on-write; calling it at the wrong time, or letting children create large frozen sets, has its own memory implications. It is a server-startup tool, used deliberately (Deep E).

**A `__del__` on a cyclic object complicates collection.**
Historically, cycles containing objects with `__del__` were *uncollectable* (put in `gc.garbage`); since Python 3.4 (PEP 442) they are collected, but finalizer order within a cycle is unspecified. Avoid `__del__` on objects that may participate in cycles (the next chapter's `weakref.finalize` is safer).

**Disabling `gc` does not help churn-heavy workloads.**
If your workload creates *and drops* lots of objects (not building a survivor pile), the collector is doing useful work and disabling it mostly just defers/leaks. The §32.3 win is specific to the build-a-large-survivor-structure pattern.

---

## 32.5 Connections

**Backward.**
The collector this module controls is Chapter 30 (the generational cyclic algorithm); reference counting, which runs regardless of `gc` state, is Chapter 31. `is_tracked` reflects the object model's container-versus-atomic distinction (Chapter 19): only objects that can hold references can form cycles.

**Forward.**
Diagnosing *what* is leaking or growing, `tracemalloc`, `gc.get_objects()`, `gc.get_referrers()`, is the next chapter. `gc.freeze()` and copy-on-write across `fork` connect to process-based concurrency (Deep E). Weak references (Chapter 29) are the structural fix for the cycles and unwanted-liveness that make the collector necessary.

**Across books.**
The `gc.disable()`-for-bulk-build optimization is one **Book I** uses at startup: loading a large reference dataset (an instrument universe, a historical bar cache, a symbol table) into memory is exactly the "millions of long-lived objects" pattern where the collector's rescanning dominates, so the load is wrapped in `gc.disable()`/`gc.enable()` for a multiple-x speedup. In steady state the order-book system keeps the collector on (its churn creates cycles it must reclaim) but designs its hot-path structures to avoid cycles (using `weakref` for back-references, Chapter 29), so the collector rarely runs and never stalls the matching loop, tuning behaviour by structure rather than by disabling the collector globally.

---

## 32.6 Exercises

**1. Explore the module.** Reproduce §32.1: force a collection and read its return count, check `is_tracked` on containers versus atomics, confirm three generations, and toggle `disable`/`enable`. Explain why ints and strings are never tracked.

**2. Measure the build.** Reproduce §32.3. Confirm the speedup from disabling `gc` during a large build. Then show that for a *churn* workload (create and immediately drop objects), disabling `gc` gives little benefit, and explain the difference.

**3. Demonstrate the danger.** Disable `gc`, create cyclic garbage in a loop, and watch memory grow (Chapter 31's §31.3). Re-enable and `collect()` to reclaim it. Explain why global `gc.disable()` is dangerous.

**4. Watch generations.** Use `gc.get_count()` and `gc.get_stats()` to observe objects moving through generations as you allocate. Explain the generational hypothesis and why old generations are collected less often.

**5. The design question.** CPython exposes `gc.disable()` and threshold tuning as public knobs, unusual for a memory manager. Argue why (the §32.3 bulk-build case, `gc.freeze()` for `fork`), and what responsibility that puts on the programmer (the §32.4 leak risk). Would a fully-automatic collector with no knobs have been better? Defend your answer.

---

## 32.7 Summary and cross-references

- The **`gc` module** controls the **cyclic collector** (Chapter 30), not memory management as a whole, reference counting (Chapter 31) runs regardless. `gc.collect()` forces a collection and returns the count reclaimed; `gc.is_tracked` shows only **containers** are tracked (atomics never form cycles); there are **three generations**; `gc.disable()`/`enable()` toggle it.
- **Measured:** building 2,000,000 long-lived dicts is **4.5x** faster with `gc` disabled (112 vs 507 ms), because each full collection needlessly rescans the growing survivor pile. This is a **scoped** optimization for a known bulk build, not a global setting.
- **The knobs' discipline:** disable `gc` only around a known cycle-free bulk build and **re-enable immediately**; with it off, cycles leak (Chapter 31). Default settings are right for normal churn.
- **Other tools:** `gc.freeze()` before `fork` preserves copy-on-write; `set_threshold` tunes frequency (only with evidence). Leave defaults alone unless you have a measured reason.
- **Edges:** thresholds and empty-container tracking are non-portable; `gc.collect()` is expensive (not for hot loops); `__del__` on cyclic objects complicates collection.

**Cross-references.** The generational algorithm this tunes → Chapter 30. Reference counting (runs regardless) → Chapter 31. Container-vs-atomic tracking → Chapter 19. Leak diagnosis (`tracemalloc`) → next chapter. `gc.freeze()`/`fork` copy-on-write → Deep E. Weak references (breaking cycles) → Chapter 29.
