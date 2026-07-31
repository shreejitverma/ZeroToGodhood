# Chapter 230: __slots__

## The constraint

Python 2.2's new-style classes (Chapter 4) unified types and classes and gave every object a per-instance `__dict__` - the dictionary that holds its attributes.
That `__dict__` is what makes Python objects so pleasantly dynamic: you can attach any attribute to any instance at runtime, and the object just grows a new dictionary entry.
For the overwhelming majority of programs, that flexibility is free in every way that matters.

But it is not free in memory.
A dictionary is a substantial object - a hash table with its own overhead - and when an instance is small, that dictionary is not a rounding error on the object's cost; it *is* the object's cost.
The moment you have a great many small objects - points in a mesh, rows in a table, nodes in a tree, particles in a simulation - the per-instance `__dict__` multiplied by the instance count becomes the dominant term in your program's footprint.
The constraint 2.2 answered, in the very same release that introduced the `__dict__`, was this: **give the programmer a lever to trade the dictionary's flexibility for memory when there are too many objects to afford it.**
That lever is `__slots__`.

This is a two-track chapter.
The object layout it rests on - how an instance stores its attributes, what a slot descriptor is, how the type's C-level structure lays out fixed fields versus a dict pointer - all belongs to Deep Volume A (the object and type model).
The cost model that tells you *when* the memory saving is worth reaching for belongs to Chapter 88.
What this chapter owns is the release fact: in 2.2, alongside the `__dict__`, Python shipped the declaration that lets a class opt out of it.

## What shipped

A class that sets `__slots__` to a tuple of attribute names tells the interpreter to store exactly those attributes in a compact, fixed-size array laid out in the object itself - and to give instances *no* `__dict__` at all.
Listing 230.1 puts a dict-backed point and a slots-backed point side by side on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- the default: every instance carries a __dict__ ---
  PointDict instance has __dict__ : True
  its contents : {'x': 1, 'y': 2}
  the __dict__ is what lets you add pd.z = 9 at runtime. flexible,
  but every instance pays for a whole dictionary (Deep A's layout)
--- __slots__: a fixed array, no __dict__ ---
  PointSlots instance has __dict__ : False
  x and y still work normally : 1, 2
  __slots__ = ('x','y') tells the type to store x and y in a compact
  slot array, NOT a dict. the attributes read and write identically;
  only the storage changed (the point of the mechanism)
--- the memory win: smaller instances ---
  PointDict  : object 48 + dict 296 = 344 bytes
  PointSlots : object 48 bytes (no dict)
  slots instance is smaller : True
  the dict is the bulk of a small object's cost. remove it and each
  instance shrinks - decisive when you have millions of them, which
  is exactly when Chapter 88's cost model says to care about layout
--- the side effect: __slots__ catches attribute typos ---
  pd.actve = True  (typo on a __dict__ class):
    silently created pd.actve = True  (bug hides)
  ps.actve = True  (typo on a __slots__ class):
    raised AttributeError('PointSlots' object has no attribute 'actve' and no __dict__ for setting new attributes)  (bug caught)
  with a __dict__, a misspelled attribute silently becomes a new
  field and the real one stays unset - a classic silent bug. with
  __slots__, only declared names exist, so the typo raises at once
--- the cost of __slots__: you give up dynamic attributes ---
  ps.z = 9 would raise: 'z' is not a declared slot. that is the
  trade - you lose runtime attribute addition (and multiple
  inheritance gets fiddly) in exchange for memory and typo-safety.
  use it for high-count, fixed-shape objects; skip it otherwise
--- the constraint answered ---
  new-style classes (2.2) gave every instance a flexible __dict__,
  which costs memory that dominates when objects are small and
  numerous. __slots__ (same release) is the lever: declare the
  fields, drop the dict, shrink the instance, and catch typos - the
  memory knob for object-heavy code Chapter 88 tells you to reach for
```

## Why each part answers the constraint

**The default carries a dictionary.**
The first block establishes the baseline: `PointDict` has a `__dict__`, and that dict is what lets you write `pd.z = 9` at runtime.
This is the flexibility the constraint is trading against - real and valuable, but paid for on every instance.

**`__slots__` removes the dictionary, not the attributes.**
`PointSlots` has no `__dict__` at all, yet `ps.x` and `ps.y` read and write exactly as before.
This is the crucial reassurance: `__slots__` changes only *where* the attributes live, from a per-instance hash table to a fixed array in the object's own memory.
The interface is identical; the storage is not.

**The memory win is the whole point.**
The measured numbers on this interpreter make the case concrete: the dict-backed point costs 48 bytes for the object plus 296 bytes for its dictionary - 344 bytes total - while the slots-backed point is 48 bytes with no dictionary.
The dictionary is roughly six-sevenths of the small object's cost.
Multiply by a million instances and the difference is hundreds of megabytes.
This is precisely the situation Chapter 88's cost model flags: when objects are small and numerous, layout is not a micro-optimization, it is the memory budget, and `__slots__` is the knob.
(The exact byte counts are interpreter- and build-specific; what generalizes is the ratio, and that the dict is the bulk of the cost.)

**Typo-catching is a free side benefit.**
The subtle bug the `__dict__` enables: `pd.actve = True` on a dict-backed class *silently succeeds*, creating a brand-new `actve` field while the real `active` stays unset.
Nothing complains, and the bug hides until something reads the attribute that was never set.
On a `__slots__` class, `ps.actve = True` raises `AttributeError` immediately, because `actve` is not a declared slot and there is no `__dict__` to absorb it.
So `__slots__` buys, in addition to memory, a small measure of the attribute-name checking that a purely dynamic object cannot offer.

**The cost is dynamism.**
The chapter is honest about the trade, as a release chapter should be: with `__slots__` you cannot add undeclared attributes at runtime (`ps.z = 9` raises), and multiple inheritance involving slotted classes gets fiddly.
That is the price of the fixed layout.
The decision rule is therefore narrow and clear: reach for `__slots__` on high-count, fixed-shape objects where memory is measured and matters, and leave it off everywhere else, where the flexibility of the `__dict__` is worth far more than the bytes it costs.

## The two-track note

The mechanism - how a slot becomes a descriptor on the class, how the object's C structure reserves fixed fields, why a slotted subclass of a non-slotted class silently regains a `__dict__` - is Deep Volume A's to lay out.
The decision procedure - profile first, confirm the object count and the per-instance size dominate, then measure the win - is Chapter 88's.
What the timeline records is that both the dictionary and its off-switch shipped together in 2.2: new-style classes made every object dynamic by default, and `__slots__` gave you the way to say "not this class, not a million times."
The modern consequence, verified above, is that the memory lever is exactly as effective today as the day it shipped, and the typo-catching is a bonus that has quietly saved a lot of debugging.

## Where this lands

`__slots__` is the first memory-shaping tool the language gave the working programmer, and it set the pattern for later ones: a declaration that trades flexibility you probably are not using for a resource you have measured yourself short on.
Most classes should never use it - the `__dict__` is one of the nicest things about Python objects.
But when the profiler says a few small classes, instantiated by the million, own your memory, `__slots__` is the release-provided answer.
Deep Volume A explains the layout; Chapter 88 tells you when to care; this chapter is the record of the day the lever arrived, in the same release as the flexibility it exists to trade away.

This closes Volume 4 (Unification): the 2.2-2.3 arc that unified types and classes and, in doing so, handed the programmer the descriptor protocol, properties, iterators and generators, the set and bool types, and the memory lever - a coherent enlargement of what a Python object could be.
