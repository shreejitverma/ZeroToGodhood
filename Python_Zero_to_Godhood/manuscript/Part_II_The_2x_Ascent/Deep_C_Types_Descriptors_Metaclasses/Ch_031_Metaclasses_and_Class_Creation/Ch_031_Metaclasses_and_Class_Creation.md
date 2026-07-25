# Chapter 31: Metaclasses and Class Creation

Chapter 4 established a fact that sounds like a riddle: a class *is* an object, an instance of `type`.
If a class is an instance, then something *created* it, and that something is `type` itself. This
chapter follows that thread to its end. If `type` builds classes, then `class` is not special syntax
for a unique kind of construction; it is sugar over a function call, and you can make the call
yourself, or replace it. The tool for replacing it is a **metaclass**, and metaclasses are
simultaneously the most powerful and the most overused feature in Python's object model.

The power is real: a metaclass runs code every time a class is *defined*, letting a framework enforce
invariants, register subclasses, or rewrite a class before any instance exists. The overuse is also
real: for most of what people historically reached for metaclasses to do, Python 3.6 added lighter,
composable hooks (`__init_subclass__` and `__set_name__`, PEP 487) that do the job without the metaclass
costs. This chapter opens **Deep C**, the volume on types, descriptors, and metaclasses that Chapter 4
deferred to. It covers how a class is actually built, what a metaclass can do, and, importantly, when
*not* to use one.

## Section index

- **31.1** A class is built by `type`
- **31.2** Metaclasses: hooking class creation
- **31.3** The lighter tools: `__init_subclass__` and `__set_name__` (PEP 487)
- **31.4** When to use a metaclass, and when not to
- **31.5** Edges and failure modes
- **31.6** Connections
- **31.7** Exercises
- **31.8** Summary and cross-references

Listings live under `code/ch031/` and are re-executed by `make verify` on both interpreters.

---

## 31.1 A class is built by `type`

`type` has two entirely different jobs, which share a name for historical reasons. With one argument,
`type(x)` returns the type of `x`. With three arguments, `type(name, bases, namespace)` *builds a new
class*, and that three-argument form is exactly what the `class` statement compiles to:

```python
# code/ch031/l01_type_and_metaclass.py
Dynamic = type("Dynamic", (object,), {"x": 1, "greet": lambda self: "hi"})
```

Verified output (CPython 3.13.5):

```text
--- a class built at runtime with type() ---
  Dynamic.__name__ : Dynamic
  Dynamic().x      : 1
  Dynamic().greet(): hi
  type(Dynamic)    : type (its metaclass is type)
```

`type("Dynamic", (object,), {...})` produces a real class, with attributes and methods, identical to
what `class Dynamic(object): x = 1; ...` would produce. The `class` statement is sugar: it collects the
name, the bases, and the body's namespace, and calls the metaclass (default `type`) with them. And the
tower bottoms out cleanly, as the listing also shows: `type(type) is type`, `type` is its own metaclass,
and `type(object) is type`, even the root base class is an instance of `type`. There is no infinite
regress; `type` is the fixed point.

The **metaclass** is the callable that gets invoked to build the class, `type` by default. Change it,
and you change how the class is built.

---

## 31.2 Metaclasses: hooking class creation

A metaclass is a subclass of `type`. Its `__new__` (and `__init__`) run when a class using it is
*defined*, receiving the same `(name, bases, namespace)` and returning the class object. This lets it
inspect or modify the class before it exists:

```python
# code/ch031/l01_type_and_metaclass.py (excerpt)
class Meta(type):
    def __new__(mcs, name, bases, namespace):
        namespace["created_by_meta"] = True         # inject at creation
        return super().__new__(mcs, name, bases, namespace)

class WithMeta(metaclass=Meta):
    pass
```

Verified output (CPython 3.13.5):

```text
--- a metaclass customizes the class object as it is built ---
  WithMeta.created_by_meta: True
  type(WithMeta)          : Meta (Meta, not type)
```

`Meta.__new__` ran when `WithMeta` was defined, injected `created_by_meta`, and `type(WithMeta)` is now
`Meta` rather than `type`, `WithMeta` is an instance of its metaclass. The critical timing: a
metaclass's `__new__` runs **once per class definition**, not once per instance. This is what a
framework exploits, ORMs use a metaclass to scan a model class's fields at definition time and wire up
the mapping, `abc.ABCMeta` uses one to enforce abstract methods, and enum (Chapter 10) uses `EnumMeta`
to turn `NAME = value` into singleton members. All of that work happens once, when the class is built.

The classic metaclass costs, which motivate §31.3: a metaclass changes the class's *type*, so two
classes with different metaclasses cannot be combined without a metaclass that inherits from both (the
"metaclass conflict"), and metaclass code is notoriously hard to read because it operates one level of
abstraction up from the class it builds.

---

## 31.3 The lighter tools: `__init_subclass__` and `__set_name__` (PEP 487)

Most metaclass uses are one of two patterns: *do something each time this class is subclassed*
(registration, validation) or *tell a descriptor its name*. Python 3.6 added a hook for each, and
neither requires a metaclass:

```python
# code/ch031/l02_init_subclass.py
class Plugin:
    registry = []
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Plugin.registry.append(cls.__name__)
```

Verified output (CPython 3.13.5):

```text
--- __init_subclass__ registers subclasses, no metaclass needed ---
  Plugin.registry: ['AudioPlugin', 'VideoPlugin']
--- __init_subclass__ accepts keywords from the class definition ---
  Config.required_field: api_key
--- __set_name__ gives a descriptor its attribute name at class creation ---
  Host().first : I am 'first'
  Host().second: I am 'second'
```

**`__init_subclass__`** is a classmethod on the *base* that runs each time the base is subclassed, so
`Plugin` collected `AudioPlugin` and `VideoPlugin` automatically, the subclass-registration pattern with
no metaclass. It even accepts keyword arguments from the class definition line (`class Config(Validated,
required="api_key")`), which a framework uses for per-subclass configuration. **`__set_name__`** (Chapter
4) is called on each descriptor at class creation with its attribute name, so a descriptor learns it is
`first` or `second` without the class author repeating the name. Together they cover the bulk of what
metaclasses were used for.

The advantages over a metaclass are decisive for these cases: they **compose** (a class can have many
bases each with an `__init_subclass__`, which all run, where two metaclasses conflict), they do not
change the class's type, and they read at the same level of abstraction as ordinary methods. The
guidance follows directly: reach for `__init_subclass__` and `__set_name__` first.

---

## 31.4 When to use a metaclass, and when not to

A metaclass is the right tool only when you need to change something a class *is*, not just react to its
creation. Legitimate cases: controlling the class's `__call__` (so `MyClass()` does something custom
before `__new__`, as a true singleton metaclass does), changing the namespace *type* used during class
body execution (as `enum` does to capture member order and reject duplicates), or intercepting attribute
access *on the class itself* (`__getattr__` on the metaclass). These require operating at the metaclass
level because they concern the class object's own behavior, not its subclasses.

Everything else, subclass registration, field validation, descriptor naming, attribute injection, is
better done with `__init_subclass__`, `__set_name__`, a class decorator (Chapter 5, which
`@dataclass` uses), or `__init_subclass__` plus a decorator together. A class decorator runs after the
class is built and is the simplest tool of all when you do not need to influence subclasses. The
decision rule: **use the least powerful tool that works.** Class decorator, then PEP 487 hooks, then a
metaclass only when you genuinely must change the class's own machinery. A metaclass reached for
reflexively is a maintenance burden and a composition hazard; a metaclass used deliberately for one of
its true jobs is irreplaceable.

---

## 31.5 Edges and failure modes

**The metaclass conflict.** §31.2. Combining two classes with different metaclasses raises `TypeError`
unless you write a metaclass inheriting from both. This is the composition hazard PEP 487 avoids; prefer
`__init_subclass__` when you only need subclass behavior.

**Forgetting `super().__init_subclass__()`.** §31.3. In a cooperative hierarchy, omitting the `super()`
call breaks the chain and later hooks never run, the same cooperative-inheritance trap as `__init__`
(Chapter 4).

**Metaclass `__new__` runs once per class, not per instance.** §31.2. Do not put per-instance logic in a
metaclass; it runs at class-definition time. Per-instance construction is `__new__`/`__init__` on the
class (Chapter 4).

**Reaching for a metaclass reflexively.** §31.4. Most uses are better served by a class decorator or PEP
487 hooks. A metaclass is the heaviest tool; justify it.

**`type()` with a mutable namespace.** The namespace dict passed to `type()` is consumed; do not reuse it
across classes expecting independence. Build a fresh dict per class.

---

## 31.6 Connections

**Backward.** That a class is a `PyTypeObject` instance of `type`, and the descriptor protocol
`__set_name__` serves, are Chapter 4. Class decorators, the lighter alternative for post-creation
modification, are Chapter 5. `EnumMeta`, a real metaclass doing a real metaclass job, is Chapter 10. The
`@dataclass` decorator that generates a class without a metaclass is Chapter 13.

**Forward.** The full `PyTypeObject` slot table, the descriptor protocol in depth, and `abc.ABCMeta` are
the rest of **Deep C**. The type system that reads the classes metaclasses build is **Deep I**.

**Across books.** Metaclasses and `__init_subclass__` are how Book II builds framework machinery at the
seams. A **Book III** agent framework that registers tool classes as they are defined uses
`__init_subclass__` for a self-populating tool registry, no metaclass, no manual registration. A binding
layer over **Book I** C++ types can use a metaclass to wire each bound class to its C++ counterpart at
definition time. **Deep I** owns the type-system consumption; this chapter is the class-creation
machinery frameworks hook.

---

## 31.7 Exercises

**1. Build a class three ways.** Create the same class with the `class` statement, with `type()`
directly, and with a metaclass that injects one attribute. Confirm all three produce equivalent classes,
and explain what the `class` statement did that the `type()` call made explicit.

**2. Replace a metaclass with PEP 487.** Take a metaclass that registers subclasses and rewrite it using
`__init_subclass__`. Show both produce the same registry, then demonstrate a case (two independent base
hierarchies combined) where the `__init_subclass__` version composes and the metaclass version conflicts.

**3. Trigger the metaclass conflict.** Define two classes with two different metaclasses and try to create
a class inheriting from both. Observe the `TypeError`, then resolve it with a combined metaclass. Explain
why the conflict exists.

**4. Find the right tool.** For each task, name the least powerful tool that works and justify it: (a)
add a `created_at` timestamp to every subclass, (b) make a class a singleton, (c) validate that every
subclass defines a `handle` method, (d) capture the definition order of a class's attributes. Explain why
a metaclass is or is not needed for each.

**5. The design question.** PEP 487 added `__init_subclass__` and `__set_name__` specifically to reduce
metaclass use. Argue why the core team chose to add narrow hooks rather than make metaclasses easier to
use or compose. Your answer must address the metaclass conflict, readability, and the principle of least
power.

---

## 31.8 Summary and cross-references

- A **class is built by `type`**: `type(name, bases, namespace)` constructs a class, and the `class`
  statement is sugar over calling the metaclass (default `type`) with exactly those arguments. `type` is
  its own metaclass (`type(type) is type`), so the tower bottoms out.
- A **metaclass** (a subclass of `type`) hooks class creation: its `__new__` runs **once per class
  definition**, letting it inspect or modify the class before any instance exists. The costs are the
  metaclass conflict and poor readability.
- **PEP 487** added `__init_subclass__` (react to each subclass, composable) and `__set_name__` (name a
  descriptor), which cover most historical metaclass uses **without a metaclass**.
- **Use the least powerful tool:** class decorator, then PEP 487 hooks, then a metaclass only to change
  the class's own machinery (its `__call__`, its namespace type, class-level attribute access).

**Cross-references.** A class as a `PyTypeObject` and `__set_name__` → Chapter 4. Class decorators →
Chapter 5. `EnumMeta` → Chapter 10. `@dataclass` → Chapter 13. The slot table and descriptor protocol in
depth → the rest of Deep C. The type system → Deep I. Framework machinery at the seams → Deep I.
