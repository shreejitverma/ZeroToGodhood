# Chapter 22: `__slots__` and Instance Layout

Chapter 21 ended on a promise: `__slots__` removes the per-instance `__dict__`, and that changes both the memory profile and the lookup.
This chapter makes good on it.
A normal instance carries a dictionary so it can hold *any* attribute you assign, and that flexibility is the default every Python object pays for.
`__slots__` is the opt-out: you declare the attribute names up front, the instance stores them in a fixed C-level layout with no dict, and the object gets smaller.

The reason to teach it precisely is that its reputation is wrong in two directions.
People reach for `__slots__` expecting a speed-up (attribute access is essentially the *same* speed, measured below), and they underestimate how easily the memory saving is *lost* to a single subclass that forgets to declare its own slots.
The honest picture is narrow and useful: `__slots__` saves memory (here **1.55x** for a four-field object) and locks the attribute set so that a typo'd assignment becomes an error instead of a silent new attribute, and it does neither of those things if you use it carelessly in a hierarchy.

**This is the canonical home for instance layout and `__slots__`.**
It builds directly on Chapter 19 (the object header and what `getsizeof` does and does not count), Chapter 20 (member descriptors are type slots), and Chapter 21 (slots sit at rank 1 of the lookup order, as data descriptors).
The descriptor protocol that makes a slot work is **Deep C**; here we use member descriptors, we do not derive them.

## Section index

- **22.1** No `__dict__`: fixed slots and a locked attribute set
- **22.2** `__slots__` and inheritance: keeping or losing the saving
- **22.3** Measurement: memory yes, speed no
- **22.4** Edges and failure modes
- **22.5** Connections
- **22.6** Exercises
- **22.7** Summary and cross-references

Listings live under `code/ch107/` and are re-executed by `make verify` on both verification interpreters.

---

## 22.1 No `__dict__`: fixed slots and a locked attribute set

```python
# code/ch107/l01_no_dict.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a normal instance has a __dict__; a slotted one does not ---
  WithDict  has __dict__ : True
  WithSlots has __dict__ : False
--- both store their declared attributes the same way to read ---
  wd.a, wd.b : 1, 2
  ws.a, ws.b : 1, 2
--- but a slotted instance REJECTS any undeclared attribute ---
  ws.c = 3 -> AttributeError : 'WithSlots' object has no attribute 'c' and no __dict__ for setting new attributes
  wd.c = 3 (normal instance) : allowed -> 3
--- each slot is a member_descriptor (a data descriptor) on the class ---
  type(WithSlots.a) : member_descriptor
--- the rule ---
  __slots__ replaces the instance __dict__ with fixed slot descriptors:
  smaller objects, a locked attribute set, no arbitrary assignment
```

`WithDict` has a `__dict__`; `WithSlots` does not.
Declaring `__slots__ = ("a", "b")` tells CPython to lay out storage for exactly those two attributes *inside the instance's own allocation* (like the fixed fields of a C struct) and to omit the dict pointer that would otherwise let the object grow arbitrary attributes.
Reading a slotted attribute looks identical (`ws.a` is `1`), but writing an *undeclared* name raises `AttributeError` with a precise message: there is "no `__dict__` for setting new attributes".
The normal instance accepts `wd.c = 3` because its dict has room for anything.

The two benefits fall out of that one structural change.
**Memory**: no dict means a smaller object (§22.3).
**Correctness**: the attribute set is *closed*, so `self.lenght = 5` (a typo for `length`) is no longer a silently-created third attribute you debug for an hour, it is an immediate error.
And the mechanism is one you already know: each slot is a `member_descriptor` on the class, a *data* descriptor, which is why it sits at rank 1 of Chapter 21's lookup order and cannot be shadowed by anything in an instance dict (there is no instance dict to shadow it with).

---

## 22.2 `__slots__` and inheritance: keeping or losing the saving

This is where `__slots__` is most often used wrongly, because its effect is *per class*, not per hierarchy.

```python
# code/ch107/l02_inheritance.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a subclass WITHOUT __slots__ regains a __dict__ (saving defeated) ---
  SubNoSlots has __dict__ : True
  sn.anything = 1 works   : 1
--- __slots__ = () keeps the block through a field-less subclass ---
  SubEmpty has __dict__   : False
  se.x = 1 -> AttributeError (still locked)
--- add only NEW slots; inherited ones still work ---
  SubMore has __dict__    : False
  sm.a (inherited), sm.b (new) : 10, 20
--- the rule ---
  slots bind only the declaring class; a subclass without __slots__
  restores __dict__. Use __slots__ = () to keep the block, add only new
```

`SubNoSlots` inherits from a slotted `Base` but declares no `__slots__` of its own, and its instances get a `__dict__` back, so `sn.anything = 1` works and the memory saving is gone.
This is the trap: a base class carefully uses `__slots__`, someone subclasses it without thinking about slots, and every instance of the subclass silently carries a dict again.
The interpreter *has* to do this, a class without `__slots__` promises open attributes, and it cannot keep that promise without a dict.

The two disciplined patterns:

- To subclass and add **no** new fields while keeping the block, declare `__slots__ = ()`.
  `SubEmpty` does this: no dict, `se.x = 1` still raises.
- To subclass and add fields, declare **only the new ones**.
  `SubMore` declares `("b",)`; `a` is inherited from `Base` and still works, and no dict appears.
  Repeating an inherited slot name does not error but wastes space (two storage locations for one logical attribute), so list only what is new.

The rule: **every class in the hierarchy must declare `__slots__` (possibly empty) for the object to stay dict-free.** One class that forgets reintroduces the dict for its instances and everything below.

---

## 22.3 Measurement: memory yes, speed no

**Methodology.** `code/ch107/bench_slots.py`.
A four-field class, a million instances, with and without `__slots__`: peak memory via `tracemalloc`, and per-attribute read time via `timeit` (`min` of 5 runs, 10,000,000 reads).
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.
The memory figures were byte-identical across both interpreters, so they are reported without variance.

| 1,000,000 four-field objects | value | vs `__dict__` |
|---|---|---|
| memory, `__dict__` | 107.2 MB | 1.0x |
| memory, `__slots__` | 69.1 MB | **0.64x (1.55x smaller)** |
| attribute read, `__dict__` | 13.6 ns | 1.0x |
| attribute read, `__slots__` | 13.4 ns | **0.98x** |

Two findings, and the second corrects a widespread belief.

**Memory: a real saving, but smaller than folklore says.**
`__slots__` is **1.55x** smaller here, ~38 bytes per object, the cost of the dropped dict pointer and the dict's own overhead.
Older write-ups quote 2x or more, and that gap has *narrowed* because modern CPython gives ordinary instances **key-sharing dictionaries** (PEP 412): instances of the same class share one copy of the keys, so a plain `__dict__` is already far cheaper than it was in Python 2.
`__slots__` still wins, but by 1.5x, not 3x, and that number rises with more fields and falls with fewer.

**Speed: essentially none.**
Attribute reads are the same within noise (0.98x; on 3.14.6, 0.91x).
Both paths resolve in C: an ordinary instance uses the specialized instance-dict lookup, a slotted one reads a member descriptor at a fixed offset.
Neither is dramatically faster than the other for a plain read.

So place `__slots__` correctly: it is a **memory** optimization and an **attribute-set lock**, not a speed optimization.
Reach for it when you create objects in large numbers (nodes, records, points, events) or when you want a class's attributes closed against typos.
Do *not* reach for it expecting faster attribute access, and do not scatter it across a hierarchy without ensuring every class participates, or the saving you added is quietly refunded by the first subclass that forgets.

---

## 22.4 Edges and failure modes

**The saving is lost to any subclass without `__slots__`.** §22.2.
For the memory benefit to survive, *every* class in the MRO must declare `__slots__`. Use `__slots__ = ()` for field-less subclasses.

**`__slots__` is not a speed-up.** §22.3.
Attribute access is the same speed. If someone added `__slots__` "for performance", they were measuring memory or nothing.

**No `__weakref__` unless you ask.**
A slotted class cannot be the target of a `weakref` unless `"__weakref__"` is in its `__slots__`. Code that weak-references your instances (caches, observer registries) breaks silently otherwise. Add `"__weakref__"` when needed.

**A `__dict__` slot re-enables arbitrary attributes.**
Putting `"__dict__"` in `__slots__` gives instances both the named slots *and* a dict, useful when you want fast fixed fields plus occasional dynamic ones, but it forfeits the "locked attribute set" benefit and most of the memory saving.

**Class-level defaults collide with slots.**
You cannot have both a slot named `x` and a class attribute `x = 0` as a default: the slot descriptor and the class value occupy the same name, and CPython raises `ValueError` at class creation. Initialise slot defaults in `__init__`, not as class attributes.

**Multiple inheritance with non-empty slots on two parents fails.**
If two base classes each declare non-empty `__slots__`, a class inheriting from both raises a layout error (`TypeError: multiple bases have instance lay-out conflict`). Slots and diamond inheritance interact badly; keep slotted classes single-inheritance where possible.

**`__slots__` does not deep-freeze the object.**
It closes the *set of attribute names*; the values are still mutable. It is not immutability, and it is not a security boundary.

---

## 22.5 Connections

**Backward.**
The `__dict__` that `__slots__` removes is the object whose per-instance cost Chapter 19 measured and Chapter 21 read and wrote. A slot is a member descriptor, a *data* descriptor, so it occupies rank 1 of Chapter 21's lookup order, which is why an instance cannot shadow it. The "smaller object" claim is the same accounting as Chapter 19's `tp_basicsize`: slots live *in* the instance's basic allocation, a dict lives behind a pointer.

**Forward.**
The descriptor protocol that a `member_descriptor` implements, `__get__`/`__set__` and data-versus-non-data, is **Deep C**, alongside `property`, `classmethod`, and the MRO that §22.2's inheritance rules walk. Key-sharing dictionaries (PEP 412), the reason the memory gap narrowed, are a `dict`-internals topic in **Deep Q**. The specializing interpreter's instance-attribute fast paths, which keep plain-`__dict__` access competitive with slots, are **Deep H**.

**Across books.**
`__slots__` is one of **Book I**'s standard tools for holding many small objects without the header-and-dict tax, the same motivation as `array` and NumPy dtypes in Chapter 19, applied to *structured* objects rather than raw numbers. The order-book system's price-level and order objects, created and destroyed constantly, use `__slots__` to shrink each instance and to guarantee their field set is closed, so a mistyped field is a crash in a test rather than a corrupt book in production, exactly the correctness benefit §22.1 describes, with the memory benefit §22.3 measures.

---

## 22.6 Exercises

**1. Confirm the layout.** Reproduce §22.1: build a slotted and an unslotted version of the same class, confirm the missing `__dict__`, the rejected undeclared attribute, and that each slot is a `member_descriptor`. Then use `sys.getsizeof` on one instance of each and explain the difference in terms of Chapter 19's header accounting.

**2. Lose and recover the saving.** Build a slotted `Base`, then a subclass that forgets `__slots__`, and show with `tracemalloc` that a million subclass instances cost as much as the unslotted version. Fix it with `__slots__ = ()` and re-measure. Explain why the interpreter had no choice in the un-fixed case.

**3. Measure your own object.** Reproduce §22.3 for an object with the field count *you* actually use. Report both the memory ratio and the access ratio. Then vary the field count from 1 to 20 and describe how the memory ratio moves, and why key-sharing dicts (§22.3) make the gap what it is.

**4. The weakref trap.** Build a slotted class and try to put its instances in a `weakref.WeakValueDictionary`. Observe the failure, fix it, and explain what `"__weakref__"` in `__slots__` restores and why it was gone.

**5. The design question.** `__slots__` trades flexibility (arbitrary attributes) for memory and a closed attribute set, and it is opt-in. Argue why CPython did not make slotted layout the *default* with dicts opt-in, addressing the ergonomics of dynamic attribute assignment, the inheritance fragility of §22.2, and the fact (§22.3) that key-sharing dicts already recovered much of the memory. Would `@dataclass(slots=True)` change your answer?

---

## 22.7 Summary and cross-references

- **`__slots__` replaces the per-instance `__dict__`** with a fixed set of slot descriptors: the instance has no dict, stores its declared fields in a compact layout, and **rejects any undeclared attribute** (`AttributeError`). Each slot is a `member_descriptor` (a data descriptor, rank 1 of the lookup order).
- **The effect is per class.** A subclass without its own `__slots__` **regains a `__dict__`**, defeating the saving. Use `__slots__ = ()` for field-less subclasses; declare only *new* fields when adding.
- **Measured:** for a million four-field objects, `__slots__` is **1.55x smaller** (107.2 to 69.1 MB) with **the same access speed** (0.98x). It is a memory optimization and an attribute-set lock, *not* a speed optimization; key-sharing dicts (PEP 412) narrowed the memory gap from the older 2x+ figures.
- **Edges:** no `weakref` unless `"__weakref__"` is a slot; no class-level default for a slot name; non-empty slots on two bases conflict; adding `"__dict__"` re-opens attributes. It closes names, not values, it is not immutability.

**Cross-references.** The instance `__dict__` and header accounting → Chapters 19, 21. Member/data descriptors, `property`, MRO → Deep C. Key-sharing `dict` internals → Deep Q. Instance-attribute specialization → Deep H. Escaping per-object cost for raw numbers → Chapter 19, Deep M.
