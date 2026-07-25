# Chapter 94: `@overload`

Some functions return a type that *depends on* the argument type. A `parse` that turns an `int` into a `str`
and a `str` into an `int`; a `__getitem__` that returns a scalar for an integer index and a list for a slice; a
`get(key)` that returns the value type for a present key and `None` for a default. A single signature cannot
express this: `parse(x: int | str) -> int | str` says "takes either, returns either", *losing* the
correspondence between *which input* gives *which output*, so the checker cannot tell that `parse(42)` is a
`str`. `@overload` fixes it: you declare *several* signatures, one per case, and the checker picks the right
return type for each call. And it costs *nothing* at runtime, the `@overload` stubs are static *declarations*;
only the final, undecorated implementation exists and runs, so an overloaded function is a normal function
(measured at 1.01x a plain one).

This chapter continues **Deep I** with `@overload`: expressing input-dependent return types the checker
understands, the one-implementation runtime reality, and when overloading is (and is not) the right tool. It is
the static counterpart to runtime dispatch (`singledispatch`, Chapter 34).

## Section index

- **94.1** Many signatures, one implementation
- **94.2** When to overload
- **94.3** Measurement: overloads are free
- **94.4** Edges and failure modes
- **94.5** Connections
- **94.6** Exercises
- **94.7** Summary and cross-references

Listings live under `code/ch094/` and are re-executed by `make verify` on both interpreters.

---

## 94.1 Many signatures, one implementation

```python
# code/ch094/l01_overload.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- the return type depends on the argument type (per the checker) ---
  parse(42)  : '42'  (type str; checker: str)
  parse('7') : 7   (type int; checker: int)
--- at runtime there is ONE implementation; the stubs are declarations ---
  registered overloads : 2
  parse is the impl (callable) : True
--- a single union signature could not express the correspondence ---
  parse(x: int|str) -> int|str would lose which output goes with which input
--- the rule ---
  @overload: multiple static signatures when the return depends on the input
  one runtime implementation (the stubs vanish); zero runtime cost
```

`parse` has *two* `@overload` signatures, `parse(int) -> str` and `parse(str) -> int`, followed by *one* real
implementation. At runtime, `parse(42)` returns `'42'` and `parse('7')` returns `7`, and the *checker* knows the
return types precisely: `parse(42)` is a `str`, `parse('7')` is an `int`. A single `int | str -> int | str`
signature could not say that, it would report the return as `int | str` for *both* inputs, losing the input-
output link that overloading preserves.

The runtime reality: there is exactly *one* callable. The `@overload`-decorated stubs (with `...` bodies) are
*declarations* for the checker; the final `def parse(x):` *replaces* them, and `parse` refers to that
implementation. `typing.get_overloads(parse)` (3.11+) can retrieve the registered stubs (here, 2) for
introspection, but they are not on the call path, calling `parse` runs the *implementation*, which uses a plain
`isinstance` to do at runtime what the overloads describe at the type level.

---

## 94.2 When to overload

`@overload` is the right tool for one specific situation: **the return type (or valid argument combination)
depends on the input in a way a single signature cannot express.** The canonical cases:

- **Input-dependent return type:** `parse(int) -> str` / `parse(str) -> int`; `open(path) -> TextIO` /
  `open(path, "rb") -> BinaryIO`; `__getitem__(int) -> T` / `__getitem__(slice) -> list[T]`.
- **Argument-combination constraints:** signatures where certain parameters are valid *together* but not
  separately, expressible as distinct overloads but not one signature.
- **Precise `None` handling:** `get(key) -> V` / `get(key, default: D) -> V | D`, where the return depends on
  whether a default was passed.

It is *not* a tool for **runtime dispatch**. `@overload` does nothing at runtime, the single implementation must
handle all cases itself (with `isinstance`, or by delegating). If you want the *runtime* to pick a different
*implementation* based on the argument type, that is `functools.singledispatch` (Chapter 34), a different
mechanism with real runtime dispatch. And it is not needed when a single signature *suffices*: if the return is
genuinely `int | str` regardless of input (no correspondence to preserve), just write the union, overloading
adds ceremony for no gain.

The rule: **overload when the return type varies with the input and you want the checker to track which output
goes with which input; otherwise use a single signature (or `singledispatch` for runtime dispatch).** The
implementation is always one function that handles every overloaded case, and the overloads are the *promise*
the checker enforces at each call site.

---

## 94.3 Measurement: overloads are free

**Methodology.** `code/ch094/bench_overload.py`. Calling an overloaded function versus an identical plain one.
`min` per call; ratio relative to the plain function. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| call a function | min per call | ratio |
|---|---|---|
| plain function | **44.6 ns** | 1.00x |
| overloaded function | **45.1 ns** | **1.01x** |

The two are *identical* (within noise): **44.6 ns** plain, **45.1 ns** overloaded. The `@overload` stubs never
run, only the final implementation does, so an overloaded function is a *normal* function at runtime with *no*
dispatch overhead. The overloads add zero runtime cost; they exist entirely for the static checker.

The rule: **overload freely for static precision, it is free at runtime.** Because the stubs are erased (Chapter
86) and only the one implementation runs, there is no performance reason to avoid overloading a function whose
return type depends on its input. The cost, if any, is *authoring*: you maintain the overload signatures *and* an
implementation that correctly handles every case, and a mismatch (an overload that promises a return the
implementation does not deliver) is a bug the checker may not fully catch. But at *runtime*, an overloaded
function is just a function. This is the last of Deep I's erasure lessons: the static machinery, overloads,
generics, protocols, literals, is erased and free; you spend runtime only on actual objects (a `GenericAlias`, a
union, an Enum member), and `@overload` produces none, its precision is purely a compile-time gift.

---

## 94.4 Edges and failure modes

**Using `@overload` for runtime dispatch.** §94.2. It does nothing at runtime; the single implementation handles
all cases. For runtime type-based dispatch, use `functools.singledispatch` (Chapter 34).

**An implementation that violates an overload.** The checker verifies *call sites* against the overloads, but the
*implementation* body is checked more loosely; an implementation that returns the wrong type for an overloaded
case is a real bug the tooling may miss. Keep the implementation consistent with every overload.

**Overloads that overlap or are ordered wrong.** The checker matches overloads *top to bottom*; overlapping or
mis-ordered signatures (a more general one before a more specific one) can resolve to the wrong return type. Order
from most specific to most general, and avoid ambiguous overlaps.

**Missing the implementation, or decorating it.** The final, *undecorated* `def` is the implementation; forgetting
it (only stubs) leaves the function undefined at runtime, and decorating the implementation with `@overload` too
makes *it* a stub. Exactly one undecorated implementation must follow the stubs.

**Overloading when a single signature works.** If the return is `int | str` regardless of input, a single
signature is clearer; overloading adds stubs for no precision gain. Reserve it for genuine input-output
correspondence.

**Runtime introspection of overloads.** `get_overloads` (3.11+) returns the stubs, but not on older versions;
frameworks relying on it must guard for availability. The stubs' `...` bodies do nothing useful if called
directly.

---

## 94.5 Connections

**Backward.** The zero runtime cost is Chapter 86's erasure. The runtime-dispatch alternative, `singledispatch`,
is Chapter 34. The single-implementation `isinstance` branching is Chapter 4/6. The signatures the overloads
describe connect to `inspect.signature` (Chapter 49).

**Forward.** `@overload` interacts with generics and `ParamSpec` for precise higher-order typing (the rest of
**Deep I**). Stub files (`.pyi`) full of overloads for untyped/C libraries are a Deep I tooling topic. Protocol
methods can be overloaded too.

**Across books.** `@overload` is how Book II gives precise types to the polymorphic APIs it exposes to
**Book III**. A **Book III** client whose `fetch(id) -> Doc` but `fetch(id, stream=True) -> Iterator[Chunk]`
returns different types by argument uses overloads, so callers get the exact return type per call, at zero
runtime cost, while a single implementation handles both. The §94.1 input-output correspondence is exactly what
keeps a flexible API *precisely* typed rather than collapsing to a lossy union, which **Deep U** relies on for
typed client interfaces.

---

## 94.6 Exercises

**1. Preserve the correspondence.** Reproduce §94.1: write an overloaded function whose return type depends on the
argument type, and (with a checker) show `f(int)` and `f(str)` get different return types, where a single union
signature would not. Explain the correspondence.

**2. See the single implementation.** Show `get_overloads` returns the stubs and that the runtime function is the
implementation. Explain why calling the function runs the implementation, not a stub.

**3. Measure the cost.** Run §94.3's benchmark and confirm an overloaded function costs the same as a plain one.
Explain why the overloads add no runtime overhead.

**4. Overload vs singledispatch.** Take a function that should dispatch differently at runtime by type and
implement it with `singledispatch`; contrast with `@overload` (which does not dispatch). Explain the difference.

**5. The design question.** `@overload` expresses input-dependent return types statically at zero runtime cost.
Argue when it is the right tool versus a single signature or `singledispatch`. Your answer must use the §94.3
measurement, the correspondence a union loses, and the static-vs-runtime dispatch distinction.

---

## 94.7 Summary and cross-references

- **`@overload`** declares **multiple static signatures** for one function, so the checker can give a return type
  that **depends on the argument type** (which a single `int | str -> int | str` signature cannot express).
- At runtime there is **one implementation** (the final, undecorated `def`); the `@overload` stubs are
  declarations that never run. `get_overloads` (3.11+) can introspect them.
- **Measured:** an overloaded function costs the **same** as a plain one (45.1 vs 44.6 ns), the overloads are
  erased and add no runtime dispatch. Overload freely for static precision.
- **Overload when the return varies with the input;** use a single signature when it does not, and
  **`singledispatch`** (Chapter 34) for actual *runtime* dispatch. Provide exactly one undecorated implementation;
  order overloads specific-to-general.

**Cross-references.** Erasure → Chapter 86. Runtime dispatch (`singledispatch`) → Chapter 34. `isinstance`/
branching → Chapters 4, 6. `inspect.signature` → Chapter 49. Generics/`ParamSpec`, stub files → the rest of Deep
I. The typed-client seam → Deep U.
