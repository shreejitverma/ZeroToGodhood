# Chapter 29: Weak References

A tree structure is the most natural thing in the world to build, and one of the easiest ways to create
a memory leak in a reference-counted language. A parent holds a list of children, and each child holds
a reference back to its parent so it can walk up the tree. That back-reference completes a cycle:
parent references child, child references parent, and neither's reference count ever reaches zero even
after every external reference is gone. Reference counting (Chapter 19) cannot reclaim it. The cyclic
collector (Chapters 3 and 28) can, but only when it next runs, which means the memory sits allocated
until a collection, and in a latency-sensitive program that collection is a pause you did not schedule.

The fix is to make the back-reference *not count*. A **weak reference** refers to an object without
contributing to its reference count, so the parent-child cycle is broken: when the last strong
reference to the parent goes away, its count reaches zero and refcounting reclaims it immediately, no
collector needed. This chapter is the mechanism, its toolkit (`weakref.ref`, callbacks, and the weak
containers), and an honest measurement of what it costs, because a weak reference is a correctness tool
with a real price, not a free optimization. It completes the memory-reclamation thread: refcounting
(Chapter 19) frees the acyclic, the collector (Chapter 28) frees the cyclic, and weakref lets you avoid
creating the cyclic in the first place.

## Section index

- **29.1** The problem: the back-reference cycle
- **29.2** Weak references break the cycle
- **29.3** The weakref toolkit
- **29.4** Measurement: what a weak reference costs
- **29.5** Edges and failure modes
- **29.6** Connections
- **29.7** Exercises
- **29.8** Summary and cross-references

Listings live under `code/ch029/` and are re-executed by `make verify` on both interpreters.

---

## 29.1 The problem: the back-reference cycle

Reference counting reclaims an object the instant nothing refers to it. A cycle defeats that: each
object in the cycle is referred to by another object in the cycle, so every count stays above zero even
when the whole cycle is unreachable from the rest of the program. A parent-child structure with a child
that points back to its parent is the textbook case, and it is not an exotic pattern, it is how you
build trees, doubly-linked lists, graphs, observer registries, and GUI widget hierarchies.

The cyclic collector (Chapter 28) exists precisely to reclaim such cycles, and it does. But it does so
*eventually*, on its own schedule, and Chapter 3 measured the cost of that: churning cycles is where the
collector's work accumulates, and a latency-sensitive program pays the collection as an unscheduled
pause. If you could keep refcounting able to reclaim the structure, the collector would never need to
touch it. That is what a weak reference buys.

---

## 29.2 Weak references break the cycle

A weak reference points at an object without incrementing its reference count. Make the child's
back-reference weak, and the cycle is gone: the parent's count reflects only the strong references, so
when they vanish it drops to zero and refcounting reclaims the parent (and then the child) immediately.

```python
# code/ch029/l01_weakref.py
```

Verified output (CPython 3.13.5):

```text
--- a strong parent<->child cycle: refcounting cannot reclaim it ---
  after 'del p, c': nothing freed yet (the cycle holds them up)
  running gc.collect() ...
  freed strong-parent
  freed strong-child
--- a WEAK back-reference: refcounting reclaims immediately ---
  'del wp, wc' frees both at once, before any collection:
  freed weak-parent
  freed weak-child
  (both freed above; no gc.collect was needed)
```

The contrast is the whole point. In the strong version, `del p, c` frees *nothing*, the `__del__`
finalizers do not fire, until `gc.collect()` runs and breaks the cycle. In the weak version, `del wp,
wc` frees *both immediately*, the finalizers fire on the spot, before any collection, because the weak
back-reference never held the parent's count above zero. The reclamation is not just faster; it is
*deterministic*, it happens at a point in the program you can see, rather than whenever the collector
decides to run. For an object holding a scarce resource (a file, a socket, a lock), that determinism is
the difference between releasing it now and releasing it at an unpredictable later moment.

---

## 29.3 The weakref toolkit

`weakref` provides more than a bare reference. `weakref.ref(obj)` returns a callable that yields the
object while it lives and `None` after; a callback fires when the referent dies; and the weak containers
hold their members weakly:

```python
# code/ch029/l02_weakref_flavors.py
```

Verified output (CPython 3.13.5):

```text
--- a bare weakref is alive until the referent is reclaimed ---
  r() while alive: r1
  r() after the target is freed: None
--- a callback fires when the referent dies ---
  callback record: ['callback fired']
--- WeakValueDictionary: entries vanish when nothing else holds them ---
  keys right after insert: ['kept']
  keys after collection   : ['kept'] (transient dropped itself)
```

A bare `weakref.ref` returns the object or `None`, so you always check before use. A callback (the
second argument to `ref`) fires when the referent is reclaimed, useful for cleanup or bookkeeping that
must run on an object's death. And the weak containers are the everyday application: a
`WeakValueDictionary` holds its *values* weakly, so an entry disappears automatically when nothing else
references the value. The listing shows `transient` (with no other reference) dropping out of the cache
after collection while `kept` (still referenced) remains. This is the canonical **caching pattern**: a
`WeakValueDictionary` caches objects without keeping them alive, so a cached value is reclaimed as soon
as the rest of the program stops using it, and its cache entry vanishes with it, no manual eviction, no
leak. (The callback in the listing required keeping the `weakref` object itself alive; a weakref whose
own reference is dropped can be collected before its referent, and then the callback never fires, an
edge worth remembering.)

---

## 29.4 Measurement: what a weak reference costs

It is tempting to think a weak back-reference is *faster* than a strong one because it avoids the
collector. It is not, and measuring it corrects the intuition.

**Methodology.** `code/ch029/bench_weakref_gc.py`. A per-reference comparison: a plain attribute
assignment (strong reference) versus creating a `weakref.ref` (weak reference). `min` over 15 batches;
within one interpreter; CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64. Reproduced across runs.

| reference | ratio |
|---|---|
| strong (attribute assignment) | 1.00x |
| weak (`weakref.ref`) | **2.1x** |

Creating a weak reference costs about **2.1x** a plain attribute assignment, because it allocates a
weakref object and registers it with the referent. So a weak back-reference is *slower* per operation,
not faster. Its value is not throughput; it is that reclamation is immediate and deterministic (§29.2)
and that the collector never has to trace the object.

This is Chapter 3's finding from the other side. Chapter 3 measured that the cost of cycle-churn is the
collector's tracing, and that the fix is usually *not* to tune the collector but to *not create the
cycle*. Weakref is how you avoid the parent-child cycle that is the usual culprit, and this measurement
is the price of that avoidance: a small per-reference cost, paid to keep the object out of the collector
entirely. Use it deliberately, to break a genuine cycle, to build a non-retaining cache, to observe an
object's death, not scattered through a hot path in the belief that it is free.

---

## 29.5 Edges and failure modes

**Not every object is weak-referenceable.** A class with `__slots__` cannot be the target of a weak
reference unless `'__weakref__'` is in its slots (this chapter's benchmark had to add it). Built-in
types like `int`, `str`, and `tuple` are not weak-referenceable at all. Check before designing around
weakrefs.

**A dropped weakref does not fire its callback.** §29.3. If the `weakref` object itself is garbage
collected before its referent, the death callback never runs. Keep the weakref (or use a weak container)
if you rely on the callback.

**Weak references are not free.** §29.4. At ~2.1x a plain reference, they are a determinism tool, not a
speed optimization. Do not scatter them through hot code.

**A weakref can go dead between check and use.** `r()` may return the object one moment and `None` the
next if the last strong reference is dropped in between. Bind the result to a local and check *it*, do
not call `r()` twice and assume both return the same thing.

**`WeakValueDictionary` entries vanish silently.** §29.3. That is the feature, but it means an entry you
inserted may be gone by the time you look, if nothing else held the value. Hold a strong reference to
anything you need to keep.

---

## 29.6 Connections

**Backward.** Reference counting, which weakref keeps able to reclaim, is Chapter 19. The cyclic
collector that weakref lets you avoid is Chapters 3 and 28, and Chapter 3's `gc.disable` measurement is
§29.4 from the other side. The `__del__` finalizers whose timing weakref makes deterministic are Chapter
3 (PEP 442).

**Forward.** The allocator that reclaims the freed blocks is Chapter 28. `functools.cache` and
`lru_cache`, the strong-reference caches that contrast with `WeakValueDictionary`, are Chapters 5 and
**Deep Q**. Descriptors and `__slots__`, which interact with weak-referenceability, are Chapter 4 and
**Deep A**.

**Across books.** Weak references are how Book II holds a reference to a large **Book I** resource
without owning its lifetime: a Python wrapper can hold a weakref to a C++ object that the C++ side owns,
so the Python side observes the object's existence without keeping it alive past the C++ owner's intent,
avoiding the cross-boundary cycle Chapter 3 warned about. An observer registry in a **Book III** pipeline
holds its subscribers weakly, so a subscriber that goes away is dropped automatically rather than kept
alive by the registry. **Deep M** owns the cross-boundary lifetime; weakref is how Python participates
in a lifetime it does not control.

---

## 29.7 Exercises

**1. Break a cycle and watch it die.** Build a parent-child structure with a strong back-reference, `del`
the roots, and confirm with `__del__` output that nothing is freed until `gc.collect()`. Make the
back-reference weak and show both objects free immediately on `del`. Explain the refcount difference.

**2. Build a non-retaining cache.** Use a `WeakValueDictionary` to cache objects by key, insert some with
and some without an external strong reference, and show that the unreferenced ones drop out after
collection while the referenced ones stay. Explain why this cannot leak.

**3. Catch a dropped callback.** Register a death callback on an object *without* keeping the `weakref`
alive, and show the callback does not fire. Fix it by keeping the weakref, and explain the ordering that
made the difference.

**4. Measure the cost yourself.** Reproduce §29.4's benchmark, then add a third case: accessing through a
live weakref (`r()`) versus a direct attribute. Explain where the weakref's cost falls, at creation or at
dereference, and what that implies for a read-heavy versus write-heavy structure.

**5. The design question.** Weak references let refcounting reclaim a structure the cyclic collector
would otherwise handle, at a ~2x per-reference cost. Argue when to reach for a weakref versus when to
just let the collector do its job. Your answer must address the determinism benefit (§29.2), the
throughput cost (§29.4), and Chapter 3's finding about when cycle-churn actually matters.

---

## 29.8 Summary and cross-references

- A **weak reference** points at an object *without* incrementing its refcount, so it breaks a
  reference cycle and lets **refcounting reclaim the structure immediately and deterministically**, no
  cyclic collector needed.
- The toolkit: **`weakref.ref`** (returns the object or `None`), **death callbacks**, and the **weak
  containers** (`WeakValueDictionary`, `WeakSet`) whose members vanish when nothing else holds them, the
  standard non-retaining cache.
- **Measured:** creating a weak reference costs about **2.1x** a plain attribute assignment. It is a
  **determinism and correctness tool, not a throughput optimization**; use it to break a genuine cycle
  or build a non-retaining cache, not on a hot path.
- Edges: `__slots__` classes need `'__weakref__'` to be weak-referenceable, many built-ins cannot be at
  all, and a dropped weakref does not fire its callback.

**Cross-references.** Reference counting → Chapter 19. The cyclic collector and `gc.disable` → Chapters
3 and 28. `__del__` finalization timing → Chapter 3. The allocator reclaiming freed blocks → Chapter 28.
Strong-reference caches → Chapter 5 and Deep Q. `__slots__` → Chapter 4 and Deep A. Cross-boundary
lifetimes → Deep M.
