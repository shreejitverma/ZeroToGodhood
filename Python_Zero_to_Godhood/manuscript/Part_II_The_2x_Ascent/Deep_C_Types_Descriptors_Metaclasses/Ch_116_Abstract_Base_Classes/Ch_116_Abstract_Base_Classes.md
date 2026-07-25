# Chapter 35: Abstract Base Classes

Python is a duck-typed language: if it has a `read` method, it is file-enough.
So why does it also have *abstract base classes*, a nominal-interface mechanism straight out of Java and C++?
The answer is that duck typing has two gaps, and ABCs fill exactly those, without abandoning it.
The first gap: duck typing defers the error to the latest possible moment, a class missing a required method fails with `AttributeError` deep inside some algorithm, far from the mistake.
The second: duck typing gives you no way to *ask* "does this thing support the sequence protocol?" short of trying every method.
ABCs answer both, enforcing an interface at construction time and making `isinstance(x, Sequence)` a real, structural question.

The mechanism, in one line, is a metaclass (`ABCMeta`) that does two things: it refuses to instantiate a class with unimplemented `@abstractmethod`s, and it overrides `isinstance`/`issubclass` so a class can be recognised as a subtype **without inheriting**, by explicit registration or by a structural hook.
That last capability is the clever part: it is how `collections.abc` can say "anything with `__len__` is `Sized`" and reconcile nominal interfaces with duck typing.
The cost, which the measurement pins down, is that ABC `isinstance` checks are about **4.4x** slower than concrete ones, so ABCs are an interface and design tool, not a hot-path type test.

**This is the canonical home for abstract base classes.**
It is an application of the metaclass machinery of Chapter 31 (`ABCMeta` is a metaclass), uses the MRO of Chapter 34 (structural checks walk it), and connects to the special-method protocols of Deep A/F (`collections.abc` formalises `__len__`, `__iter__`, `__contains__` into named interfaces). Static-typing `Protocol` (structural typing checked by a type checker) is the compile-time cousin and lives in **Deep I**.

## Section index

- **35.1** `@abstractmethod`: enforcing an interface at construction
- **35.2** Virtual subclasses: `register()` and `__subclasshook__`
- **35.3** Measurement: the cost of an ABC `isinstance`
- **35.4** Edges and failure modes
- **35.5** Connections
- **35.6** Exercises
- **35.7** Summary and cross-references

Listings live under `code/ch116/` and are re-executed by `make verify` on both verification interpreters.

---

## 35.1 `@abstractmethod`: enforcing an interface at construction

```python
# code/ch116/l01_abstractmethod.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- the ABC itself cannot be instantiated ---
  Shape() -> TypeError (is abstract): True
--- a fully-implementing subclass is concrete ---
  Circle(2).area() : 12.56636   name: circle
--- a subclass missing an abstract method is STILL abstract ---
  Incomplete() -> TypeError (name unimplemented): True
--- isinstance/issubclass see the interface relationship ---
  isinstance(Circle(2), Shape) : True
  issubclass(Circle, Shape)    : True
--- the rule ---
  abc.ABC + @abstractmethod defines a required interface; the class
  cannot be instantiated until every abstract method is overridden
```

An ABC declares an interface by inheriting `abc.ABC` (whose metaclass is `ABCMeta`) and marking required methods `@abstractmethod`.
The enforcement is at **construction time**, which is the whole value.
`Shape()` raises `TypeError` because `Shape` has unimplemented abstract methods, you cannot instantiate an incomplete interface.
`Circle`, which implements *both* `area` and `name`, is concrete and instantiates normally.
`Incomplete`, which implements `area` but not `name`, is **still abstract** and still raises, the check requires *every* abstract method to be overridden.

Compare this to duck typing.
Without the ABC, `Incomplete()` would succeed, and the missing `name` would surface as an `AttributeError` whenever some code eventually called `.name()`, possibly in production, possibly far from the class definition.
The ABC moves that failure to the earliest possible point, **the moment you try to construct the object**, with a message that names the unimplemented method.
This is the same "fail at the boundary, not deep in the code" principle as the inconsistent-MRO `TypeError` (Chapter 34): surface design errors early and locally.
And `isinstance`/`issubclass` confirm the relationship (`Circle` is a `Shape`), so the ABC also serves as documentation and a checkable contract.

---

## 35.2 Virtual subclasses: `register()` and `__subclasshook__`

The feature that distinguishes Python's ABCs from Java interfaces: a class can be a subtype **without inheriting**.

```python
# code/ch116/l02_register_and_hook.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- register(): a virtual subclass (isinstance True, not in the MRO) ---
  isinstance(Widget(), Drawable) : True
  issubclass(Widget, Drawable)   : True
  Drawable in Widget.__mro__     : False   (NOT a real base)
--- __subclasshook__: STRUCTURAL membership, no registration needed ---
  isinstance(Connection(), SupportsClose) : True
  (Connection has close(), so the hook accepts it)
--- collections.abc uses this for the standard protocols ---
  isinstance([], Sized)    : True
  isinstance([], Iterable) : True
  isinstance(5, Iterable)  : False   (int has no __iter__)
--- the rule ---
  register() adds a virtual subclass; __subclasshook__ recognizes types
  structurally; both make isinstance work without real inheritance
```

Two mechanisms, both reconciling nominal interfaces with duck typing.

**`register()`** declares a **virtual subclass**.
`Drawable.register(Widget)` makes `isinstance(Widget(), Drawable)` and `issubclass(Widget, Drawable)` return `True`, yet `Drawable` is **not in `Widget`'s MRO`**, `Widget` inherits nothing, gets no methods, and its layout is unchanged.
This lets you retrofit an interface onto a class you do not own (a third-party type) or avoid a dependency (the implementer need not import your ABC).
The ABC vouches for the class; the class is oblivious.

**`__subclasshook__`** goes further: **structural** recognition.
`SupportsClose.__subclasshook__` returns `True` for any class with a `close` method, so `Connection` (never registered, never inheriting) *is* a `SupportsClose` because it structurally qualifies.
This is duck typing made *checkable*: "has the right methods" becomes an `isinstance` you can write.
It is exactly how `collections.abc` works: `isinstance([], Sized)` is `True` because `list` has `__len__`, `isinstance([], Iterable)` is `True` because it has `__iter__`, and `isinstance(5, Iterable)` is `False` because `int` has no `__iter__`, no registration anywhere, just structural checks over the MRO.

So Python's ABCs are a *hybrid*: nominal when you want enforcement (`@abstractmethod`, §35.1), structural when you want duck typing with a checkable question (`__subclasshook__`), and retrofittable when you want to classify types you do not control (`register()`).
That hybrid is deliberate, it is Python refusing to choose between "interfaces" and "duck typing" and taking the useful half of each.

---

## 35.3 Measurement: the cost of an ABC `isinstance`

The flexibility of §35.2 is not free: overriding `isinstance` means running Python-level logic where a concrete check runs C.

**Methodology.** `code/ch116/bench_isinstance_abc.py`.
`isinstance(x, ConcreteClass)` versus `isinstance(x, ABC)` versus `isinstance(x, collections.abc.Iterable)`.
`min` of 5 runs, 5,000,000 checks.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| `isinstance(x, ...)` | ns | vs concrete |
|---|---|---|
| concrete class | 18.9 | 1.0x |
| ABC | 84.1 | **4.4x** |
| `collections.abc.Iterable` | 87.3 | 4.6x |

An ABC `isinstance` is **4.4x** slower than a concrete one (4.2x on 3.14.6).
A concrete `isinstance` is a built-in C check that walks the object's type and MRO directly.
An ABC `isinstance` invokes `ABCMeta.__instancecheck__`, which applies the `__subclasshook__` and the registry logic, backed by a cache to avoid recomputing for known types, but even the cached path runs more code than the built-in.

The lesson positions ABCs correctly.
They are an **interface and design tool**: declare required methods, recognise structural conformers, document and enforce a protocol at boundaries.
They are **not a hot-path type test**.
Do not scatter `isinstance(x, SomeABC)` through inner loops, one check at a system boundary (validating input at an API edge) is fine and clarifying; the same check per element in a million-iteration loop is 4.4x of a cost you probably do not need.
Where you can, prefer plain **duck typing**, just call the method and let it fail if absent (EAFP), which is both faster and more Pythonic than a defensive `isinstance` guard.
The ABC's job is to make the *contract* explicit and checkable when you need to check it, not to gate every operation.
This is the recurring Deep C shape once more: the expressive mechanism (a metaclass-customised `isinstance`) costs more than the plain one, so spend it at the boundary where it buys clarity, not in the loop where it buys nothing.

---

## 35.4 Edges and failure modes

**Every abstract method must be overridden to instantiate.** §35.1.
Missing one keeps the subclass abstract (a `TypeError` at construction). The message names the unimplemented method(s).

**`@abstractmethod` must be the innermost decorator.**
Combining with `@property`/`@classmethod`/`@staticmethod` requires `@abstractmethod` closest to the function: `@property` then `@abstractmethod`. Wrong order silently loses the abstractness. (The old `abc.abstractproperty` and friends are deprecated in favour of stacking.)

**`register()` gives no methods and does no checking.** §35.2.
A virtual subclass inherits nothing and is *not* verified to actually implement the interface, `register()` is a promise you make, not one Python checks. If the registered class lacks the methods, calls fail at runtime as usual.

**`__subclasshook__` should return `NotImplemented` to defer, not `False`.**
Returning `NotImplemented` lets normal subclass checking (real inheritance, registrations) proceed; returning `False` *vetoes* them. Return `True` to accept structurally, `NotImplemented` to fall through, and reserve `False` for a deliberate veto.

**ABC `isinstance` is ~4.4x slower.** §35.3.
Fine at boundaries, wrong in hot loops. Prefer duck typing (EAFP) where you can.

**Structural checks (`__subclasshook__`) only see method *presence*, not signatures.**
`collections.abc.Iterable` accepts anything with `__iter__`, regardless of whether it behaves correctly. ABCs check the shape, not the semantics; a malformed implementation still passes `isinstance`.

**Multiple ABCs and MRO.**
Combining several ABCs (a class implementing `Sized` and `Iterable` and `Container`) is normal, but the abstract methods accumulate and the MRO (Chapter 34) applies. `collections.abc` provides rich combined ABCs (`Sequence`, `Mapping`) that pull in several, with mixin methods derived from the abstract ones.

**`abc.ABC` versus `metaclass=ABCMeta`.**
`class C(abc.ABC)` is sugar for `class C(metaclass=ABCMeta)`. If you already need a *different* metaclass, you must combine it with `ABCMeta` (a metaclass conflict otherwise), one of the few places ordinary code meets Chapter 31's metaclass rules.

---

## 35.5 Connections

**Backward.**
`ABCMeta` is a metaclass (Chapter 31): the `@abstractmethod` enforcement and the `__instancecheck__` override are what a metaclass can do, made concrete. `__subclasshook__`'s structural check walks the MRO (Chapter 34). The `collections.abc` protocols formalise the special methods of Deep A (`__len__`, `__eq__`) and Deep F (`__iter__`, `__next__`) into named, checkable interfaces.

**Forward.**
`typing.Protocol` (**Deep I**) is the static-typing counterpart: structural typing checked by a type checker at "compile" time rather than by `isinstance` at runtime, often the better tool when you want the interface documented and checked without the runtime cost of §35.3. `collections.abc`'s full hierarchy (`Sequence`, `Mapping`, `Set`) and its mixin methods are a **Deep Q** topic. `@dataclass` and `enum` (other `ABCMeta`/metaclass-adjacent class tools) are the rest of Deep C.

**Across books.**
ABCs are how **Book I** defines the contracts its pluggable components must satisfy: a `DataSource`, a `Strategy`, an `ExecutionVenue` declared as an ABC with abstract methods, so a new implementation that forgets a required method fails at construction, in a test, rather than at 09:30 in production. The order-book system defines its strategy and feed-handler interfaces as ABCs for exactly this early enforcement, uses `register()` to adopt third-party adapters into those interfaces without modifying them, and keeps the `isinstance` checks at module boundaries (not in the matching loop), honouring the §35.3 cost.

---

## 35.6 Exercises

**1. Enforce an interface.** Reproduce §35.1: an ABC with two abstract methods, a complete subclass, and an incomplete one. Confirm the ABC and the incomplete subclass both refuse to instantiate, and the complete one works. Explain why this beats duck typing for catching a missing method.

**2. Retrofit with `register()`.** Define an ABC and a class that does not inherit it but implements its methods. Register it and confirm `isinstance` passes while the ABC is not in the MRO. Then show that `register()` does *not* verify the methods exist (register a class missing them and watch the runtime failure).

**3. Structural hook.** Write an ABC whose `__subclasshook__` accepts any class with `read` and `write`. Confirm an unrelated class with those methods passes `isinstance`. Explain why the hook returns `NotImplemented` rather than `False` for non-matches.

**4. Measure and place.** Reproduce §35.3. Then write a function that validates its argument with an ABC `isinstance` once at entry versus one that checks per loop iteration, and measure the difference on a large input. State where ABC checks belong.

**5. The design question.** Python has both ABCs (runtime, nominal-or-structural) and `Protocol` (static, structural). Argue when each is the right tool, using the §35.1 construction-time enforcement, the §35.3 runtime cost, and the fact that `Protocol` needs no runtime check. Would a language be better with only one? Defend your answer.

---

## 35.7 Summary and cross-references

- An **abstract base class** (`abc.ABC`, metaclass `ABCMeta`) declares an interface with **`@abstractmethod`**; a class with any unimplemented abstract method **cannot be instantiated** (`TypeError` at construction), moving "you forgot a method" from a deep `AttributeError` to an early, local error.
- **Virtual subclasses** let a class be a subtype **without inheriting**: `register(Cls)` vouches for it (not in the MRO), and **`__subclasshook__`** recognises it **structurally** (by method presence). This is how `collections.abc` makes `isinstance([], Sized)` true.
- ABCs are a **hybrid** of nominal interfaces (enforcement) and duck typing (structural recognition), Python taking the useful half of each.
- **Measured:** an ABC `isinstance` is **4.4x** slower than a concrete one (84.1 vs 18.9 ns) because it runs `ABCMeta.__instancecheck__`. Use ABCs at boundaries as an interface tool; prefer duck typing (EAFP) in hot paths.
- **Edges:** all abstract methods must be overridden; `@abstractmethod` innermost when stacking; `register()` does not verify; `__subclasshook__` returns `NotImplemented` to defer; structural checks see presence, not semantics.

**Cross-references.** `ABCMeta` as a metaclass → Chapter 31. Structural checks over the MRO → Chapter 34. Special methods formalised as protocols → Deep A, Deep F. `typing.Protocol` (static structural typing) → Deep I. `collections.abc` full hierarchy → Deep Q. `@dataclass`, `enum` → Deep C.
