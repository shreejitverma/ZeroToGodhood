# Chapter 33: `property`, `classmethod`, `staticmethod`

Chapter 32 built the descriptor protocol and promised that `property`, `classmethod`, and `staticmethod`, three decorators you have used since your first week of Python, are nothing more than descriptors applied to functions.
This chapter cashes that in.
Each of the three is a descriptor whose `__get__` does something specific, and once you see *what* each `__get__` does, the differences between them stop being three memorised rules and become one idea seen from three angles: a descriptor decides what an attribute access returns, and these three decide it differently.

`property` returns a computed value (and can validate on assignment).
`classmethod` binds the *class* instead of the instance, which is exactly what an alternative constructor needs.
`staticmethod` binds *nothing*, giving a plain function that happens to live in a class namespace.
That is the whole chapter, plus one measurement that decides between `property` and its caching cousin `cached_property`, which turns out to be a **100x-plus** difference when the getter is expensive.

**This is the canonical home for the three built-in method descriptors.**
It builds directly on Chapter 32 (the descriptor protocol they implement), Chapter 25 (`classmethod` alternative constructors complement `__new__`), and Chapter 20 (all method dispatch is on the type).

## Section index

- **33.1** `property`: computed and validated attributes
- **33.2** `classmethod` and `staticmethod`: two more bindings
- **33.3** Measurement: `property` versus `cached_property`
- **33.4** Edges and failure modes
- **33.5** Connections
- **33.6** Exercises
- **33.7** Summary and cross-references

Listings live under `code/ch114/` and are re-executed by `make verify` on both verification interpreters.

---

## 33.1 `property`: computed and validated attributes

```python
# code/ch114/l01_property.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- read via getter, both real and computed ---
  t.celsius    : 20
  t.fahrenheit : 68.0   (computed from celsius)
--- assign via setter; the computed one follows ---
  after t.celsius = 25, t.fahrenheit : 77.0
--- the setter validates ---
  t.celsius = -300 -> ValueError : below absolute zero
--- a getter-only property is READ-ONLY ---
  t.fahrenheit = 100 -> AttributeError (no setter): True
--- property is a DATA descriptor (has __set__) ---
  hasattr(Temperature.__dict__['celsius'], '__set__') : True
--- the rule ---
  @property turns methods into attributes: getter/setter/deleter, with
  validation in the setter; getter-only is read-only
```

`property` packages the descriptor protocol for the most common customization: make a method *look like an attribute*.
`t.celsius` is attribute syntax, no parentheses, but it runs the getter method; `t.celsius = 25` runs the setter.
The three parts are the getter (`@property`), the setter (`@celsius.setter`), and the deleter (`@celsius.deleter`), and each is optional.

Two capabilities follow, both visible.
**Validation** lives in the setter: `celsius`'s setter rejects values below absolute zero, so `t.celsius = -300` raises `ValueError` at the point of assignment, no separate `validate()` call, no way to bypass it with a plain assignment.
**Computed, read-only attributes** need only a getter: `fahrenheit` derives from `celsius` and has no setter, so it is always current (`t.celsius = 25` immediately changes `t.fahrenheit`) and assigning to it raises `AttributeError` ("no setter").
That read-only enforcement is a direct consequence of Chapter 32: `property` is a **data descriptor** (it defines `__set__`, the output confirms it), so it outranks the instance `__dict__` and a getter-only property's `__set__` raises rather than allowing a shadowing instance attribute.

The design payoff is the one from Chapter 32, now concrete: because `t.celsius` is the same syntax whether `celsius` is a plain attribute or a property, you expose a plain attribute first and *upgrade* it to a property, adding validation or computation, without touching a single caller.
`property` is the tool you reach for the day a plain attribute needs to become smart, and not a day before.

---

## 33.2 `classmethod` and `staticmethod`: two more bindings

```python
# code/ch114/l02_classmethod_staticmethod.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- classmethod: alternative constructor, receives cls ---
  Date.from_string('2026-07-25').iso() : 2026-07-25
--- classmethod called via instance still gets the class ---
  d.from_string('1999-12-31').iso()    : 1999-12-31
--- staticmethod: no binding, plain function in the namespace ---
  Date.is_valid_year(2026) : True
  Date.is_valid_year(0)    : False
--- all three are descriptors, binding differently ---
  type(Date.__dict__['from_string'])  : classmethod
  type(Date.__dict__['is_valid_year']): staticmethod
  type(Date.from_string) (bound)      : method   (cls bound)
  type(Date.is_valid_year)            : function   (plain function)
--- the rule ---
  classmethod binds cls (use for alternative constructors);
  staticmethod binds nothing (a namespaced plain function)
```

The three method kinds differ only in what their `__get__` binds:

- A **normal method**'s `__get__` binds the **instance** (`self`), Chapter 32.
- A **`classmethod`**'s `__get__` binds the **class** (`cls`). `Date.from_string` receives `Date` as `cls`, and, crucially, so does `d.from_string` (called on an instance, it *still* gets the class, not the instance). The output confirms `Date.from_string` is a bound `method` with the class bound in.
- A **`staticmethod`**'s `__get__` binds **nothing**: it returns the underlying plain function. `Date.is_valid_year` is a `function`, and calling it passes no implicit first argument.

The canonical use of `classmethod` is the **alternative constructor**, and it is why `cls` (not the hardcoded class) matters.
`Date.from_string` builds a `Date` by calling `cls(...)`, and because it uses `cls` rather than `Date`, a subclass `SubDate.from_string(...)` builds a `SubDate`, the constructor is inherited correctly.
This complements `__new__`/`__init__` (Chapter 25): where those customize the *primary* construction path, a `classmethod` provides *named additional* ones (`Date.from_string`, `Date.today`, `dict.fromkeys`), each returning `cls(...)`.

`staticmethod` is the weakest of the three and the least needed: it is a plain function you have chosen to namespace inside a class because it is logically related, `Date.is_valid_year` needs neither the instance nor the class.
Often a module-level function is clearer; `staticmethod` earns its place mainly when the function is tightly coupled to the class's concept and you want it found on the class (including for subclass overriding).
The rule: **`classmethod` when you need the class (alternative constructors, class-level registries); `staticmethod` when you need neither self nor cls; a normal method otherwise.**

---

## 33.3 Measurement: `property` versus `cached_property`

A `property` runs its getter on *every* access (Chapter 32's 1.7x). When the getter is expensive and the value does not change, that is pure waste, and `functools.cached_property` is the fix.

**Methodology.** `code/ch114/bench_cached_property.py`.
Repeated reads of a computed attribute whose getter sums a 1,000-element list: a plain `property` versus `functools.cached_property`.
`min` of 5 runs, 1,000,000 reads.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| repeated read of an expensive getter | ns/read | vs property |
|---|---|---|
| `property` (recompute) | 2493 | 1.0x |
| `cached_property` (compute once) | 19 | **130x faster** |

`cached_property` is **130x** faster here (96x on 3.14.6) for repeated reads, and the margin scales with the getter's cost, a heavier computation widens it, a trivial one narrows it toward the plain-attribute baseline.
The mechanism is a lovely application of Chapter 32's data/non-data distinction.
`cached_property` is a **non-data** descriptor: on first access its `__get__` runs the getter *once* and stores the result in the instance's `__dict__` under the same name.
Because it is non-data, the instance `__dict__` now **outranks** it (Chapter 32's precedence), so every subsequent access finds the stored value and never calls the descriptor again, later reads are plain attribute fetches.
The caching *is* the shadowing rule, used on purpose.

The decision between them is about *staleness*, not just speed.
Use `cached_property` for an attribute that is **expensive, pure, and read-mostly**, computed from data that does not change after construction (a parsed representation, an aggregate, a derived index).
Use a plain `property` when the underlying value **can change** (a cache would go stale and return wrong answers) or when the getter is cheap enough that caching is not worth the stored bytes.
And note the constraint that ties back to Chapter 22: because `cached_property` stores into the instance `__dict__`, a class with `__slots__` and no `__dict__` cannot use it, the memory optimization and this caching optimization are mutually exclusive unless you add `"__dict__"` to the slots.

---

## 33.4 Edges and failure modes

**A getter-only property is read-only.** §33.1.
Assignment raises `AttributeError`. Add a `@name.setter` to allow writes. This read-only behaviour depends on `property` being a data descriptor (Chapter 32).

**Validation belongs in the setter, and cannot be bypassed.** §33.1.
Because the property intercepts assignment, `obj.x = bad` triggers the setter's check. Do not also keep a public plain attribute for the same value, or the validation is bypassable.

**`classmethod` uses `cls`, not the hardcoded class.** §33.2.
Writing `return Date(...)` instead of `return cls(...)` breaks inheritance: `SubDate.from_string` would return a `Date`. Always build with `cls`.

**`property` on a computed value recomputes every read.** §33.3.
For an expensive, unchanging value, use `cached_property`. For a changing value, keep `property` (a cache would be stale).

**`cached_property` needs an instance `__dict__` and is not thread-safe on first access.**
It fails on `__slots__` classes without `"__dict__"`. And two threads racing the first access can both compute the value (the last write wins); this is fine for pure functions but not for getters with side effects. Later reads are lock-free.

**`staticmethod` is often a module function in disguise.** §33.2.
If it does not use the class at all and is not meant for subclass overriding, a module-level function is usually clearer. Reserve `staticmethod` for functions genuinely coupled to the class.

**Stacking decorators has an order.**
`@classmethod` over `@property` did not work historically and was deprecated in 3.11 (removed later); to make a class-level computed attribute, use a metaclass property or a `classmethod` returning the value. Order matters: `@property` must be the innermost (closest to the function) for setters/getters to chain.

**A property's getter that raises masks the attribute.**
If the getter raises `AttributeError`, Python treats the attribute as missing and may fall through to `__getattr__` (Chapter 21), turning a bug in the getter into a confusing "no such attribute". Raise a different exception type from getters when the cause is not a genuine missing attribute.

---

## 33.5 Connections

**Backward.**
All three are the descriptor protocol of Chapter 32: `property` a data descriptor, `classmethod`/`staticmethod`/methods non-data descriptors differing in what `__get__` binds. `classmethod` alternative constructors complement `__new__`/`__init__` (Chapter 25). Method dispatch on the type is Chapter 20. `cached_property`'s caching *is* the non-data-descriptor shadowing of Chapter 32 and interacts with `__slots__` (Chapter 22).

**Forward.**
The C3 MRO and `super()` (how inherited methods and `classmethod`s resolve across a hierarchy) are later in Deep C. `@dataclass`, which generates `__init__`/`__repr__`/`__eq__` and can make frozen (read-only) fields, is a Deep C ergonomics topic and often replaces hand-written properties for simple validated records. How the interpreter specializes `LOAD_METHOD` and property access is **Deep H**.

**Across books.**
These three are everyday tools in **Book I**: `classmethod` factories parse domain objects from wire formats and database rows (`Order.from_message`, `Bar.from_dict`), `property` exposes validated and derived fields (a position's `market_value` computed from quantity and price), and `cached_property` memoizes expensive derived state (a parsed schema, a compiled matcher) that is built once per object. The order-book system uses `classmethod` constructors for its message types, read-only computed `property` for derived book metrics (spread, mid), and `cached_property` for per-symbol precomputed tables, choosing `property` over `cached_property` exactly where the underlying book changes, the §33.3 staleness rule applied where correctness depends on it.

---

## 33.6 Exercises

**1. Build a validated property.** Reproduce §33.1: a class with a validated setter and a computed read-only property. Confirm the validation fires, the computed value tracks its source, and the read-only one rejects assignment. Explain why read-only works, using Chapter 32's data-descriptor precedence.

**2. Alternative constructors.** Give a class three `classmethod` constructors (`from_string`, `from_dict`, `today`-style). Subclass it and confirm the constructors return *subclass* instances. Show what breaks if you hardcode the class name instead of `cls`.

**3. Static or module function?** Write a `staticmethod` and argue whether it should instead be a module-level function. Give one case where `staticmethod` is the better choice (hint: subclass overriding) and one where the module function is.

**4. Measure the cache.** Reproduce §33.3. Then vary the getter's cost (sum 10, 1,000, 100,000 elements) and show how the `cached_property` advantage scales. Then construct a case where `cached_property` returns a *stale* wrong answer, and explain when `property` is mandatory.

**5. The design question.** Python provides `property`, `classmethod`, `staticmethod`, and `cached_property` as four decorators, all descriptors. Argue why building them on one protocol (Chapter 32) is better than four bespoke features, and identify the one subtlety the unification imposes (the §33.4 `cached_property` + `__slots__` conflict, or the decorator-stacking order). Would you have made `staticmethod` a language keyword instead? Defend your answer.

---

## 33.7 Summary and cross-references

- All three are **descriptors** (Chapter 32) differing in what `__get__` binds. **`property`** (a *data* descriptor) turns methods into attributes: getter/setter/deleter, with **validation in the setter** and **read-only** when getter-only.
- **`classmethod`** binds the **class** (`cls`), the tool for **alternative constructors** (`return cls(...)`, inheritance-correct). **`staticmethod`** binds **nothing**, a plain function namespaced in the class.
- **Measured:** `cached_property` is **130x** faster than a `property` for repeated reads of an expensive getter (19 vs 2493 ns), because it computes once and stores in the instance `__dict__`, then the non-data descriptor is shadowed by that value. The margin scales with getter cost.
- **Choose by staleness:** `cached_property` for expensive, pure, read-mostly values; `property` when the value can change (a cache would be stale). `cached_property` needs an instance `__dict__` (not `__slots__`) and is not thread-safe on first compute.
- **Edges:** use `cls` not the class name in `classmethod`; keep no bypassing plain attribute alongside a validated property; a getter raising `AttributeError` masks the attribute.

**Cross-references.** The descriptor protocol they implement → Chapter 32. Alternative constructors vs `__new__`/`__init__` → Chapter 25. `cached_property` + `__slots__` → Chapter 22. Method dispatch on the type → Chapter 20. MRO/`super()`, `@dataclass` → Deep C. Method/property specialization → Deep H.
