# Chapter 94: Biased Reference Counting and Immortality

Chapter 2 established the oldest invariant in CPython: every object carries a count of its references, and the count reaching zero frees it. Chapter 93's table said that keeping `ob_refcnt += 1` safe was the first of the GIL's five jobs. This chapter is what replaced it: the reference count itself was rebuilt, split into an owner-thread field written without atomics and a shared field written with them, with the busiest objects in the interpreter opting out of counting entirely.

The redesign is measurable from pure Python, and the measurement is the chapter's spine. Four threads doing identical work, differing only in *whose* object they hold references to: an object each thread created itself costs **29.7 ms**; the same object owned by another thread, **~5x** that; one object shared by all four, **~17x**, and `None`, **1.02x**, indistinguishable from private. On the GIL build all four rows tie at 88 ms, because one lock charges one price.

That fan-out is the free-threaded build's real cost model, and it produces this volume's first design rule: **allocate where you use, and share immortals or share deliberately.**

**This is a Deep L chapter.**
Deep B owns reference counting and the collector as mechanisms; Chapter 81 owns refcounts across the C boundary, where immortality was first measured. This chapter owns what a refcount *is* on the free-threaded build, and what each kind of reference costs.

## Section index

- **94.1** What is observable: immortals, headers, and what `getrefcount` no longer sees
- **94.2** The redesigned count: bias, the shared field, deferral, immortality
- **94.3** Measurement: the price of a reference, by ownership
- **94.4** Edges and failure modes
- **94.5** Connections
- **94.6** Exercises
- **94.7** Summary and cross-references

Listings live under `code/ch175/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 94.1 What is observable: immortals, headers, and what `getrefcount` no longer sees

```python
# code/ch175/l01_refcounts_without_the_gil.py
```

Verified output (CPython 3.13.5):

```text
--- immortality: the objects that opted out of counting ---
  1,000 new references to None moved its refcount : False
  1,000 references to an ordinary object moved it by : +1,000
  None, True, False, small ints, and interned strings are immortal on
  every current build (PEP 683); incref and decref on them are no-ops.
  built FOR free-threading: the most-shared objects generate no
  refcount writes, so they cannot become cache-line contention points
--- the object header, by build ---
  sizeof(object())          : 16 bytes
  sizeof([]) (GC-tracked)   : 56 bytes
  sizeof(two-slot instance) : 48 bytes
--- container references are still exact; frame references are not ---
  getrefcount(fresh local object) : 2
  append moves it by exactly +1   : True
  pop restores it                 : True
```

Two lines change across the matrix, and each is a chapter-sized fact. On both 3.14 builds, the frame line becomes Verified output (CPython 3.14.6, and identically on 3.14t):

```text
  getrefcount(fresh local object) : 1
```

And on the free-threaded build alone, the header line becomes Verified output (CPython 3.14t):

```text
  sizeof(object())          : 32 bytes
```

**The immortality block is identical everywhere, which is the point of immortality.**
A thousand new references to `None` move its count by nothing, on every current build, because PEP 683 pinned the most-shared objects, `None`, `True`, `False`, small integers, interned strings, at a sentinel where incref and decref are no-ops. Chapter 81 measured this from the C side and promised the real purpose here: **an object no thread counts is an object no threads contend on**, and §94.3's `None` row is that purpose realised.

**The header arithmetic is a small masterpiece of accounting.**
A bare `object()` doubles, 16 to 32 bytes: the free-threaded header adds the owning thread id, the split refcount fields, a per-object mutex (Chapter 96's subject), and GC bits. But the list stays at 56 and the slotted instance at 48, because the GIL build's separate 16-byte GC pre-header (Deep B) is *gone* on the free-threaded build, absorbed into the new header's bits. So GC-tracked objects, which is most objects that matter, pay nothing; only small non-GC objects like `object()`, floats, and ints pay the doubling. Chapter 89's memory arithmetic survives the new build better than the headline "headers doubled" suggests.

**And the frame line is 3.14 changing what `getrefcount` reports on *both* builds.**
3.13 reports 2 for a fresh local: the object's reference from the local variable, plus `getrefcount`'s own argument. 3.14 reports 1, because frames now hold **deferred stack references** (part of the same family of changes as biased counting) that the count does not include. The container arithmetic stays exact everywhere, `append` is +1, `pop` restores, which is the enduring lesson: `getrefcount` is a diagnostic whose baseline moves between versions, never a contract (§94.4).

---

## 94.2 The redesigned count: bias, the shared field, deferral, immortality

On the free-threaded build the object header is (illustrative, CPython 3.14, `Include/object.h`, `Py_GIL_DISABLED`; field layout is implementation detail and has already changed once):

```c
struct _object {
    uintptr_t      ob_tid;         /* owning thread's id                 */
    uint16_t       ob_flags;
    PyMutex        ob_mutex;       /* per-object lock (Chapter 96)       */
    uint8_t        ob_gc_bits;     /* GC tracking; replaces PyGC_Head    */
    uint32_t       ob_ref_local;   /* owner thread's count: no atomics   */
    Py_ssize_t     ob_ref_shared;  /* everyone else's count: atomic      */
    PyTypeObject  *ob_type;
};
```

**Biased reference counting is a bet on locality.**
Most objects are only ever touched by the thread that created them, so that thread, identified by `ob_tid`, gets a private counter it may increment and decrement with plain instructions, exactly as cheap as the GIL build's. Every other thread must use atomic operations on `ob_ref_shared`. The object dies when the two counts, reconciled, reach zero; when the owning thread exits, or the shared count goes negative, ownership is merged and the object falls back to purely atomic counting. The bet's payoff is §94.3's bottom row; the bet's loss, an object biased to a thread that no longer touches it, is the `foreign` row.

**Deferred reference counting removes the counts the bet cannot win.**
Some objects are, by construction, touched constantly by every thread: modules, top-level functions, classes, the code objects behind them. Biasing them helps no one. The free-threaded build marks them for **deferred counting**: most incref/decref pairs on them from the interpreter loop are simply skipped, and their true liveness is settled by the garbage collector (Chapter 95). This is also the family of machinery behind 3.14's frame behaviour in §94.1: references held from the evaluation stack can be deferred on both builds, which is why `getrefcount` reports one less.

**Immortality removes the counts that must never be contended.**
`None` is passed, returned, and compared everywhere; if every `return None` in a hundred threads wrote one shared cache line, the line would ricochet between cores and the interpreter would serialise on its own most common value. PEP 683's sentinel makes those objects write-free. §94.3 shows the difference between an immortal and a merely shared object is a factor of **~17**.

**The hierarchy, then, is a price list, and the interpreter walks it for every reference:**
immortal, free; owned, plain arithmetic; foreign, atomic; contended, atomic plus coherence traffic. The GIL build has one price for everything, which was cheap per operation and cost the whole machine its parallelism. The free-threaded build has four prices, and the rest of this volume, allocator (95), container locks (96), specialization (97), is the engineering required to keep the common paths at the cheap end of the list.

---

## 94.3 Measurement: the price of a reference, by ownership

**Methodology.** `code/ch175/bench_refcount_contention.py`.
Four threads, each doing one million `append`/`pop` pairs into a **private** list; the appended object is the only variable, because appending increfs it and popping decrefs it. `min` of 5, within-build ratios only.
CPython 3.14.6, both builds; Apple M3 Pro, macOS 27.0, arm64.

**The free-threaded build.**

| the object being referenced | time | vs own |
|---|---|---|
| own object (thread-created) | 29.7 ms | 1.00x |
| foreign object, unshared (main-thread-owned) | 146.2 ms | **~5x** |
| one object shared by all four threads | 503.0 ms | **~17x** |
| `None` (immortal) | 30.2 ms | 1.02x |

**The GIL build, same program.**

| the object being referenced | time | vs own |
|---|---|---|
| own object | 87.9 ms | 1.00x |
| foreign object, unshared | 87.3 ms | 0.99x |
| one object shared by all | 87.0 ms | 0.99x |
| `None` (immortal) | 86.1 ms | 0.98x |

**The GIL table is flat because one lock charges one price**; the work re-serialises and ownership is irrelevant. The free-threaded table is §94.2's price list with numbers attached. The `foreign` row deserves emphasis because no *contention* is involved: each worker hammers a different main-thread-owned object, and the ~5x is the pure cost of atomic operations replacing plain ones. The `shared` row adds the cache line bouncing between four cores, and the `None` row deletes the writes entirely and lands back at the owned price.

**Two design rules fall out, and they are the chapter's deliverables.**
First, **allocate where you use**: an object built by the main thread and handed to a worker pays the atomic path forever, even with no sharing, because the bias belongs to the creating thread and does not migrate. Builders that construct a scene graph in main and fan work out to threads inherit a tax the profiler will show as "everything is a little slow". Second, **hot shared objects are the new GIL**: four threads on one object serialised most of their refcount traffic at ~17x; the fix is per-thread copies, immortal constants, or not holding references at all (borrow via arguments rather than storing).

**Book I**'s cousin of this table is `shared_ptr` against a raw pointer: its atomic control-block traffic is exactly `ob_ref_shared`, and C++ engineers learned decades ago to pass `const&` in hot paths precisely to avoid it. Python's frames learned the same trick in 3.14 (deferred stack references), which is a rare case of the two books' optimisations converging on the identical idea at the identical layer.

---

## 94.4 Edges and failure modes

**The bias does not migrate.** §94.3.
An object's owner is the thread that created it, for life (merging on owner exit demotes it to purely atomic, which is worse, not better). The handoff pattern, main constructs, workers consume, is the pattern the design is worst at. Restructure so workers construct what workers use, or accept the ~5x on the references involved.

**`getrefcount` is a diagnostic, never a contract.** §94.1.
Its baseline differs between 3.13 and 3.14 (deferred stack references), and on the free-threaded build the reported number is a reconciliation of two fields that other threads are concurrently changing. Test invariants with deltas under your own control (the listing's append/pop), not with absolute values, and expect deltas to break too for deferred objects: a function or class may show no movement where an ordinary object shows +1.

**Deferred objects die late, deliberately.**
Functions, classes, and modules under deferred counting are reclaimed by the collector (Chapter 95), not at the instant their last reference drops. Code that relies on `__del__` running at a precise refcount-zero moment, Deep B's warning, is wrong on the free-threaded build for exactly the objects most likely to hold interesting resources. Use context managers; that advice has now survived every build of every version in this book.

**Ordinary objects still die promptly.**
The redesign did not make CPython a deferred-everything runtime: a plain object whose owned and shared counts reach zero is freed then and there, and RAII-style idioms on instances keep working. The deferral is targeted at the objects whose counting was pure contention.

**Immortality is one-way and version-scoped.**
Objects the interpreter immortalises stay immortal for the process; the *set* of immortals (and the sentinel's value, Chapter 19 measured it changing between 3.13 and 3.14) is an implementation detail. Do not write code that detects or depends on immortality; write code that shares immutable constants, and the interpreter will do the right thing on every build.

**Old wheels compiled `Py_INCREF` inline, which is why there is a `t` ABI.**
A GIL-build extension has non-atomic increments baked into its machine code; running it against split refcounts would corrupt counts immediately. That, more than any API difference, is why `cp314t` wheels are a separate universe (Chapters 82 and 93) and why importing a non-`t` wheel re-enables the GIL rather than gambling.

**And false sharing exists below the level Python can see.**
Two unrelated hot objects allocated adjacently can share a cache line, making their owners pay contention with no shared object in the program. Chapter 95's allocator design (per-thread heaps) makes this rare, but a profiler showing contention with no visible sharing has this as a candidate; the fix is padding or allocation-site separation, both C-level concerns flagged here for honesty.

---

## 94.5 Connections

**Backward.**
`ob_refcnt` as the oldest invariant is Chapter 2; the object header it lives in is Chapter 19, whose immortal-sentinel measurement this chapter's header table extends. Reference counting and the cyclic collector as mechanisms are Deep B (the GC pre-header this build absorbed is Chapter 28's diagram). Refcounts across the C boundary, owned versus borrowed, and the immortality measurement are Chapter 81; the ABI flags that keep old wheels out are Chapter 82. The volume map giving this chapter its place is Chapter 93.

**Forward.**
The collector that settles deferred counts, and the allocator whose per-thread heaps make bias pay, are Chapter 95. The per-object mutex sitting in the new header is Chapter 96. What all this machinery costs the single-threaded interpreter, and how 3.14 clawed it back, is Chapter 97. The correctness discipline for code that shares, Chapter 99, leans directly on this chapter's price list, and Chapter 100 prices whole architectures with it.

**Across books.**
`ob_ref_shared` is a `std::atomic<ssize_t>`; the biased fast path is the single-threaded `shared_ptr` optimisation C++ libraries have shipped for years; deferred counting is a cousin of hazard pointers. **Book I** avoids the entire subject in its hot path by using value semantics and arena allocation, no counted references at all, and that remains the endgame this volume's Chapter 100 points at: the cheapest reference count on any build is the one the design never takes.

---

## 94.6 Exercises

**1. Reproduce the price list.** Run `bench_refcount_contention.py` on both builds. Then extend it with 8 and 16 threads on the shared row and report how the ~17x scales with contenders.

**2. Find the bias crossover.** Vary the fraction of appends that target a foreign object from 0% to 100% and measure the curve on the t-build. State the fraction at which a mixed workload loses half the owned-path advantage.

**3. Fix a handoff.** Write the anti-pattern: main builds 100,000 small objects, four workers process them. Measure. Restructure so workers build their own quarter, measure again, and report the difference as a fraction of total runtime.

**4. Observe deferral.** On 3.14, show that `sys.getrefcount` of a module-level function does not move when you create and destroy references that would move an ordinary object's count. State what this breaks in refcount-based testing.

**5. The immortal audit.** For `None`, `True`, `0`, `256`, `257`, `"a"`, and an f-string result, report which are immortal on each interpreter you have (by the moved-refcount test, not by reading the sentinel). Explain the 256/257 boundary from Chapter 89.

**6. The design question.** Biased counting fixes the bias at creation and never migrates it; an alternative design would move ownership to the most recent frequent toucher. Argue CPython's choice: what migration would cost on every incref (a check that is currently free), how the merge-on-owner-exit path bounds the damage, and why "allocate where you use" is a teachable rule while "the runtime will adapt" is not. Then find the workload shape where migration would win decisively, and note which chapter of this volume would have to measure it.

---

## 94.7 Summary and cross-references

- **The refcount was split**: an owner-thread field written plainly, a shared field written atomically, reconciled at death. The owner is the creating thread, for life.
- **The price list, measured on 3.14t**: owned 29.7 ms, foreign **~5x**, contended-shared **~17x**, immortal 1.02x, for identical work. The GIL build charges one flat price (~88 ms) for all four.
- **Allocate where you use**; the handoff pattern pays the atomic path with zero sharing. **Hot shared objects are the new GIL**; share immortals or share deliberately.
- **Immortality's purpose is delivered here**: objects nobody counts are objects nobody contends on, and the difference is the ~17x between the `shared` and `None` rows.
- **Headers: `object()` doubles to 32 bytes on the t-build, but GC-tracked objects break even** because the separate GC pre-header was absorbed. Chapter 89's arithmetic mostly survives.
- **`getrefcount` baselines moved in 3.14 on both builds** (deferred stack references) and deferred objects (functions, classes, modules) both under-report and die late, at the collector, not at zero. It is a diagnostic, not a contract; resource lifetime belongs to context managers.
- **Old wheels have non-atomic increments compiled in**, which is the deep reason for the separate `t` ABI and the silent GIL re-enable on legacy imports.

**Cross-references.** The invariant → Chapter 2. The header and the sentinel → Chapter 19. Refcounting and the GC pre-header → Deep B. The C boundary's owned/borrowed contract and immortality measured → Chapter 81. The `t` ABI → Chapter 82. The volume map → Chapter 93. The collector and allocator → Chapter 95. Per-object locks → Chapter 96. Single-threaded cost → Chapter 97. Correctness under sharing → Chapter 99.
