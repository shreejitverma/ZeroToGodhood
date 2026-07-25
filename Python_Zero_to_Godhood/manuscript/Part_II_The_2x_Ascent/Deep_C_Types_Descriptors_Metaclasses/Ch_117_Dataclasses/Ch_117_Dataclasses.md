# Chapter 36: Dataclasses

Half the object-model machinery in Deep A and Deep C exists so you can write a *value class*: a small object that holds a few fields, compares by value, prints readably, and maybe sorts or hashes.
Chapter 23 made you write `__eq__` and `__hash__`; Chapter 24, the comparison methods; Chapter 27, `__repr__`; Chapter 25, an `__init__`.
For a three-field record that is a dozen lines of boilerplate, all of it mechanical, all of it a chance to introduce a bug (an `__eq__` that forgets a field, a `__repr__` that drifts from the constructor).
`@dataclass` (PEP 557, Python 3.7) writes all of it for you, correctly, from the field annotations.

The framing that matters is *what kind of tool* it is, and the measurement settles it: `@dataclass` is a **code generator**, not a runtime wrapper.
It reads the annotated fields at class-creation time and generates the source of `__init__`, `__repr__`, `__eq__` (and more, on request), which compile like any hand-written method.
So a dataclass costs **nothing** at runtime over the class you would have written by hand, construction is the same speed (measured **0.96x**), and there is no magic on the hot path.
It removes the boilerplate and the bug surface, and keeps the performance.

**This is the canonical home for dataclasses.**
It is the ergonomic capstone of Deep A/C: `frozen=True` gives the hashable value type of Chapter 23, `order=True` the comparisons of Chapter 24, `slots=True` the memory layout of Chapter 22, and the generated `__repr__` is Chapter 27's, all from annotations. `NamedTuple` and `attrs` are its neighbours; `typing` annotations that drive it are **Deep I**.

## Section index

- **36.1** What `@dataclass` generates
- **36.2** The mutable-default trap, `default_factory`, and `slots=True`
- **36.3** Measurement: dataclasses are free (and slots are smaller)
- **36.4** Edges and failure modes
- **36.5** Connections
- **36.6** Exercises
- **36.7** Summary and cross-references

Listings live under `code/ch117/` and are re-executed by `make verify` on both verification interpreters.

---

## 36.1 What `@dataclass` generates

```python
# code/ch117/l01_dataclass_basics.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- generated __init__ and __repr__ ---
  Point(1, 2)  : Point(x=1, y=2)
  Point(5)     : Point(x=5, y=0)   (y defaulted to 0)
--- generated __eq__ compares fields ---
  Point(1, 2) == Point(1, 2) : True
  Point(1, 2) == Point(1, 9) : False
--- frozen=True: immutable and hashable (a value type) ---
  hashable   : True
  set dedups : 1   (one element)
  fp.x = 99 -> FrozenInstanceError (immutable)
--- order=True: generated comparisons (field order = sort order) ---
  Version(1, 2) < Version(1, 3) : True
  Version(2, 0) > Version(1, 9) : True
--- the rule ---
  @dataclass generates __init__/__repr__/__eq__ from annotated fields;
  frozen=True for immutable+hashable value types, order=True for sorting
```

`@dataclass` reads the class body's **annotated fields** (`x: int`, `y: int = 0`) and generates the value-class methods:

- **`__init__`** takes the fields as parameters, in order, honouring defaults (`Point(5)` sets `y=0`).
- **`__repr__`** is `Class(field=value, ...)`, Chapter 27's reconstructable form, `Point(x=1, y=2)`.
- **`__eq__`** compares instances field-by-field (as a tuple), so `Point(1, 2) == Point(1, 2)` is `True`.

The options add the rest of a value type from the earlier chapters:

- **`frozen=True`** makes instances **immutable** (assignment raises `FrozenInstanceError`) and therefore **hashable** (Chapter 23's exact contract: a frozen dataclass gets a `__hash__` derived from its fields, so it deduplicates in a set and works as a dict key). This is the one-line way to get a correct value type.
- **`order=True`** generates `__lt__`/`__le__`/`__gt__`/`__ge__` comparing fields **in declaration order** (Chapter 24), so `Version(1, 2) < Version(1, 3)`, and instances sort.

Every one of these is something Deep A/C taught you to write by hand, generated correctly from the annotations.
The win is not just fewer lines; it is that the generated `__eq__` *cannot* forget a field and the `__repr__` *cannot* drift from the fields, the two classic hand-written-boilerplate bugs are structurally impossible.

---

## 36.2 The mutable-default trap, `default_factory`, and `slots=True`

Two things every dataclass user must know, one a safety rail and one a lever.

```python
# code/ch117/l02_fields_and_slots.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a mutable default is rejected at class creation ---
  list default -> ValueError (use default_factory): True
--- default_factory gives each instance its own object ---
  a.items : ['apple']   b.items : []   (isolated, not shared)
--- slots=True: no __dict__, smaller instances, locked attributes ---
  has __dict__ : False
  fields work  : 1, 2
  sp.z = 3 -> AttributeError (locked attribute set)
--- the rule ---
  mutable defaults need field(default_factory=...); slots=True generates
  __slots__ for smaller, attribute-locked instances
```

**The mutable-default trap, caught.**
A field defaulting to a *mutable* object (`items: list = []`) is the classic Python bug: a single default object would be created once and **shared by every instance** (the same trap as a mutable function default argument), so one instance's `append` would show up in all of them.
`@dataclass` **refuses to create the class**, raising `ValueError` at definition time, and tells you the fix: `field(default_factory=list)`, which calls the factory to produce a **fresh** object per instance.
The output shows the fix working: `a.items` and `b.items` are independent.
This is a rare and welcome case of a language feature *detecting* a common bug rather than merely enabling it, `@dataclass` turns a silent shared-state bug into a loud definition-time error.

**`slots=True`, the memory lever.**
`@dataclass(slots=True)` (Python 3.10+) generates the class with `__slots__` (Chapter 22): instances have **no `__dict__`**, so they are smaller and the attribute set is locked (`sp.z = 3` raises, `z` is not a field).
This is the ergonomic way to get Chapter 22's memory benefit, no hand-written `__slots__` tuple to keep in sync with the fields, the decorator derives it from the annotations.
The one constraint from Chapter 33 carries over: a `slots=True` dataclass has no `__dict__`, so it cannot use `functools.cached_property`.

Together these are the dataclass safety-and-efficiency defaults: `default_factory` for any mutable field, and `slots=True` whenever you will hold many instances.

---

## 36.3 Measurement: dataclasses are free (and slots are smaller)

The question that decides whether to use dataclasses everywhere: do they cost anything at runtime?

**Methodology.** `code/ch117/bench_dataclass.py`.
Construction speed: a `@dataclass` `__init__` versus a hand-written one (`min` of 5 runs, 5,000,000 constructions). Memory: a plain `@dataclass` versus `@dataclass(slots=True)`, one million three-field instances, `tracemalloc`.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64; memory byte-identical on both interpreters.

| measurement | value | vs baseline |
|---|---|---|
| construction, `@dataclass` | 55.3 ns | **0.96x** hand-written |
| construction, hand-written | 57.8 ns | 1.0x |
| memory, `@dataclass` | 130.1 MB | 1.0x |
| memory, `@dataclass(slots=True)` | 92.0 MB | **1.41x smaller** |

**Dataclasses are free.**
Construction is **the same speed** as a hand-written `__init__` (0.96x, within noise, and the same on 3.14.6), because `@dataclass` is a **code generator**: it builds the `__init__` source string once, at class-creation time, and `exec`s it into a normal compiled method.
There is no per-call decorator wrapper, no runtime reflection over fields on each construction, the generated `__init__` is byte-for-byte the kind of `self.x = x` method you would write.
So the boilerplate removal costs nothing; you do not trade performance for convenience.

**Slots make them smaller.**
`slots=True` is **1.41x** smaller for a three-field object (Chapter 22's mechanism, Chapter 22's caveat about key-sharing dicts narrowing the gap), the memory lever with none of the hand-maintenance.

The combined guidance is simple and strong: **use dataclasses for value and record types by default**, they remove boilerplate and the bugs that come with it, at no runtime cost, and add `slots=True` when you hold many instances.
The old reasons to hand-write these classes (fear of overhead, wanting slots) are both answered: there is no overhead, and `slots=True` gives the slots.
This is the endpoint of Deep A/C: the object model is powerful and detailed, and `@dataclass` packages the common case of it into a decorator that is as fast as doing it by hand and far harder to get wrong.

---

## 36.4 Edges and failure modes

**Mutable defaults are rejected; use `default_factory`.** §36.2.
`field(default_factory=list/dict/set)`. This catches the shared-mutable-default bug at definition time.

**`frozen=True` is shallow immutability.**
It blocks attribute *reassignment*, but a mutable field's *contents* can still change (`frozen_obj.items.append(...)` works if `items` is a list). For a truly immutable value, use immutable field types (`tuple`, `frozenset`) too.

**`eq=True` (default) with `frozen=False` sets `__hash__` to `None`.**
A mutable dataclass with generated `__eq__` is *unhashable* (Chapter 23's rule: custom `__eq__` removes `__hash__`), so it cannot go in a set/dict. `frozen=True` restores hashability; `eq=False` keeps identity hashing. This surprises people who expect every dataclass to be hashable.

**`order=True` requires `eq=True` and compares as a tuple.**
The generated comparisons order by fields in declaration order. Reorder fields and you reorder sorting; a field you did not intend as a sort key still participates. Use `field(compare=False)` to exclude a field from `__eq__`/ordering.

**`slots=True` and `cached_property` conflict.** §36.2, Chapter 33.
No `__dict__` means no place to cache. Also, `slots=True` creates a *new* class (it cannot add slots to an existing one), which can surprise code relying on class identity or that uses `super()` in `__post_init__` subtleties.

**`__post_init__` for derived fields and validation.**
`@dataclass` generates `__init__`, so to run extra logic after field assignment (validation, computing a derived field) define `__post_init__(self)`. For a `frozen` dataclass, setting a field in `__post_init__` requires `object.__setattr__` (assignment is blocked).

**Inheritance and default ordering.**
A subclass dataclass's fields follow the base's, and a base field with a default forces all later fields (including the subclass's) to have defaults, the same "non-default after default" rule as function parameters, surfaced across the hierarchy.

**Annotations are required, and `ClassVar`/`InitVar` are special.**
Only *annotated* names become fields; a bare `x = 5` is a class attribute, not a field. `typing.ClassVar` excludes a name from fields; `InitVar` passes a value to `__post_init__` without storing it. These are easy to get subtly wrong.

---

## 36.5 Connections

**Backward.**
Every method `@dataclass` generates is a Deep A/C protocol: `__init__` (Chapter 25), `__repr__` (Chapter 27), `__eq__`/`__hash__` (Chapter 23), the comparisons (Chapter 24), and `slots=True` is Chapter 22. The mutable-default rejection is the shared-default bug from the functions chapter, caught at class creation. `frozen`'s immutability uses `object.__setattr__` blocking (Chapter 21's write hook).

**Forward.**
`typing` annotations that drive field types, and how a type checker reads a dataclass, are **Deep I**. `NamedTuple` (an immutable, tuple-based alternative) and `TypedDict` (a dict with a fixed schema) are neighbours in **Deep I**/**Deep Q**. The third-party `attrs` (which predates and influenced dataclasses) and `pydantic` (dataclasses plus runtime validation) are ecosystem topics. `enum.Enum` (another class-generating tool) is the rest of Deep C.

**Across books.**
Dataclasses are the default shape of **Book I**'s domain objects: orders, fills, quotes, positions, config records, each a `@dataclass` (often `frozen=True, slots=True`) that is a correct value type, prints readably in logs, compares and hashes for use in sets and dicts, and costs nothing over a hand-written class. The order-book system models its immutable messages and events as frozen slotted dataclasses, so they are hashable for deduplication and routing, small enough to hold millions of, and their `__repr__` (Chapter 27) makes every log line diagnosable, the whole of Deep A/C's value-type machinery delivered in one decorator, at hand-written speed.

---

## 36.6 Exercises

**1. Generate the boilerplate.** Reproduce §36.1: a `@dataclass` with a defaulted field. Confirm the generated `__init__`, `__repr__`, and `__eq__`. Then hand-write the equivalent class and diff the behaviour, and count the lines you saved.

**2. The mutable-default trap.** Try a dataclass with `items: list = []` and observe the `ValueError`. Fix it with `default_factory` and confirm two instances have independent lists. Explain the shared-state bug the rejection prevents.

**3. A proper value type.** Make a `frozen=True` dataclass and confirm it is immutable and hashable and deduplicates in a set. Then show that `frozen` is *shallow* by mutating a list field's contents. Explain, using Chapter 23, why `frozen` gives you `__hash__` back.

**4. Measure it.** Reproduce §36.3. Confirm construction is the same speed as hand-written and that `slots=True` is smaller. Explain why the decorator adds no per-call overhead (what does it do, and when).

**5. The design question.** `@dataclass` generates code at class-creation time rather than doing reflection at runtime (as some frameworks do). Argue why, using the §36.3 measurement, and name what this costs (the generated methods are fixed at definition; §36.4's `slots=True` creates a new class). Would runtime reflection have been more flexible, and is the flexibility worth the speed?

---

## 36.7 Summary and cross-references

- **`@dataclass` generates** `__init__`, `__repr__`, and `__eq__` from annotated fields, the Deep A/C value-class boilerplate, correctly and without drift. **`frozen=True`** adds immutability + hashability (Chapter 23), **`order=True`** adds comparisons (Chapter 24), **`slots=True`** adds `__slots__` (Chapter 22).
- **Mutable defaults are rejected** at class creation (the shared-default bug); use **`field(default_factory=...)`** for a fresh object per instance.
- **Measured:** `@dataclass` construction is **the same speed** as a hand-written `__init__` (0.96x), because the decorator is a **code generator**, not a runtime wrapper, no per-call overhead. `slots=True` is **1.41x** smaller.
- **Use dataclasses for value/record types by default** (no runtime cost, no boilerplate bugs); add `slots=True` for many instances.
- **Edges:** `frozen` is shallow; a mutable dataclass is unhashable (`__eq__` removes `__hash__`); `order` compares fields in declaration order; `slots=True` conflicts with `cached_property`; use `__post_init__` for validation/derived fields; only annotated names are fields.

**Cross-references.** Generated methods → Chapters 25 (`__init__`), 27 (`__repr__`), 23 (`__eq__`/`__hash__`), 24 (ordering), 22 (`slots`). The mutable-default bug → the functions chapter. Type annotations and `NamedTuple`/`TypedDict` → Deep I. `enum` → Deep C. `attrs`/`pydantic` → ecosystem.
