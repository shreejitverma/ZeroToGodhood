# Chapter 30: The Cyclic Collector Algorithm

Chapter 3 introduced the cyclic collector as a fact: reference counting cannot free a cycle, so a
separate collector finds and breaks unreachable cycles. Chapter 28 placed it in the memory system, and
Chapter 29 showed how to avoid feeding it. This chapter answers the question those left open: *how does
the collector find an unreachable cycle at all?* The problem is genuinely hard. Reference counts cannot
tell it anything, because a cycle keeps its own members' counts above zero precisely when it is
unreachable. Looking at `refcount == 0` finds nothing; the whole point is that the garbage has nonzero
counts.

The collector's answer is an elegant algorithm called **copy-and-subtract**, and it is the mechanism
this chapter dissects. It works by computing, for each object in a candidate set, how many references
to it come from *outside* the set versus *inside* it. An object referenced only from inside the set is
part of unreachable garbage; an object referenced from outside is a live root. This chapter shows the
algorithm, the traversal it depends on, and the optimizations (container-only tracking, tuple
untracking) that keep its cost proportional to the object graph's real complexity rather than to every
object in the program.

## Section index

- **30.1** The problem: refcounts cannot find a dead cycle
- **30.2** The traversal: `tp_traverse` and tracked objects
- **30.3** Copy-and-subtract
- **30.4** Optimizations: container-only tracking and tuple untracking
- **30.5** Measurement: collection cost scales with live objects
- **30.6** Edges and failure modes
- **30.7** Connections
- **30.8** Exercises
- **30.9** Summary and cross-references

Listings live under `code/ch030/` and are re-executed by `make verify` on both interpreters.

---

## 30.1 The problem: refcounts cannot find a dead cycle

Consider two objects, `a` and `b`, each referencing the other, with no reference from anywhere else.
They are unreachable, no code can ever touch them again, so they are garbage. But `a`'s reference count
is 1 (from `b`) and `b`'s is 1 (from `a`). Refcounting's rule, "free when the count hits zero," never
fires, because neither count ever hits zero. The garbage is invisible to the mechanism that frees
everything else.

So the collector cannot use reference counts directly. It needs to distinguish "referenced from live
code" from "referenced only by other garbage," and a raw refcount conflates the two: `b`'s count of 1
looks identical whether that 1 reference comes from a live variable or from the dead `a`. The collector
must look *inside* the reference count and separate its sources. That is what copy-and-subtract does.

---

## 30.2 The traversal: `tp_traverse` and tracked objects

To separate a reference count's sources, the collector must walk the reference graph: for each object,
which objects does it point at? Every container type implements a `tp_traverse` slot that reports its
references, and `gc.get_referents` drives it:

```python
# code/ch030/l01_traversal.py
```

Verified output (CPython 3.13.5):

```text
--- tp_traverse: what an object references (get_referents) ---
  a references: ['Node', 'str', 'type']
--- the reverse: who references b (get_referrers) ---
  number of objects referencing b: 2
--- only containers are tracked; atomic objects never are ---
  is_tracked(Node instance): True
  is_tracked(42)           : False
  is_tracked('text')       : False
  is_tracked([1, 2])       : True
```

`get_referents(a)` reports what `a` points at (its `Node` peer, its name `str`, and its type); this is
`tp_traverse` exposed. And the collector only tracks *containers*, objects that can reference other
objects. An `int` or a `str` is atomic: it cannot point at another object, so it can never be part of a
cycle, so the collector never tracks it (`is_tracked(42)` is `False`). This is the first cost control:
the collector's work is proportional to the number of *containers*, not to every object in the program,
and Chapter 19 measured that most objects (integers, strings) are atomic.

---

## 30.3 Copy-and-subtract

The algorithm runs over the tracked objects of the generation being collected, in four steps:

1. **Snapshot.** Copy each tracked object's real reference count into a private `gc_refs` field.
2. **Subtract internal references.** Traverse every tracked object's references (`tp_traverse`); for
   each reference to another object *in the set*, decrement that target's `gc_refs`. After this pass,
   each object's `gc_refs` counts only references from *outside* the set.
3. **Partition.** Objects with `gc_refs > 0` are referenced from outside the set, so they are reachable
   roots; they and everything they reach are *live*. Objects still at `gc_refs == 0` are referenced only
   from within the set, so they are unreachable garbage.
4. **Reclaim.** Break the garbage cycles (`tp_clear`) and free them.

```python
# code/ch030/l02_copy_and_subtract.py
```

Verified output (CPython 3.13.5):

```text
--- copy-and-subtract in one sentence ---
  gc_refs = real refcount, minus references from within the tracked set.
  A cycle's objects are referenced only from within the set, so their
  gc_refs reaches 0 and they are identified as unreachable garbage.
  gc.collect() reclaimed the a<->b cycle: 2 objects
```

Trace it on `a <-> b` with no outside reference. Snapshot: both have `gc_refs == 1`. Subtract: `a`
references `b`, so `b`'s `gc_refs` drops to 0; `b` references `a`, so `a`'s drops to 0. Partition: both
are at 0, referenced only from within the set, so both are garbage. `gc.collect()` reclaims exactly the
2 objects. Now add an outside reference, say a live variable pointing at `a`: `a`'s snapshot is 2, one
internal reference is subtracted leaving `gc_refs == 1`, so `a` is a root, and `b`, reachable from `a`,
is kept live too. The algorithm found the difference a raw refcount could not.

---

## 30.4 Optimizations: container-only tracking and tuple untracking

Two optimizations keep the collector's cost down. The first is container-only tracking (§30.2): atomic
objects are never scanned. The second is subtler and worth seeing:

```text
--- the tuple-untracking optimization ---
  (1, 2, 3) tracked when created: False
  (1, 2, 3) tracked after a collection: False
  ([1], 2) stays tracked: True (it holds a mutable)
```

A tuple is a container, so in principle it should be tracked. But a tuple whose elements are *all*
immutable and themselves untracked can never be part of a cycle, an all-integer tuple has nothing that
could point back at it. So the collector *untracks* such tuples: `(1, 2, 3)` is not tracked at all,
while `([1], 2)`, which holds a mutable list, stays tracked. This matters at scale: a program with large
constant tuples of numbers (lookup tables, coordinates, configuration) pays the collector nothing for
them, because they are untracked and never enter a scan. The same optimization applies to dicts and
other containers that provably cannot cycle. It is the collector refusing to pay for objects it can
prove are cycle-free.

---

## 30.5 Measurement: collection cost scales with live objects

The copy-and-subtract pass visits every tracked object in the scanned generation. So a collection's cost
is proportional to how many tracked objects are *alive*, not to how much garbage there is, live objects
are exactly the ones the algorithm must prove reachable.

**Methodology.** `code/ch030/bench_collection_cost.py`. `gc.collect()` over live heaps of increasing
size (each object a small dict, so tracked). `min` of five runs. CPython 3.13.5, Apple M3 Pro, macOS
27.0, arm64.

| live tracked objects | full collection |
|---|---|
| 50,000 | 0.72 ms |
| 200,000 | 1.65 ms |
| 800,000 | 5.66 ms |

The collection time grows **roughly linearly** with the live tracked-object count: 4x the objects is
roughly 3.4x the time (the pass plus some fixed overhead). The lesson is counterintuitive until you see
the algorithm: **garbage is cheap to reclaim; live objects are what a collection pays for**, because it
must traverse them to prove they are reachable. A program with a large, long-lived heap pays that
traversal on every full collection, for objects that are never going to be garbage.

This is the precise justification for `gc.freeze()` (Chapter 3, §3.5). Freezing moves the permanent heap
into a generation the collector never scans, so a full collection only traverses the young, churning
generation, not the megabytes of startup state that will live forever. Chapter 3 measured that freezing
before a fork helps; this chapter is why, the frozen objects are removed from the linear cost this
benchmark demonstrates.

---

## 30.6 Edges and failure modes

**Expecting garbage volume to drive cost.** §30.5. Collection cost scales with *live* tracked objects,
not garbage. A big live heap is expensive to collect even if it produces no garbage; freeze it.

**Assuming all containers are tracked.** §30.4. A tuple or dict of only immutables is untracked and
invisible to the collector. Do not rely on a constant tuple being scanned.

**`get_referrers` in production.** It is a debugging tool that walks the whole heap; it is expensive and
can keep objects alive by referencing them. Use it to diagnose a leak, not in hot code.

**Finalizers changing the graph.** A `__del__` that resurrects an object or creates new references
during collection complicates the algorithm; PEP 442 (Chapter 3) made this safe but it is still a place
to tread carefully. Keep finalizers simple.

**Uncollectable objects.** If the collector cannot safely reclaim something (rare since PEP 442), it goes
to `gc.garbage`. A growing `gc.garbage` is a real leak; monitor it in a long-running process.

---

## 30.7 Connections

**Backward.** The cycle problem and the `gc.disable`/`freeze` levers are Chapter 3, whose measurements
§30.5 now explains from the algorithm. The `PyGC_Head` that threads tracked objects into the collector's
lists, and the object header, are Chapter 19. The allocator that reclaims the freed blocks is Chapter
28. Weak references, which keep objects out of the tracked set entirely, are Chapter 29.

**Forward.** The container growth policies and the tuple/dict internals that determine trackability are
**Deep Q**. The free-threaded build changes the collector's synchronization and is Chapter 26 and **Deep
L**. Memory profiling and leak-finding with `tracemalloc` and `gc` are **Deep K**.

**Across books.** The collector's linear-in-live-objects cost is the quantitative reason Book II holds
large data across the **Book I** boundary as buffers rather than object graphs: a million price levels
as Python objects is a million tracked containers the collector traverses on every full pass, while the
same data as one NumPy array or C++ buffer is untracked and invisible to the collector, one allocation
the GC never scans. The order-book capstone's memory design is this measurement applied. **Deep M** owns
the boundary; this chapter is the collector cost that motivates it.

---

## 30.8 Exercises

**1. Trace copy-and-subtract by hand.** Draw three objects in a cycle with one external reference to one
of them. Compute each object's `gc_refs` after the snapshot and subtract steps, and identify which are
roots and which are garbage. Then build it and confirm `gc.collect()` reclaims the right count.

**2. Find the untracking boundary.** Determine, using `gc.is_tracked`, exactly which tuples are tracked:
`(1, 2)`, `([1], 2)`, `((1, 2), 3)`, `(object(),)`. Explain each result in terms of whether the tuple can
possibly participate in a cycle.

**3. Measure your own heap.** Reproduce §30.5's benchmark, then repeat it with the heap `gc.freeze()`n
and show the collection cost drops. Explain the difference in terms of what the collector traverses in
each case.

**4. Catch a real leak.** Build a structure that leaks (an uncollectable cycle, or an ever-growing
container), and use `gc.get_referrers` and `gc.garbage` to find what holds it. Explain how the tools
locate the leak and why they are too expensive to leave running.

**5. The design question.** Copy-and-subtract requires two full passes over the tracked set (snapshot,
then subtract) plus a partition. Argue why this is worth it over the alternative of tracing from known
roots (as a tracing GC does), given Python's refcounting foundation. Your answer must address why Python
uses refcounting *plus* a cyclic collector rather than a tracing GC alone, and what copy-and-subtract
exploits that a from-roots trace would not.

---

## 30.9 Summary and cross-references

- Reference counts **cannot find a dead cycle**, because a cycle keeps its own members' counts above
  zero. The collector uses **copy-and-subtract**: snapshot each tracked object's refcount, subtract
  references from within the tracked set, and the objects left at zero are referenced only internally,
  hence unreachable garbage.
- The collector walks the graph through **`tp_traverse`** (`gc.get_referents`) and tracks only
  **containers**; atomic objects (`int`, `str`) are never tracked because they cannot cycle.
- **Optimizations:** a tuple (or dict) of only immutables is **untracked**, so large constant tuples of
  numbers cost the collector nothing.
- **Measured:** a full collection's cost scales **linearly with live tracked objects** (0.72 ms at 50k,
  5.66 ms at 800k), because the algorithm must traverse the live objects to prove them reachable. This
  is why `gc.freeze()` (Chapter 3) helps: it removes the permanent heap from every scan.

**Cross-references.** The cycle problem and GC levers → Chapter 3. The GC header and object model →
Chapter 19. The allocator → Chapter 28. Weak references → Chapter 29. Container trackability → Deep Q.
Free-threading's collector → Chapter 26 and Deep L. Memory profiling → Deep K. The large-data boundary →
Deep M.
