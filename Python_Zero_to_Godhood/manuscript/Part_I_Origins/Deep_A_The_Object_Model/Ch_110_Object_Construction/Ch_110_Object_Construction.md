# Chapter 25: Object Construction

`C(args)` looks like one operation.
It is two, and the split is the subject of this chapter.
Calling a class runs `__new__` to **create** the instance and then `__init__` to **initialize** it, and almost everyone writes only the second, uses only `self`, and never thinks about the first, which is exactly right until the day it is not.
The day it is not comes in three shapes: you subclass an *immutable* type and discover `__init__` runs too late to set the value; you want `C(x)` to sometimes return an *existing* object rather than a new one; or you want to intercept creation itself.
All three are `__new__`, and understanding the two-step protocol turns those from mysteries into three-line solutions.

The distinction is precise.
`__new__(cls, *args)` receives the *class* and must **return an instance**, it allocates.
`__init__(self, *args)` receives the *already-created* instance and **returns `None`**, it configures.
Between them sits `type.__call__`, which orchestrates: call `__new__`, and *if* it returned an instance of the class, call `__init__` on it.
That "if" is load-bearing, and it is where the surprising behaviours live.

**This is the canonical home for instance construction.**
It follows Chapter 20 (the call that reaches `type.__call__` is `__call__` on the metatype), Chapter 19 (the small-integer cache in §25.2 is a `__new__`-style flyweight in C), and defers the metaclass's own `__call__` and `__init_subclass__`/`__set_name__` creation hooks to **Deep C**.

## Section index

- **25.1** Two steps: `__new__` creates, `__init__` initializes
- **25.2** Why `__new__` exists: immutable types and instance control
- **25.3** Measurement: a caching `__new__` and the flyweight payoff
- **25.4** Edges and failure modes
- **25.5** Connections
- **25.6** Exercises
- **25.7** Summary and cross-references

Listings live under `code/ch110/` and are re-executed by `make verify` on both verification interpreters.

---

## 25.1 Two steps: `__new__` creates, `__init__` initializes

```python
# code/ch110/l01_new_then_init.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- C(v) runs __new__ then __init__ ---
  1. __new__  creates the instance (cls = Trace)
  2. __init__ initializes it (v = 5)
  result: t.v = 5
--- __new__ is implicitly a staticmethod ---
  type(Trace.__dict__['__new__']) : staticmethod
--- if __new__ returns a non-instance of cls, __init__ is SKIPPED ---
  ReturnsForeign.__new__ returns a str, not a ReturnsForeign
  result: 'not an instance of cls'   (a str; __init__ never ran)
--- __init__ must return None ---
  __init__ returning 42 raises TypeError : True
--- the rule ---
  __new__ makes the object (returns it); __init__ sets it up (returns
  None); type.__call__ runs __new__ then, if it got a cls instance, __init__
```

`Trace(5)` prints `__new__` first, then `__init__`: creation before initialization, always.
`__new__` receives `cls` (the class being instantiated) because there is no instance yet, that is what it is about to make, and it is implicitly a **staticmethod** (the output confirms it), which is why it takes `cls` explicitly rather than getting a bound `self`.
The normal body is `return super().__new__(cls)`: delegate to the base (ultimately `object.__new__`) to allocate, then return the new object.
`__init__` then receives that object as `self` and configures it.

Two rules fall out of `type.__call__`'s logic, and both are visible.
`__init__` **must return `None`**, returning `42` raises `TypeError`, because `__init__`'s job is to mutate `self` in place, and a return value would be silently discarded, so Python treats a non-`None` return as a bug.
And **if `__new__` returns an object that is not an instance of `cls`, `__init__` is skipped entirely**: `ReturnsForeign.__new__` returns a `str`, and `__init__` never runs, the final object is that `str`.
This is not a curiosity; it is the mechanism that makes caching `__new__`s (§25.2) safe, a `__new__` returning a cached instance of a *different* configuration will not have `__init__` re-run on it, though the common flyweight case returns an instance of `cls` and must guard against re-initialization (§25.4).

---

## 25.2 Why `__new__` exists: immutable types and instance control

If `__init__` handles the 95% case, why does `__new__` exist at all? Two reasons that `__init__` structurally cannot serve.

```python
# code/ch110/l02_immutable_and_cache.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- immutable subclass: value fixed in __new__ ---
  UpperStr('hello') : HELLO
  is a real str     : True
--- instance control: __new__ returns a SHARED instance ---
  Color('red') is Color('red')  : True   (same cached object)
  Color('red') is Color('blue') : False
  distinct objects created      : 2   (red, blue)
--- the rule ---
  use __new__ to set immutable state (before creation) and to control
  which instance is returned (caching, singletons); __init__ cannot
```

**Immutable types.**
`str`, `int`, `tuple`, `frozenset`, and `bytes` fix their value at creation and cannot be mutated afterward, that is what immutable means.
So a subclass that wants to *transform* the value, `UpperStr` uppercasing its input, cannot do it in `__init__`, because by the time `__init__` runs the string already exists and its characters cannot be changed.
The transformation has to happen *before* the object exists, which is exactly `__new__`'s window: `super().__new__(cls, value.upper())` passes the uppercased value to `str`'s own `__new__`, and the resulting object is `HELLO`, a genuine `str` subclass instance.
This is *the* reason to override `__new__` for value types: immutable state must be set at creation.

**Instance control.**
Because `__new__` decides *which* object to return, it can return one that already exists.
`Color`'s `__new__` keeps a cache keyed by name and returns the cached instance for a repeated name, so `Color("red") is Color("red")` is `True`, two "constructions", one object.
This is the **flyweight** (or interning, or memoized-singleton) pattern, and `__init__` cannot express it because `__init__` never chooses the object; it only configures whatever `__new__` already made.
The output shows only two objects created for however many `Color(...)` calls, which is the memory lever §25.3 measures, and it is precisely how CPython implements the small-integer cache and string interning of Chapter 19, a `__new__`-shaped decision, in C, to hand back a shared object instead of a fresh one.

---

## 25.3 Measurement: a caching `__new__` and the flyweight payoff

**Methodology.** `code/ch110/bench_construction.py`.
One million constructions of objects taking only **8 distinct values**, two ways: `Fresh` always allocates; `Cached` uses a `__new__` that returns a shared instance per value.
Peak memory via `tracemalloc`, plus a count of distinct objects (`id`).
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64; memory byte-identical on both interpreters.

| 1,000,000 constructions, 8 distinct values | memory | distinct objects |
|---|---|---|
| `Fresh` (always allocate) | 46.2 MB | 1,000,000 |
| `Cached` (flyweight `__new__`) | 8.1 MB | **8** |

The caching `__new__` creates **8 objects** where `Fresh` creates a million, and uses **6x** less memory.
The remaining 8.1 MB is almost entirely the list of a million *pointers* (8 bytes each is ~8 MB); the objects themselves are 8, negligible.
`Fresh` pays for a million distinct `__slots__` objects on top of the pointer array.

The finding is not "caching is faster" (constructing through a cache does real work, a dict lookup, per call); it is that **`__new__` controls whether an object is created at all**, which is a lever `__init__` does not have.
When a type has few distinct values that recur constantly, enums, colors, currency codes, small integers, interned symbols, a caching `__new__` collapses "a million logical values" into "a handful of physical objects", and every equality-by-identity check on them becomes an `is` on a shared object.
CPython applies exactly this reasoning to `-5..256` (Chapter 19).
The constraint, and it is a hard one, is that flyweight objects **must be immutable**: if two call sites share one object and one mutates it, the other sees the change.
So the pattern is safe for value types (where mutation is meaningless) and dangerous for anything with per-instance mutable state, which §25.4 makes precise.

---

## 25.4 Edges and failure modes

**`__init__` must return `None`.** §25.1.
It configures `self` in place; a return value is a bug and raises `TypeError`.

**`__new__` returning a non-`cls` instance skips `__init__`.** §25.1.
Deliberate for some patterns, a trap if unintended: override `__new__`, forget to return a `cls` instance, and your `__init__` silently never runs.

**A flyweight `__new__` re-runs `__init__` on the cached object.** §25.2.
When `__new__` returns a cached instance *of `cls`*, `type.__call__` still calls `__init__` on it every time. If `__init__` does real work, it re-initializes the shared object on every "construction". Fixes: put all setup in `__new__` and make `__init__` a no-op (as the listings do), or guard `__init__` with an "already initialized" flag. This is the most common flyweight bug.

**Flyweight objects must be immutable.** §25.3.
Sharing a mutable object across call sites means one site's mutation is visible to all. Only cache value types with no per-instance mutable state.

**`__new__` signature must accept the constructor's arguments.**
`type.__call__` passes the same `*args, **kwargs` to both `__new__` and `__init__`. If you override `__new__(cls)` but the class is called as `C(x)`, `__new__` gets `x` and must accept it (or the base `object.__new__`, which ignores extra args only when `__init__` is overridden, will complain). Keep the signatures compatible.

**`object.__new__` rejects extra arguments (usually).**
`object.__new__(cls, x)` raises `TypeError` *unless* the class also overrides `__init__` (a historical special case). Subtle, and a reason to override both or neither when passing constructor arguments through.

**Caching leaks memory if unbounded.**
A flyweight cache holds every distinct value forever (a strong reference). For an unbounded key space this is a leak; use a `WeakValueDictionary` or a bounded cache when values are not a small fixed set.

**Do not confuse `__new__` with a factory.**
For most "return different types depending on input" needs, a classmethod factory (`C.from_x(...)`) or a module function is clearer than a polymorphic `__new__`. Reserve `__new__` for immutable state and genuine instance control.

---

## 25.5 Connections

**Backward.**
The call `C(args)` is `type(C).__call__(C, args)`, a special-method dispatch (Chapter 20) on the metatype. The small-integer cache and string interning (Chapter 19) are the flyweight of §25.2 implemented in C. A `__slots__` value type (Chapter 22) is the natural thing to make immutable and cache. The immutability that forces `__new__` for `str`/`tuple` subclasses is the same immutability that makes them hashable value types (Chapter 23).

**Forward.**
`type.__call__` itself, and how a metaclass overrides it to control construction at the class level (the singleton-metaclass pattern), plus `__init_subclass__` and `__set_name__` (creation-time hooks that fire when a *class* is built), are **Deep C**. `@dataclass`, which generates `__init__` (and can generate `__new__`-adjacent behaviour via `frozen`), is a **Deep C** ergonomics topic. `WeakValueDictionary` for safe unbounded caches is **Deep B** (weak references and the GC).

**Across books.**
Instance control is how **Book I**'s value types stay cheap at scale: interned symbols, cached currency and instrument identifiers, and shared immutable constants are flyweights whose `__new__` hands back one object per distinct value, so a system that mentions the symbol a million times holds it once. The order-book system interns its instrument and side objects exactly this way, and uses `__new__` on its immutable price and quantity types to normalize and validate the value at creation, before the object exists and can be misused, the §25.2 pattern applied where correctness and memory both matter.

---

## 25.6 Exercises

**1. Watch the two steps.** Reproduce §25.1: a class whose `__new__` and `__init__` both print. Confirm the order, confirm `__new__` is a staticmethod, and make `__new__` return a foreign object to show `__init__` is skipped. Explain each in terms of `type.__call__`.

**2. Subclass an immutable.** Write a `PositiveInt(int)` subclass whose `__new__` raises `ValueError` for negative inputs and otherwise returns a normal `int` value. Explain why this must be `__new__` and cannot be `__init__`.

**3. Build a flyweight, then break it.** Implement §25.2's caching `Color`. Then give it a mutating `__init__` (say `self.count += 1`) and show that "constructing" an existing color re-runs `__init__` on the shared object. Fix it two ways (no-op `__init__`, and an initialized-flag guard) and explain the §25.4 trap.

**4. Measure it.** Reproduce §25.3 for a value type of your own with a small distinct-value set. Report memory and object count for fresh versus cached. Then make the distinct-value count large (say 100,000) and show the saving shrink, and explain when caching stops paying.

**5. The design question.** CPython splits construction into `__new__` and `__init__` rather than a single constructor. Argue what the split buys, using immutable subclassing (§25.2) and instance control (§25.3), and name the cost (the §25.4 re-initialization trap, the argument-passing subtleties). Would a single constructor with an explicit `return self` have been simpler and sufficient? Defend your answer against the immutable-`str` case.

---

## 25.7 Summary and cross-references

- **`C(args)` is two steps**, orchestrated by `type.__call__`: **`__new__(cls, ...)` creates** and returns the instance (allocates; implicitly a staticmethod), then **`__init__(self, ...)` initializes** it in place and **must return `None`**.
- **If `__new__` returns a non-`cls` instance, `__init__` is skipped.**
- **`__new__` exists for what `__init__` cannot do:** setting **immutable** state before the object exists (`str`/`int`/`tuple` subclasses), and **instance control**, returning a shared/cached object (the flyweight pattern, as CPython does for small ints).
- **Measured:** a caching `__new__` turns 1,000,000 constructions of 8 distinct values into **8 objects** (8.1 vs 46.2 MB, **6x** less). Flyweight objects **must be immutable**, and a flyweight's `__init__` still re-runs on the cached object (make it a no-op or guard it).
- **Edges:** keep `__new__`/`__init__` signatures compatible; `object.__new__` rejects extra args unless `__init__` is overridden; unbounded caches leak (use `WeakValueDictionary`); prefer a classmethod factory over a polymorphic `__new__`.

**Cross-references.** `C(...)` as metatype `__call__` → Chapter 20. Small-int cache / interning as C-level flyweights → Chapter 19. Immutable, hashable value types → Chapters 22, 23. `type.__call__` override, metaclass singletons, `__init_subclass__` → Deep C. Weak-reference caches → Deep B.
