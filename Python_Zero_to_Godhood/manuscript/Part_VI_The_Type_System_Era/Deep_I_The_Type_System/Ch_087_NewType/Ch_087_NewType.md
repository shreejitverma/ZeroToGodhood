# Chapter 87: `NewType`

A payments bug ships: a function `refund(user_id, order_id)` is called with the arguments swapped,
`refund(order_id, user_id)`, and nothing complains, because both are `int`. The values have the same underlying
type, so the language, and every reviewer, sees two interchangeable integers. `NewType` is the tool that makes
them *not* interchangeable, statically, at *zero runtime cost*. `UserId = NewType("UserId", int)` creates a type
that a static checker treats as distinct from `int` (and from `OrderId`), so passing an `OrderId` where a
`UserId` is expected is flagged *before the program runs*, while at runtime a `UserId` simply *is* an `int`:
`NewType` is essentially the identity function, `UserId(42)` returns the integer `42` unchanged, with no wrapper
object and no memory overhead. Measured, making a `UserId` allocates nothing and costs about a third of a real
wrapper class (20 ns versus 52 ns), because the wrapper allocates an instance per value and `NewType` does not.

This chapter continues **Deep I** with `NewType`, the purest illustration of Chapter 86's erasure exploited
*deliberately*: a type distinction that exists *only* for the static checker and is *free* at runtime. It is how
you get type safety against confusing same-underlying-type values without paying for a wrapper.

## Section index

- **87.1** A distinct type that is the base type at runtime
- **87.2** `NewType` vs a wrapper class
- **87.3** Measurement: near-free vs a real object
- **87.4** Edges and failure modes
- **87.5** Connections
- **87.6** Exercises
- **87.7** Summary and cross-references

Listings live under `code/ch087/` and are re-executed by `make verify` on both interpreters.

---

## 87.1 A distinct type that is the base type at runtime

```python
# code/ch087/l01_newtype.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- at runtime, a UserId IS just an int ---
  UserId(42)            : 42
  type(UserId(42))      : int
  isinstance(uid, int)  : True
  uid == 42             : True
  no wrapper: same object as the int : True
--- the distinction is STATIC only ---
  UserId(42) == OrderId(42) at runtime : True  (both are int 42)
  but a static checker rejects passing an OrderId where a UserId is wanted
  (mypy/pyright flag it; the runtime does not)
--- the rule ---
  NewType: static distinctness for same-underlying-type values
           (UserId vs OrderId, both int), at zero runtime cost
  a wrapper class: runtime distinctness + methods/validation, but costs
```

`UserId(42)` produces the integer `42`: its `type` is `int`, `isinstance(uid, int)` is `True`, it equals `42`,
and it is not wrapped in anything, `NewType`'s "constructor" returns its argument unchanged. So at runtime a
`UserId` is *indistinguishable* from an `int`; there is no per-value object, no attribute to unwrap, no cost to
carry it around. It behaves exactly like the `int` it is.

The distinction is *static only*. `UserId(42) == OrderId(42)` is `True` at runtime (both are the integer `42`),
but a *static checker* treats `UserId` and `OrderId` as *different types*: it will flag `refund(order_id,
user_id)` (arguments swapped) as a type error, and reject assigning a plain `int` to a `UserId`-typed variable
without going through `UserId(...)`. The safety is entirely at authoring time; the runtime is oblivious, and free.

---

## 87.2 `NewType` vs a wrapper class

The alternative way to make `UserId` distinct is a real **wrapper class**: `class UserId: def __init__(self,
value): self.value = value`. This gives *runtime* distinctness, `isinstance(uid, UserId)` is `True`,
`type(uid)` is `UserId`, and you cannot accidentally pass a plain `int`, and it gives a place for *behavior*
(methods, validation in `__init__`, a custom `__repr__`). But it *costs*: every value is a separate object with
its own allocation, and you must *unwrap* it (`uid.value`) to use the underlying integer, and wrap it everywhere
you create one.

`NewType` and the wrapper class occupy opposite corners of the same trade:

- **`NewType`**: **static** distinctness, **zero** runtime cost and memory (it *is* the base type), but **no
  runtime protection** (a plain `int` cast to `UserId` at a boundary is not caught at runtime) and **no
  behavior** (it is not a real class; you cannot add methods).
- **Wrapper class**: **runtime** distinctness and **behavior** (methods, validation, encapsulation), but a real
  **cost** (an object per value, §87.3) and **unwrapping** ceremony.

The rule: **use `NewType` to keep same-underlying-type values from being confused, `UserId` vs `OrderId` (both
`int`), a `Url` vs a plain `str`, `Cents` vs `Dollars` (both `int`), when you want static safety at no runtime
cost and need no behavior.** Use a **wrapper class** (or a `@dataclass`, Chapter 13) when you need *runtime*
distinctness (e.g. to `isinstance`-dispatch on it), *validation* (reject a negative id at construction), or
*methods*. `NewType` is the right default for "these are logically different ids that happen to share a
representation"; the class is for "this is a real domain object with behavior".

---

## 87.3 Measurement: near-free vs a real object

**Methodology.** `code/ch087/bench_newtype.py`. Constructing a `UserId` via `NewType`, via a wrapper class (with
`__slots__`), and a bare `int`. `min` per call; ratio relative to the bare `int`. CPython 3.13.5, Apple M3 Pro,
macOS 27.0, arm64.

| make a value | min per call | ratio |
|---|---|---|
| bare `int(42)` | **7.1 ns** | 1.00x |
| `UserId(42)` (`NewType`) | **20.2 ns** | 2.82x |
| `UserIdClass(42)` (wrapper) | **52.4 ns** | **7.34x** |

`NewType` costs **20 ns**, ~2.8x a bare `int` (it is one function call that returns its argument) and, crucially,
allocates **no new object**, a `UserId` *is* the `int`, so it carries *zero* memory overhead. The wrapper class
costs **52 ns**, **7.3x** the bare int and **~2.6x** the `NewType`, because it *allocates an instance* per value
(and runs `__init__`), and each instance occupies memory even with `__slots__` (far more without). So over a
million ids, `NewType` adds *nothing* to the memory footprint while a million wrapper objects is real memory.

The rule: **`NewType` gives distinctness essentially for free; reserve the wrapper's cost for when you need
runtime distinctness or behavior.** When the only goal is to stop two same-typed values from being confused, and
a *static* check suffices (it usually does, the confusion is a *programming* error a checker catches), `NewType`
is the right tool: no allocation, no memory, no unwrapping, and the checker enforces the distinction. Paying for
a wrapper object per value, and threading `.value` through the code, is warranted only when the type must be real
at runtime or carry methods. This is Chapter 86's lesson turned to advantage: because types are erased,
`NewType`'s distinction is free, and you spend on a real type only when the runtime genuinely needs it.

---

## 87.4 Edges and failure modes

**Expecting `NewType` to protect at runtime.** §87.1. A `UserId` is an `int` at runtime; nothing stops a plain
`int` (or an `OrderId`) being used as one at runtime, only the static checker distinguishes them. For a runtime
guarantee, use a wrapper class or validate.

**`NewType` cannot be subclassed or `isinstance`d.** `isinstance(x, UserId)` raises `TypeError` (it is not a real
class), and you cannot inherit from a `NewType`. It is only a static tag. Use a class if you need those.

**Casting untyped data to a `NewType` at a boundary.** `UserId(external_int)` tells the checker "trust me, this is
a UserId" without any runtime check, if the external value is wrong, the error surfaces later. Validate the value
*before* tagging it at a trust boundary (Chapter 86).

**Adding behavior.** You cannot add methods to a `NewType`. The moment you want `user_id.some_method()`, you need
a real class (or module-level functions taking the id).

**Over-wrapping trivial values.** Not every `int` needs a `NewType`. Reserve it for values that are *genuinely
confusable* and *semantically distinct* (ids of different entities, units); tagging every integer clutters the
code for no benefit.

**Forgetting the static checker.** Like all annotations (Chapter 86), a `NewType` does nothing without mypy/
pyright running. Without a checker, `UserId` and `OrderId` are just `int` and the swap bug returns. Run the
checker in CI.

---

## 87.5 Connections

**Backward.** `NewType`'s zero runtime cost *is* Chapter 86's erasure, exploited on purpose. The wrapper-class
alternative is the object model of Chapter 4 and `__slots__` of Chapter 4 (memory). `@dataclass` as a richer
wrapper is Chapter 13. Typing basics are Chapter 16.

**Forward.** `TypeVar`/generics, `Protocol`, `Literal`, `TypedDict`, and the rest of the static-typing toolkit are
the rest of **Deep I**. Validation libraries (`pydantic`) that make types real at runtime are a Deep I/Deep O
application. Units-of-measure and domain-modeling patterns build on `NewType` and wrappers.

**Across books.** `NewType` is how Book II keeps distinct ids and units straight in the code that feeds
**Book III**, without runtime overhead. A **Book III** system distinguishes a `DocumentId` from a `ChunkId` from
an `EmbeddingId` (all strings or ints) with `NewType`, so the static checker catches a mismatched id passed
between the retrieval and indexing stages, at zero cost to the hot path, while reserving real classes for domain
objects with behavior. The §87.1 swap bug (same-typed values confused) is exactly the class of error `NewType`
eliminates statically, which **Deep U** relies on at the many-id seams of a pipeline.

---

## 87.6 Exercises

**1. See the runtime identity.** Reproduce §87.1: show a `NewType` value is the base type at runtime (`type`,
`isinstance`, equality) and that two `NewType`s over the same base are runtime-equal. Explain where the
distinction lives.

**2. Catch a swap.** Write a function taking a `UserId` and an `OrderId` (both `NewType` over `int`), call it with
the arguments swapped, and run a static checker to see it flagged. Explain why the runtime does not catch it.

**3. Measure the cost.** Run §87.3's benchmark and confirm `NewType` is far cheaper than a wrapper class and
allocates no object. Explain the memory implication over many values.

**4. Choose the tool.** For several cases (distinguish two id types, a value needing validation, a type needing
methods, a units distinction), pick `NewType` or a class and justify each. Explain the static-vs-runtime axis.

**5. The design question.** `NewType` gives static distinctness at zero runtime cost by being the base type at
runtime. Argue when that is the right trade versus a real wrapper. Your answer must use the §87.3 cost/memory, the
lack of runtime protection, and Chapter 86's erasure.

---

## 87.7 Summary and cross-references

- **`NewType('UserId', int)`** creates a type a **static checker treats as distinct** (from `int` and other
  `NewType`s) while at **runtime it IS the base type**, `UserId(42)` returns the `int` `42` unchanged, no wrapper,
  no memory. It exploits erasure (Chapter 86) deliberately.
- **`NewType`** = static distinctness, zero runtime cost/memory, no runtime protection, no behavior. **Wrapper
  class** = runtime distinctness + methods/validation, at a real per-value cost.
- **Measured:** `UserId(42)` costs **20 ns** and allocates nothing; a wrapper class costs **52 ns** (2.6x) and an
  object per value. Static distinctness is essentially free.
- **Use `NewType`** to stop same-underlying-type values being confused (ids, units) when a static check suffices;
  use a **class** for runtime distinctness or behavior. Run a static checker, or `NewType` does nothing.

**Cross-references.** Type erasure → Chapter 86. Object model, `__slots__` → Chapter 4; `@dataclass` → Chapter 13.
Typing basics → Chapter 16. `TypeVar`/`Protocol`/`Literal`/`TypedDict` → the rest of Deep I. `pydantic` validation
→ Deep I, Deep O. The many-id pipeline seam → Deep U.
