# Chapter 4: Type-Class Unification, Descriptors, and C3 MRO (Python 2.2-2.3)

Run this and watch it print `False`:

```python
class C:
    def m(self):
        return 1

c = C()
print(c.m is c.m)      # False
```

The same method, read twice off the same object, is not the same object. That is not a bug and it is
not an optimization gone wrong. It is the surface of the mechanism this chapter is about: a method is
not a thing stored on the instance. It is *manufactured on every access* by a descriptor, the single
protocol that Python 2.2's type-class unification put underneath methods, `property`, `classmethod`,
`staticmethod`, `super()`, and `__slots__`.

Python 2.2 made the most important change to the object model after Python itself existed: it unified
types and classes. Before it, user-defined classes and built-in types were different kinds of thing
at the C level, and you could not subclass `list`. After it, a class *is* a type, every class descends
from `object`, and three mechanisms, the descriptor protocol, the C3 linearized method resolution
order, and the `__new__`/`__init__` split, became the machinery under everything that feels like
object orientation in Python. This chapter is the origin story and the working reference for all
three. It is where the dunder-to-slot wiring Chapter 2 mentioned becomes a protocol you implement
yourself.

> **One home.** Descriptors and the MRO are taught in full here. The complete `PyTypeObject` slot
> table, metaclasses, and the construction of `type` itself are **Deep C**; this chapter establishes
> the model they build on and cross-references forward rather than duplicating it.

## Section index

- **4.1** New-style classes: unifying types and classes (PEP 252/253)
- **4.2** The descriptor protocol
- **4.3** The attribute-lookup algorithm and descriptor precedence
- **4.4** Methods, `classmethod`, `staticmethod`, and `property` as descriptors
- **4.5** Method Resolution Order and C3 linearization
- **4.6** Instance lifecycle: `__new__` versus `__init__`
- **4.7** Measurement: what an attribute actually costs
- **4.8** Edges and failure modes
- **4.9** Connections
- **4.10** Exercises
- **4.11** Summary and cross-references

Listings live under `code/ch004/` and are re-executed by `make verify` on both interpreters.

---

## 4.1 New-style classes: unifying types and classes (PEP 252/253)

**Why this exists.** Before Python 2.2 there were two parallel universes. *Classic classes*
(`class C:`) were all instances of one C type, `PyClass_Type`, and their instances were all
`PyInstance_Type`. *Built-in types* (`int`, `list`, `str`) were `PyTypeObject`s. The two could not
mix: `type(c)` of any classic instance returned `<type 'instance'>` rather than the class, and **you
could not subclass a built-in type**, because the classic-class machinery had no idea how to manage a
built-in's C memory layout.

**PEP 252 and PEP 253** introduced **new-style classes**: a class that derives, directly or
transitively, from `object` is itself a `PyTypeObject`, an instance of `type`. That collapsed the two
universes into one. Python 3 removed classic classes entirely, so every class is new-style, but the
mechanisms unification introduced are exactly what the rest of this chapter dissects.

```python
# code/ch004/l02_unification.py
class NewStyle:            # implicitly subclasses object in Python 3
    pass
```

Verified output (CPython 3.13.5):

```text
--- one universe: type(instance) IS the class ---
  type(n)                     : NewStyle
  issubclass(NewStyle, object): True
  type(NewStyle) is type      : True
```

The C-level consequence is the **slot system**, and it is observable in both directions. Every class
is a `PyTypeObject` whose slots (`tp_init`, `tp_new`, `tp_getattro`, and the rest) hold the function
pointers the interpreter calls. When you write a Python method named `__init__`, CPython installs a
slot wrapper into `tp_init` that calls your function. Conversely, a built-in's C slot is exposed to
Python as a **wrapper descriptor**:

```text
--- the slot bridge, both directions ---
  a Python __init__ is a function in the type:
    type(D.__init__)          : function
  a built-in C slot is a wrapper_descriptor exposed to Python:
    type(object.__init__)     : wrapper_descriptor
    repr(object.__init__)     : <slot wrapper '__init__' of 'object' objects>
    type(int.__add__)         : wrapper_descriptor (the nb_add slot)
```

`int.__add__` being a `wrapper_descriptor` is the whole unification in one line: the integer type's C
`nb_add` slot (part of its `tp_as_number` sub-table) is surfaced to Python as an ordinary attribute
you can look up, pass around, and call. A Python method and a C slot are the same protocol seen from
two sides. The full slot table, `tp_as_number`, `tp_as_sequence`, `tp_as_mapping`, and how a type is
assembled from them, is **Deep C**; what matters here is that the bridge is total and symmetric.

---

## 4.2 The descriptor protocol

**Why this exists.** A **descriptor** is an object that customizes what happens when it is accessed as
a *class attribute* of another object. It is the single mechanism behind methods, `property`,
`classmethod`, `staticmethod`, `__slots__` members, and `functools.cached_property`, and you can
implement it yourself. The protocol is three optional methods:

```python
def __get__(self, instance, owner=None): ...   # attribute is read
def __set__(self, instance, value): ...        # attribute is assigned
def __delete__(self, instance): ...            # attribute is deleted
```

The presence of `__set__` or `__delete__` splits descriptors into two kinds, and that distinction
governs lookup precedence (§4.3):

- **Data descriptor**: defines `__set__` and/or `__delete__`, with or without `__get__`. `property` is
  the canonical example.
- **Non-data descriptor**: defines only `__get__`. Plain functions are the canonical example, which is
  why the chapter opened with a method behaving like one.

A minimal data descriptor that validates writes, using the modern `__set_name__` hook:

```python
# code/ch004/l03_descriptor_precedence.py (excerpt)
class ValidatedPositive:
    def __set_name__(self, owner, name):      # 3.6+: learn the attribute name
        self.private = "_" + name
    def __get__(self, obj, owner=None):
        return self if obj is None else getattr(obj, self.private)
    def __set__(self, obj, value):
        if value <= 0:
            raise ValueError("must be positive")
        setattr(obj, self.private, value)
```

Verified output (CPython 3.13.5):

```text
--- a data descriptor intercepting writes ---
  a.balance: 100
  a.balance = -5 -> ValueError: must be positive
```

`__set_name__` (PEP 487, Python 3.6) is the modern touch: the descriptor is told its own attribute
name at class-creation time, so it can compute a private backing slot without the boilerplate the 2.x
originals required. Before it, the descriptor either hard-coded the name or received it as a
constructor argument, both of which duplicated information the class definition already had.

---

## 4.3 The attribute-lookup algorithm and descriptor precedence

**What the interpreter actually does.** Every `obj.name` read goes through the type's `tp_getattro`
slot, which for ordinary objects is `PyObject_GenericGetAttr` (`Objects/object.c`). Its algorithm is
precise and worth memorizing, because the ordering is the source of every descriptor behavior:

1. **Search the type's MRO** (`_PyType_Lookup`) for `name`; call any result `descr`.
2. **Data-descriptor short-circuit.** If `descr` is a data descriptor, call
   `descr.__get__(obj, type(obj))` and return. The instance dict is never consulted.
3. **Instance dict.** Otherwise, if `name` is in `obj.__dict__`, return that value.
4. **Non-data descriptor or class attribute.** Otherwise, if `descr` exists: if it is a non-data
   descriptor, call `descr.__get__(...)`; if it is a plain class attribute, return it.
5. **`__getattr__` fallback.** If nothing was found, raise `AttributeError`, which triggers
   `__getattr__(self, name)` if the class defines it.

```text
obj.name
   |
   v
 MRO has a DATA descriptor? ---yes--> descr.__get__(obj, type)   (instance dict ignored)
   | no
   v
 name in obj.__dict__? --------yes--> return obj.__dict__[name]
   | no
   v
 MRO has a NON-DATA descriptor? -yes-> descr.__get__(obj, type)
   | no
   v
 MRO has a plain class attr? ---yes--> return it
   | no
   v
 raise AttributeError --> __getattr__(self, name) if defined
```

The precedence is directly observable. Give a class one data descriptor and one non-data descriptor,
then write an instance-dict entry over each:

```python
# code/ch004/l03_descriptor_precedence.py (excerpt)
c.__dict__["d"] = "instance-d"     # try to shadow the DATA descriptor
c.__dict__["n"] = "instance-n"     # try to shadow the NON-DATA descriptor
```

Verified output (CPython 3.13.5):

```text
--- both names have an instance-dict entry; only one wins ---
  c.d -> data-descriptor   (data descriptor wins; instance dict ignored)
  c.n -> instance-n   (instance dict wins over the non-data descriptor)
```

This is *why* you cannot accidentally clobber a `property` by assigning to `self.x` in `__init__`: the
property is a data descriptor and its `__set__` intercepts the assignment, so the value never reaches
the instance dict where step 3 would find it. It is also why you *can* shadow a method by storing a
callable in the instance dict, which is a real and occasional bug: a method is a non-data descriptor,
so an instance attribute of the same name wins. And it is why ordinary instance attributes are cheap:
they resolve at step 3, and only methods and properties pay the MRO walk at step 1. That cost is what
§4.7 measures.

---

## 4.4 Methods, `classmethod`, `staticmethod`, and `property` as descriptors

Every flavor of "method" is a descriptor; the differences live entirely in `__get__`:

- **Plain function**: a non-data descriptor. `obj.method` evaluates `function.__get__(obj,
  type(obj))`, which returns a bound method pairing the function with `obj`. `Class.method` calls
  `__get__(None, Class)` and returns the raw function.
- **`@classmethod`**: `__get__` ignores the instance and binds the class, so the first argument is
  `cls`.
- **`@staticmethod`**: `__get__` returns the underlying function unchanged; no binding.
- **`@property`**: a data descriptor wrapping `fget`, `fset`, `fdel`.

The chapter's opening surprise is now fully explained by the plain-function case:

```python
# code/ch004/l01_method_identity.py
class C:
    def m(self):
        return 1
```

Verified output (CPython 3.13.5):

```text
--- reading the same method twice yields two different objects ---
  c.m is c.m       : False
  type(c.m)        : method
  c.m == c.m       : True (equal by value: same func, same self)
--- the bound method is a thin wrapper: function + instance ---
  bound.__self__ is c   : True
  bound.__func__ is C.m : True
--- accessed on the CLASS, __get__ returns the raw function ---
  type(C.m)             : function
  C.m.__get__(c, C) == c.m: True
```

`c.m is c.m` is `False` because each read runs `__get__` and builds a fresh bound-method object; `c.m
== c.m` is `True` because two bound methods are equal when they wrap the same function and the same
`__self__`. The bound method holds `obj` in `__self__` and the function in `__func__`, and calling it
prepends `__self__` as the first positional argument. That is the entire mechanism of `self`: no
magic, a non-data descriptor returning a small wrapper. (The per-access allocation is real but tiny,
and the specializing interpreter's `LOAD_METHOD`/`CALL` path avoids materializing the wrapper at all
for the common `obj.method()` call shape; §4.7 and Chapter 17.)

---

## 4.5 Method Resolution Order and C3 linearization

**Why this exists.** With multiple inheritance, "which base defines this method?" needs a total order
over the ancestors that is *consistent*. Classic classes used naive depth-first, left-to-right, which
in a diamond reached the shared ancestor *before* a sibling that overrode it, so the ancestor's method
shadowed the override, the opposite of what specialization demands. Python 2.3 adopted **C3
linearization**, which guarantees two properties: **local precedence** (bases appear in the order you
declared them) and **monotonicity** (if `X` precedes `Y` in one class's MRO, `X` precedes `Y` in every
subclass's MRO too).

**The algorithm.** Let `L(C)` be the MRO of `C` with parents `B1...Bn`:

$$L(C) = [C] + \mathrm{merge}\big(L(B_1), L(B_2), \dots, L(B_n), [B_1, B_2, \dots, B_n]\big)$$

`merge` repeatedly takes a **good head**, the head of some list that does not appear in the *tail*
(everything past the head) of any other list, appends it, and removes it from all lists. If no good
head exists, the hierarchy is inconsistent and CPython raises `TypeError`.

**Worked example, the simple diamond.** For `O` at the top, `X` and `Y` deriving from it, and `A`
deriving from both:

$$L(A)=[A]+\mathrm{merge}([X,O,\text{object}],[Y,O,\text{object}],[X,Y])$$

Take `X` (in no tail), then `Y` (which blocked `O`, since `O` sits in `Y`'s tail until `Y` is
removed), then `O`, then `object`, giving `[A, X, Y, O, object]`:

```python
# code/ch004/l04_c3_mro.py (excerpt)
class O: pass
class X(O): pass
class Y(O): pass
class A(X, Y): pass
```

Verified output (CPython 3.13.5):

```text
--- the simple diamond: O <- {X, Y} <- A ---
  A.__mro__: ['A', 'X', 'Y', 'O', 'object']
```

**Worked example, the monotonicity stress test** (the case that defeats the naive 2.2 algorithm but
resolves cleanly under C3):

```text
--- Pedroni's monotonicity stress test ---
  Z.__mro__: ['Z', 'K1', 'K2', 'K3', 'Do', 'Ao', 'Bo', 'Co', 'Eo', 'object']
  matches the hand computation [Z,K1,K2,K3,D,A,B,C,E,object].
```

**When C3 fails.** If the constraints contradict, there is no consistent order and the class cannot be
built:

```text
--- an impossible hierarchy is rejected at class-creation time ---
  TypeError: Cannot create a consistent method resolution order (MRO) for bases Bad1, Bad2
```

`Bad3(Bad1, Bad2)` where `Bad2(Bad1)` demands `Bad1` before `Bad2` (local precedence of the base list)
and `Bad1` after `Bad2` (monotonicity through `Bad2`), which cannot both hold.

**`super()` follows the MRO, not the parent.** `super().method()` dispatches to the *next* class in
`type(self).__mro__` after the current one, which is why cooperative multiple inheritance works only
when every class in the chain calls `super()`. This is the practical payoff of C3: the MRO is a single
linear chain the whole hierarchy agrees on, so `super()` has an unambiguous "next."

---

## 4.6 Instance lifecycle: `__new__` versus `__init__`

CPython splits construction into two slots:

- **`__new__` to `tp_new`**: a *static* method that **allocates** and returns the instance, typically
  via `super().__new__(cls)`, ultimately `PyType_GenericNew`, which sets up the `PyObject` header
  (`ob_refcnt`, `ob_type`) from Chapter 19. It runs first.
- **`__init__` to `tp_init`**: an instance method that **initializes** the already-allocated object and
  must return `None`. It runs only if `__new__` returned an instance of `cls`.

```python
# code/ch004/l05_new_vs_init.py
class Lifecycle:
    def __new__(cls, *args, **kwargs):
        print("  __new__ (allocate)")
        return super().__new__(cls)
    def __init__(self, v):
        print("  __init__ (initialize) with", v)
        self.v = v
```

Verified output (CPython 3.13.5):

```text
--- order of construction ---
  __new__ (allocate)
  __init__ (initialize) with 7
  obj.v: 7

--- returning a different type from __new__ silently skips __init__ ---
  Sneaky() returned: 42 (an int; __init__ was skipped)
```

The split is what makes immutable types possible: `int`, `str`, `tuple`, and frozen dataclasses do
their work in `__new__`, because by the time `__init__ ` could run there is nothing left to mutate.
Override `__new__` to control allocation (singletons, instance caching, subclassing immutables);
override `__init__` for ordinary setup. And note the trap the listing demonstrates: returning an
object of a *different* type from `__new__` silently skips `__init__`, because the "instance of `cls`"
condition fails.

---

## 4.7 Measurement: what an attribute actually costs

Two pieces of folklore attach to this chapter's material: that `property` is "basically free" and that
`__slots__` is "a speed optimization." Both are testable, and both are wrong in the direction that
matters.

**Methodology.** `code/ch004/bench_attribute_access.py`, through `_harness/bench.py`. Access speed is
1000 reads per timed loop of an attribute stored three ways: a plain instance dict, a `__slots__`
member, and a `property`. `min` is the headline statistic; ratios are within this one interpreter.
Memory is measured separately with `tracemalloc`, which is deterministic. CPython 3.13.5, `-O2`,
computed gotos on, Apple M3 Pro, macOS 27.0, arm64. Access ratios reproduced to two decimal places
across runs; memory figures are exact.

| storage | access ratio | bytes/instance |
|---|---|---|
| instance dict | 1.00x | 88 |
| `__slots__` | **1.00x** | **48** |
| `property` | **2.08x** | (backing dict) |

**Two corrections fall out.** First, `__slots__` is *not* faster than a plain instance dict for
access, at 1.00x. The specializing interpreter turns both into an inline-cached direct read,
`LOAD_ATTR_INSTANCE_VALUE` for the dict-backed attribute and `LOAD_ATTR_SLOT` for the slot (Chapter
17), and the two paths cost the same. The real payoff of `__slots__` is the memory column: **48 bytes
against 88, a 45% saving**, because there is no per-instance `__dict__`. Reach for `__slots__` when you
have many small objects and memory matters, not when you want faster attribute reads.

Second, `property` genuinely costs, at **2.08x**, and the reason is structural rather than incidental:
every read calls a Python function, the getter, and a Python function call cannot be specialized down
to a direct load the way a bare attribute can. That is a fine price for validation or a computed
value, and a poor one for a getter that just returns a stored field. If a property's body is `return
self._x`, it is buying you nothing but the 2x.

The lesson generalizes the chapter: the descriptor protocol is uniform and elegant, but the three ways
of using it, bare attribute, slot, and property, have measurably different costs, and the costs do not
match the folklore. Measure the one you are about to put in a hot path.

---

## 4.8 Edges and failure modes

**A method is not identity-stable.** §4.4. `obj.m is obj.m` is `False`. Never use a bound method as a
dictionary key expecting identity, and never compare bound methods with `is`; use `==`, which compares
`__func__` and `__self__`.

**Shadowing a method with an instance attribute.** §4.3. A non-data descriptor loses to the instance
dict, so `self.method = something` in `__init__` silently overrides the class method for that instance.
Usually a bug; occasionally a deliberate per-instance override, but write it on purpose.

**Implementing only `__get__` when you need write interception.** §4.2. A non-data descriptor cannot
stop an assignment; the value lands in the instance dict and shadows the descriptor forever after.
Define `__set__` (making it a data descriptor) if writes must be intercepted.

**Real work in `__init__` for an immutable type.** §4.6. It must go in `__new__`; `__init__` is too
late and, for a genuinely immutable object, has nothing to write to.

**Returning the wrong type from `__new__`.** §4.6. It silently skips `__init__`. If `__new__` returns
something that is not an instance of `cls`, the initializer does not run, and no error is raised.

**Forgetting `super().__init__()` in a cooperative hierarchy.** §4.5. It breaks the `super()` chain, so
later classes' initializers never run. In multiple inheritance this is a silent, order-dependent bug.

**Heavy `__getattribute__`.** It runs on *every* attribute access and is easy to make accidentally
quadratic or infinitely recursive; always delegate through `super().__getattribute__`.

**Mutating a class in a hot path.** Monkeypatching or setting a class attribute invalidates the type
version cache and de-optimizes every dependent `LOAD_ATTR` site (Chapter 17). Configure behavior at
class-definition time.

---

## 4.9 Connections

**Backward.** The `PyObject` and `PyTypeObject` headers whose slots this chapter drives are Chapter 19
(**Deep A**); `int.__add__` being a `wrapper_descriptor` is that header's slot table made visible. The
symbol table and the compiler that turn `obj.name` into a `LOAD_ATTR` are Chapter 2.

**Forward.** The complete slot table (`tp_as_number`, `tp_as_sequence`, `tp_as_mapping`,
`PyGetSetDef`), metaclasses, and how `type` builds a class are **Deep C**, which owns everything this
chapter deliberately stopped short of. `property` and context managers in idiomatic use are Chapter 5.
`__slots__` and `weakref` in depth are **Deep A**. The `LOAD_ATTR` specialization and the type version
cache that make §4.7's numbers what they are is Chapter 17. `functools.cached_property`, a non-data
descriptor with a deliberate one-shot cache, is **Deep Q**.

**Across books.** The unification that lets `int.__add__` be an ordinary attribute is exactly what lets
a C++ class exposed through `nanobind` present as a normal Python type with normal methods: `nanobind`
fills the same `PyTypeObject` slots CPython fills for a built-in, so from Python there is no seam. A
C++ operator overloaded and bound this way appears as a `wrapper_descriptor` on the bound type, just
like `int.__add__`. **Deep M** owns that boundary; this chapter is why it can be seamless.

---

## 4.10 Exercises

**1. Predict the precedence.** Given a class with a `property` named `x` and this code, state what each
line does and why:

```python
obj = C()
obj.__dict__["x"] = 99      # (a) does this succeed? does it shadow the property?
print(obj.x)                # (b)
del C.x                      # (c) now what is obj.x?
```

Explain (a) in terms of §4.3's step 2 versus step 3, and (c) in terms of what happens to the lookup
when the data descriptor is removed from the class.

**2. Build a lazy attribute two ways.** Implement a "compute once, then cache" attribute first as a
non-data descriptor (like `functools.cached_property`) and then as a data descriptor. One of them lets
a later instance-dict write override the cache and one does not. Show which, explain why using §4.3,
and argue when each behavior is the one you want.

**3. Hand-compute an MRO, then check it.** Design a four-class diamond where the naive depth-first
order and the C3 order *differ*, compute both by hand, and confirm C3 with `__mro__`. Then add one base
that makes the hierarchy inconsistent and predict the exact `TypeError` before running it.

**4. Measure your own property.** Take the benchmark from §4.7 and add a fourth case: a `property`
whose getter does real work (say, `return self._x * 2 + 1`). Predict, before running, where it lands
relative to the bare-property 2.08x, and explain the result in terms of what the specializing
interpreter can and cannot do to a function call. Report to the standard of §4.7.

**5. The design question.** Python unified types and classes so that `int` and a user class are the
same kind of object, which is what makes `int.__add__` an ordinary attribute and `class Money(int)`
possible. Java deliberately did *not* do this: its primitives are not objects. Argue what Python buys
with unification and what it pays, using this chapter's measurements. Your answer must address the
per-instance header cost from Chapter 19, the `property` overhead from §4.7, and why a language aimed
at numeric performance might reasonably make Java's choice instead.

---

## 4.11 Summary and cross-references

- Python 2.2 **unified types and classes** (PEP 252/253): every class is a `PyTypeObject` descending
  from `object`, and a Python method and a C slot bridge in both directions (`int.__add__` is a
  `wrapper_descriptor`). Python 3 has only new-style classes.
- A **descriptor** customizes attribute access via `__get__`/`__set__`/`__delete__`. **Data
  descriptors** (with `__set__`/`__delete__`) outrank the instance dict; **non-data descriptors** (only
  `__get__`) do not. This one rule explains methods, `property`, `classmethod`, `staticmethod`, and
  `__slots__`, and it is why a method read twice is two objects.
- `PyObject_GenericGetAttr` resolves `obj.name` as: data descriptor, then instance dict, then non-data
  descriptor or class attribute, then `__getattr__`.
- **C3 linearization** gives multiple inheritance a single order with **local precedence** and
  **monotonicity**; `super()` walks that order; inconsistent hierarchies raise `TypeError` at class
  creation.
- Construction is **`__new__` (allocate) then `__init__` (initialize)**; immutables work in `__new__`,
  and returning the wrong type from `__new__` skips `__init__`.
- **Measured:** `__slots__` is 1.00x of a plain instance dict for *access* (both specialize) but saves
  **45% memory** (48 vs 88 bytes); a `property` costs **2.08x** because it calls a Python function per
  read. The folklore about both is backwards.

**Cross-references.** The `PyObject`/`PyTypeObject` header → Chapter 19 (Deep A). `property` in
idiomatic use → Chapter 5. The full slot table, metaclasses, and `type` → Deep C. `__slots__` and
`weakref` → Deep A. `LOAD_ATTR` specialization and the type version cache → Chapter 17.
`functools.cached_property` → Deep Q. The C-API boundary that makes bound C++ types seamless → Deep M.
