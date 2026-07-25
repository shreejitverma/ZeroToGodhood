# Chapter 31: Reference Counting

Chapter 19 established that every object's first field is `ob_refcnt`, and deferred the algorithm that field drives.
This is that algorithm, and it is the beating heart of CPython's memory management, older than the cyclic collector, older than the allocator's arenas, load-bearing for the C-API, and the single biggest reason the GIL was so hard to remove.
**Reference counting** is disarmingly simple: every object counts how many references point at it, the count goes up when a reference is made and down when one goes away, and *the instant it reaches zero the object is destroyed*.
No pauses, no "eventually", no separate collector run for the common case, an object dies the moment its last reference does.

That word *instant* is the whole value proposition, and it distinguishes CPython from Java, Go, and most managed runtimes.
Those use **tracing** garbage collection: garbage accumulates and is reclaimed later, in batches, during a collection pause.
CPython reclaims **deterministically**: a temporary is freed the moment it goes out of scope, a file is closed the moment its handle is dropped, memory is returned promptly and predictably.
The price is a blind spot, reference *cycles*, which the measurement makes vivid: with the cyclic collector switched off, cyclic garbage leaks without bound while acyclic garbage stays perfectly flat.
That blind spot is exactly why CPython also needs the cyclic collector of Chapter 30; this chapter is the primary mechanism it supplements.

**This is the canonical home for the reference-counting algorithm.**
Chapter 19 owns the `ob_refcnt` field and immortality; this chapter owns the algorithm, its determinism, its C-API contract, and its cyclic blind spot. The allocator that hands back freed blocks is Chapter 28; the cyclic collector that catches what cycles hide is Chapter 30; weak references (a reference that does *not* count) are Chapter 29.

## Section index

- **31.1** Deterministic destruction, and the cyclic blind spot
- **31.2** What counts, the C-API contract, and immortality
- **31.3** Measurement: prompt reclamation versus the cyclic leak
- **31.4** Edges and failure modes
- **31.5** Connections
- **31.6** Exercises
- **31.7** Summary and cross-references

Listings live under `code/ch120/` and are re-executed by `make verify` on both verification interpreters.

---

## 31.1 Deterministic destruction, and the cyclic blind spot

```python
# code/ch120/l01_refcounting.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- deterministic: freed at the LAST reference, immediately ---
  del a (b still holds it, so it lives):
  del b (last reference gone):
  A: __del__ runs NOW (refcount hit 0)
--- the refcount tracks references as they come and go ---
  after [x, x]     : refcount rose by 2   (2 refs in the list)
  after del holder : refcount change from baseline is 0   (back to baseline)
  del x:
  X: __del__ runs NOW (refcount hit 0)
--- the blind spot: a reference CYCLE refcounting cannot free ---
  after del n1, n2: no __del__ yet (refcounts stuck at 1 via the cycle)
  gc.collect() (the cyclic collector) reclaims them:
  Node: __del__ (freed by the cyclic collector)
  Node: __del__ (freed by the cyclic collector)
--- the rule ---
  reference counting frees an object the instant its count hits 0
  (deterministic); cycles need the separate cyclic collector
```

**Determinism.**
`A`'s `__del__` runs at exactly the `del b` line, not at `del a` (where `b` still held it), and not at some later collection, *right when the last reference goes away*.
This is the property that makes Python's cleanup predictable: an object's finalizer, a file's close, a lock's release fires promptly at the last reference, so patterns like "the file closes when the `TextIOWrapper` is dropped" work reliably (though `with` is still preferred, §31.4).

**The count tracks references.**
Binding `[x, x]` raises the count by 2 (the list holds two references); `del holder` drops it back.
The absolute number is deliberately *not* shown, because it is not portable, CPython 3.14 counts local-variable references differently from 3.13, so `sys.getrefcount` returns different absolutes on each (this is why the listing reports the stable *delta* against a baseline, the same version-drift discipline as Chapter 19's immortality sentinel).
What is stable and true everywhere is the *behaviour*: references push the count up, dropping them pushes it down, and zero means death.

**The blind spot.**
`n1` and `n2` reference each other, a **cycle**.
After `del n1, n2`, the names are gone but each object is still referenced *by the other*, so both counts sit at 1, never zero, and reference counting **cannot free them**, no `__del__` fires.
They are leaked, held alive only by each other, reachable from nothing.
This is refcounting's one fundamental limitation, and `gc.collect()` (the cyclic collector, Chapter 30) is what finds such islands and reclaims them, the two `Node.__del__`s finally run.
Reference counting handles the overwhelming common case promptly; the cyclic collector exists solely to catch cycles.

---

## 31.2 What counts, the C-API contract, and immortality

Reference counting is not a background process; it is *inline work on every operation*, and understanding what triggers it explains both its cost and its correctness requirements.

A reference is created, and the count incremented, whenever a name, list slot, dict value, instance attribute, function argument, or any other slot is made to point at an object.
It is destroyed, and the count decremented, when that slot is rebound, deleted, or its owner is itself destroyed.
So `y = x`, `lst.append(x)`, `d["k"] = x`, `obj.attr = x`, and `f(x)` all `incref` `x`; `del`, reassignment, `lst.pop()`, and scope exit `decref`.
Every one of these is a `Py_INCREF`/`Py_DECREF` in the C source, a memory write, and the cumulative traffic of those writes is real overhead, small per operation, pervasive across the program.

This is the **C-API contract** that every extension author must honour: a C function that receives a `PyObject *` and keeps it must `Py_INCREF` it, and must `Py_DECREF` everything it owns when done.
Get it wrong in one direction and you **leak** (a count that never reaches zero); get it wrong in the other and you get a **use-after-free** (a count that reached zero too early, freeing an object still in use), the most dangerous class of C bug.
The entire correctness of a CPython extension rests on balancing these increments and decrements, which is why the C-API's ownership rules (borrowed versus new references) are studied so carefully, and why higher-level tools (Cython, pybind11, PyO3) exist largely to manage refcounts for you.

Two facts from Chapter 19 complete the picture.
**Immortal objects** (`None`, `True`, `False`, small ints, interned strings, PEP 683) skip refcounting entirely, their count is a sentinel the interpreter never touches, precisely because incrementing a single shared count on every use of `None` from every thread would be a scalability disaster.
And that disaster is the reason **free-threading** (removing the GIL) is so hard: without the GIL, every `incref`/`decref` on a shared object would need to be an *atomic* operation, which is far slower than a plain memory write, so the free-threaded build uses **biased reference counting** to keep the common single-threaded case cheap (Chapter 30 / the free-threading volume).
Reference counting's simplicity at the object level is paid for by its pervasiveness, and that pervasiveness is what makes it interact with everything from the C-API to the GIL.

---

## 31.3 Measurement: prompt reclamation versus the cyclic leak

**Methodology.** `code/ch120/bench_refcount.py`.
With the cyclic collector **disabled** (`gc.disable()`, leaving only reference counting), a loop of 100,000 temporaries: one version acyclic (each freed when the next is bound), one version cyclic (each references itself).
Peak memory (`tracemalloc`).
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64; the cyclic figure was byte-identical on both interpreters.

| 100,000 temporaries, GC off | peak memory | |
|---|---|---|
| acyclic (refcounting frees each immediately) | ~0.01 MB | one object live at a time |
| cyclic (refcounting cannot free) | 175.5 MB | every object leaked |

The contrast is the entire chapter in two numbers.
The acyclic loop peaks at **one object's worth** of memory (~0.01 MB), because reference counting frees each temporary the *instant* the next iteration rebinds `obj`, the previous dict's count hits zero and it is reclaimed before the next allocation, so only one is ever live.
This is prompt, deterministic, bounded memory with **no GC pause**, the benefit tracing collectors cannot match, they would let the garbage pile up until a collection.
The cyclic loop, with the collector off, **leaks every one** of the 100,000 objects to **175.5 MB** (roughly 30,000x more), because each cycle keeps its own refcount above zero forever.

The lesson is why CPython uses **both** mechanisms.
Reference counting is the primary manager: it reclaims promptly, deterministically, and touches only the objects actually being freed (no whole-heap scan for the common case).
But it is structurally incapable of freeing cycles, so the cyclic collector (Chapter 30) runs periodically to find and reclaim the islands that refcounting misses, in normal operation (GC *enabled*), the cyclic loop would not leak, because the collector sweeps it up.
Disable the collector and you see refcounting's blind spot laid bare.
This division of labour, prompt refcounting plus periodic cycle-collection, is CPython's answer to "reclaim memory promptly *and* completely", and each half covers the other's weakness: refcounting gives determinism the tracing collector lacks, the tracing collector gives cycle-completeness refcounting lacks.

---

## 31.4 Edges and failure modes

**Cycles are not freed by refcounting.** §31.1, §31.3.
Objects referencing each other (directly or through a chain) leak under refcounting alone. The cyclic collector (Chapter 30) reclaims them; do not disable it unless you are certain your workload creates no cycles (and profile if you do).

**`sys.getrefcount` returns a non-portable absolute (and is always one high).**
It counts its own argument (Chapter 19) *and* the absolute differs across versions (3.14 handles local references differently). Reason about *deltas*, never absolutes, and never assert on an exact refcount.

**`__del__` timing is prompt but fragile.** §31.1.
It runs at the last reference for *acyclic* objects, but for objects in a cycle it runs only when the cyclic collector reclaims them (later, and in an unspecified order). Do not rely on `__del__` for critical cleanup; use `with`/context managers (deterministic by construction) or `weakref.finalize` (Chapter 29). A `__del__` that resurrects the object or raises complicates collection further.

**A stray reference keeps an object alive forever.**
The flip side of deterministic freeing: an object lives exactly as long as *something* references it. A forgotten entry in a cache, a registry, a closure, or a module-level list is the classic Python "leak", not a refcounting bug but a logic bug (a reference you did not mean to keep). Use `weakref` for caches that should not keep their values alive.

**C-extension refcount bugs are severe.** §31.2.
An unbalanced `Py_INCREF`/`Py_DECREF` leaks or (worse) frees a live object (use-after-free). This is the dominant class of C-extension bug; prefer tools that manage refcounts (Cython, pybind11, PyO3) over hand-written C-API code.

**Refcount traffic is a real, if small, cost.** §31.2.
Every reference operation is a memory write. In tight loops over many objects, this contributes to why pure-Python numeric code is slow (each operation touches refcounts) and why `array`/NumPy (which avoid per-element objects, Chapter 19) are faster. It is also the crux of the free-threading challenge.

**Deterministic destruction is a portability assumption to avoid.**
CPython frees promptly; PyPy and other implementations use tracing GC and do *not* guarantee prompt `__del__`. Code that relies on "the file closes when the object is dropped" is CPython-specific. Use `with` for portable, deterministic resource management.

---

## 31.5 Connections

**Backward.**
The `ob_refcnt` field this algorithm drives, and immortality (which opts objects out of it), are Chapter 19. The historical introduction of reference counting in Python 1.x is Chapter 2; this is the algorithm it described. The determinism here is why Python's `with`/context-manager idiom and prompt file closing work.

**Forward.**
The **cyclic collector** that reclaims what §31.1 and §31.3 show refcounting cannot, its generational algorithm, `gc` module, and thresholds, is Chapter 30. **Weak references** (a reference that deliberately does *not* increment the count, for caches and back-pointers that must not keep objects alive) are Chapter 29. The **allocator** (`pymalloc`) that actually returns freed blocks to pools is Chapter 28. **Biased reference counting** under free-threading, which changes what `incref`/`decref` cost when the GIL is gone, is the free-threading volume.

**Across books.**
Deterministic reclamation is why **Book I**'s resource management is predictable: a socket, a file, a memory-mapped region, a C buffer is released promptly at its last reference, so a long-running system does not accumulate unreleased handles between GC pauses the way a tracing-GC language can. The order-book system relies on this for its hot-path temporaries, the millions of short-lived objects a matching loop creates are reclaimed immediately (the §31.3 acyclic case), keeping memory flat with no pause, and it is careful to avoid reference cycles (and to break them with `weakref`, Chapter 29) in its long-lived structures so that the cyclic collector rarely has work to do, keeping latency predictable.

---

## 31.6 Exercises

**1. Watch determinism.** Reproduce §31.1's first block: an object with `__del__`, aliased and then `del`'d twice. Confirm `__del__` fires at the *last* `del`, not the first. Explain what "deterministic" means here versus a tracing GC.

**2. Track the count by delta.** Add and remove references to an object (a list, a dict, an attribute) and observe the refcount *delta* (not absolute) via `sys.getrefcount`. Explain why you must use deltas, and what each operation did to the count.

**3. Build and break a cycle.** Reproduce §31.1's cycle. Confirm `__del__` does not fire after `del`, then that `gc.collect()` reclaims it. Then break the cycle manually (`n1.peer = None`) *before* `del` and show refcounting frees it without the collector. Explain both.

**4. See the leak.** Reproduce §31.3 with `gc.disable()`. Confirm acyclic garbage stays flat and cyclic garbage grows. Re-enable `gc` and show the cyclic version no longer leaks. Explain the division of labour.

**5. The design question.** CPython chose reference counting (with a cyclic-collector supplement) over pure tracing GC. Argue the trade, using §31.3 (prompt determinism) and §31.2 (the C-API contract, the free-threading difficulty). What does CPython gain, what does it pay, and why does the free-threaded build (biased refcounting) make the trade sharper rather than settling it?

---

## 31.7 Summary and cross-references

- **Reference counting** is CPython's primary memory manager: every object counts its references, and it is **destroyed the instant the count reaches zero**, promptly and **deterministically** (`__del__` fires at the last reference for acyclic objects), no GC pause.
- References are created/destroyed by binding, appending, attribute/dict assignment, argument passing, and their inverses, each an inline `Py_INCREF`/`Py_DECREF`. The **C-API contract** (balance them) is what makes extensions correct; imbalance leaks or frees-too-early.
- The **blind spot is cycles**: objects referencing each other keep their counts above zero forever and **leak** under refcounting alone. The **cyclic collector** (Chapter 30) reclaims them.
- **Measured (GC off):** acyclic garbage stays flat at **one object** (~0.01 MB, freed immediately) while cyclic garbage leaks to **175.5 MB** (~30,000x). CPython uses **both** mechanisms: prompt refcounting plus periodic cycle-collection.
- **Edges:** `getrefcount` absolutes are non-portable (use deltas); rely on `with`, not `__del__`, for cleanup; a stray reference is a logic-level leak (use `weakref`); refcount traffic is the crux of the free-threading challenge.

**Cross-references.** The `ob_refcnt` field and immortality → Chapter 19. Historical origin → Chapter 2. The cyclic collector → Chapter 30. Weak references → Chapter 29. The allocator → Chapter 28. Biased refcounting under free-threading → the free-threading volume.
