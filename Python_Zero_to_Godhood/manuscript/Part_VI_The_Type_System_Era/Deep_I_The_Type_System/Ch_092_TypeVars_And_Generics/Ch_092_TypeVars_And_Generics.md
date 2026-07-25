# Chapter 92: TypeVars and Generics

A helper `first(items)` returns the first element of a list, and you annotate it `def first(items: list) ->
Any` because "it can return anything". That annotation *throws away* the one thing the caller most needs: the
type checker no longer knows that `first([1, 2, 3])` is an `int`, so every downstream use of the result is
untyped, no autocompletion, no error if you treat it as a string. A **TypeVar** fixes this by *linking* the
input and output types: `def first[T](items: list[T]) -> T` tells the checker "the return type *equals* the
element type", so `first([1, 2, 3])` is known to be an `int` and `first(["a"])` a `str`. Generics *preserve*
precise types through a function where `Any` *erases* them, and they do it at **zero runtime cost** (the TypeVar
is erased, Chapter 86): calling a generic function costs exactly what calling a plain one does. The only runtime
cost of generics is *subscripting* one, `list[int]` builds a `GenericAlias` object, **14x** a bare `list`
reference, which matters only if you evaluate parameterized generics in a hot loop.

This chapter continues **Deep I** with TypeVars and generics: how they preserve type relationships that `Any`
loses, the PEP 695 syntax, and the two runtime facts, free to call, costed to subscript. It is what makes typed
*reusable* code possible without sacrificing precision.

## Section index

- **92.1** Preserving the type relationship
- **92.2** Generic to call, `GenericAlias` to subscript
- **92.3** Measurement: erased calls, allocating subscripts
- **92.4** Edges and failure modes
- **92.5** Connections
- **92.6** Exercises
- **92.7** Summary and cross-references

Listings live under `code/ch092/` and are re-executed by `make verify` on both interpreters.

---

## 92.1 Preserving the type relationship

```python
# code/ch092/l01_generics.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a generic function returns the element type (statically) ---
  first([1, 2, 3]) : 1   (checker knows: int)
  first(['a', 'b']): a   (checker knows: str)
  first_any([1,2]) : 1   (checker only knows: Any, link lost)
--- PEP 695 records the type parameters ---
  first.__type_params__ : (T,)
--- generics are erased: no runtime type check ---
  first([1, 'mixed']) : 1   (runtime does not check T)
--- subscripting a generic builds a GenericAlias (a runtime object) ---
  type(list[int])       : GenericAlias
  list[int].__origin__  : list
  list[int].__args__    : ('int',)
--- the rule ---
  a TypeVar preserves precise types the checker needs (vs Any, which loses them)
  generics are free at runtime; only subscripting (list[int]) allocates
```

The generic `first[T]` and the `Any`-returning `first_any` produce the *same runtime value* (`1`), but they give
the checker *different information*. For `first`, the checker knows the return type is `T`, *bound to the
element type of the argument*, so `first([1, 2, 3])` is an `int` and `first(["a"])` a `str`: the precise type
flows through. For `first_any`, the return is `Any`, so the checker knows *nothing* about the result, the type
link is severed, and downstream code is untyped. A TypeVar is how a *reusable* function stays *precisely typed*
for each call.

`first.__type_params__` is `(T,)`: PEP 695 (3.12+) syntax `def first[T](...)` declares the type parameter
inline (no separate `T = TypeVar("T")`), and records it on the function. And, as the third block shows, the
generic is *erased* at runtime, `first([1, "mixed"])` runs fine despite `T` being ambiguous; the runtime does
*not* check that the list is homogeneous. Precision is a *static* guarantee.

---

## 92.2 Generic to call, `GenericAlias` to subscript

There are two distinct runtime interactions with generics, and only one costs.

*Calling* a generic function is *free*: the TypeVar is erased, so `first` is an ordinary function with no
type-checking machinery, its call cost is identical to a non-generic function's (§92.3). You can annotate every
reusable helper generically with no runtime penalty.

*Subscripting* a generic, writing `list[int]`, `dict[str, User]`, `Sequence[T]`, is a *runtime operation* that
builds a **`types.GenericAlias`** object (the last block: `type(list[int])` is `GenericAlias`, with `__origin__`
= `list` and `__args__` = `(int,)`). That object records the parameterization for introspection and is what
annotations *are* when evaluated. Building it allocates, so `list[int]` costs several times a bare `list`
reference (§92.3), and it is *not cached* (each `list[int]` builds a fresh alias).

The consequence for practice: **annotate generically without hesitation, and avoid *evaluating* parameterized
generics in hot code.** In *annotations*, the subscription cost is usually irrelevant: with deferred annotations
(Chapter 12) the annotation `list[int]` is a *string*, never evaluated at runtime, and even without deferral it
is evaluated once at definition. The cost bites only if you *construct* a parameterized generic *at runtime in a
loop*, e.g. `isinstance`-style checks (which do not even work on parameterized generics, §92.4) or dynamically
building types per iteration. For those, hoist the `list[int]` out of the loop (build it once) or use the bare
type. The generic *type system* is free; only the runtime *object* that represents a parameterization allocates.

---

## 92.3 Measurement: erased calls, allocating subscripts

**Methodology.** `code/ch092/bench_generics.py`. Calling a generic vs a plain (`Any`) function, and referencing a
bare `list` vs subscripting `list[int]`. `min` per call; ratios relative to the bare `list` reference. CPython
3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| operation | min per call | ratio |
|---|---|---|
| reference bare `list` | **3.5 ns** | 1.00x |
| call plain (`Any`) | **29.9 ns** | 8.47x |
| call generic `[T]` | **29.6 ns** | 8.38x |
| subscript `list[int]` | **50.0 ns** | **14.17x** |

The two function calls are *identical*, **29.9 ns** (plain) and **29.6 ns** (generic), confirming the TypeVar is
erased: a generic function has *no* runtime type-checking overhead, it is just a function. Subscripting
`list[int]` costs **50 ns**, **14x** a bare `list` reference, because it allocates a `GenericAlias`. So the
*static* precision a generic buys is free at call time, and the *only* runtime cost is materializing a
parameterized generic *object*.

The rule: **use generics freely for static precision; the runtime cost is zero for calls and paid only when you
subscript a generic at runtime.** Annotate reusable functions and classes with TypeVars so the checker preserves
types across them (where `Any` would lose them), there is no call-time penalty. Reserve concern for the
subscription cost only in the rare case of building `list[int]`/`dict[str, int]` inside a hot loop, where you
hoist the alias out or use the bare type. As with the rest of Deep I, the type-level machinery is erased and
free; only *runtime objects* (a `GenericAlias`, a resolved hint, an Enum member) cost, and generics' one such
object, the subscription, is easy to avoid where it would matter.

---

## 92.4 Edges and failure modes

**Annotating `Any` instead of a TypeVar.** §92.1. `Any` erases the type link the caller needs. Use a TypeVar to
preserve the input-output relationship in reusable code.

**`isinstance` with a parameterized generic.** `isinstance(x, list[int])` raises `TypeError`, you cannot runtime-
check a parameterization (the element type is erased). Check `isinstance(x, list)` and validate elements
separately.

**Subscripting generics in a hot loop.** §92.2. Each `list[int]` allocates a `GenericAlias`. Build it once
(hoist out of the loop) if you need it repeatedly at runtime; in annotations it is usually free (deferred).

**Unbound or over-general TypeVars.** A TypeVar used only once conveys nothing (it is just `Any` with extra
syntax); a TypeVar links *two or more* positions. Use `bound=`/constraints to restrict it (`T: (int, float)` or
`T: Number`) when the generic should not accept *everything*.

**Variance confusion.** A `list[Derived]` is *not* a `list[Base]` (mutable containers are invariant), while a
`Sequence[Derived]` *is* a `Sequence[Base]` (read-only, covariant). Mis-assuming variance causes checker errors
that look wrong; know that mutability drives variance (a later Deep I topic).

**Old vs new syntax.** PEP 695 `def f[T]()` (3.12+) and the classic `T = TypeVar("T"); def f(x: T)` coexist; the
new syntax scopes `T` to the function/class and needs no import. Do not mix a module-level `TypeVar` with the new
inline syntax for the same parameter.

---

## 92.5 Connections

**Backward.** Generics' zero runtime cost is Chapter 86's erasure (like `NewType`, `TypedDict`, `Literal`). The
`GenericAlias` is the subscription machinery behind the `list[int]` syntax of Chapter 16. PEP 695's lazy-scoped
type parameters connect to the scoping of Chapters 2-3. Deferred annotations (why subscription is usually free)
are Chapter 12.

**Forward.** Generic *classes*, variance (covariance/contravariance), bounded/constrained TypeVars, `ParamSpec`,
and `TypeVarTuple` are the rest of **Deep I**. The `collections.abc` generic protocols (`Sequence[T]`,
`Mapping[K, V]`) are Chapter 69 and Deep I. `get_type_hints` resolving generic annotations is Chapter 91.

**Across books.** Generics are how Book II writes *reusable typed infrastructure* for **Book III**. A **Book III**
pipeline's generic stages, a `Cache[K, V]`, a `Pipeline[In, Out]`, a `Result[T]`, preserve precise types across
composition so the checker verifies that a stage producing `list[Doc]` feeds one consuming `list[Doc]`, at zero
runtime cost. The §92.1 `Any`-loses-the-link failure is exactly what makes a large typed codebase drift into
untyped soup, which generics prevent, and **Deep U** relies on for typed pipeline composition.

---

## 92.6 Exercises

**1. Preserve vs lose the type.** Reproduce §92.1: write a generic `first[T]` and an `Any`-returning version, and
(with a checker) show the generic preserves the element type while `Any` loses it. Explain the type link.

**2. See the erasure.** Show a generic function accepts a heterogeneous list at runtime (no `T` check) and costs
the same as a non-generic one. Explain why generics are free to call.

**3. Measure the subscript.** Run §92.3's benchmark and confirm `list[int]` costs more than a bare `list`
reference. Explain the `GenericAlias` allocation and when it matters.

**4. Bound a TypeVar.** Write a generic function whose TypeVar is bounded (`T` bound to a base or constrained to
specific types) and show the checker rejects an out-of-bound argument. Explain when to bound.

**5. The design question.** Generics preserve static type precision at zero runtime cost by erasing the TypeVar.
Argue why this is the right design for a gradually-typed language. Your answer must use the §92.3 measurement, the
`Any`-loses-the-link problem, and Chapter 86's erasure.

---

## 92.7 Summary and cross-references

- A **TypeVar** links a function's input and output types (`def first[T](items: list[T]) -> T`), so the checker
  **preserves precise types** across the call where **`Any` loses** them. PEP 695 (3.12+) declares type
  parameters inline.
- **Generics are erased at runtime:** a generic function has **no runtime type check** and costs the same as a
  non-generic one.
- **Measured:** calling a generic == calling a plain function (29.6 vs 29.9 ns); the only runtime cost is
  **subscripting** a generic, `list[int]` builds a `GenericAlias`, **14x** a bare `list` reference.
- **Use generics freely for static precision** (zero call cost); avoid building parameterized generics in a hot
  loop. `isinstance` cannot check a parameterization; bound TypeVars that should not accept everything.

**Cross-references.** Erasure → Chapter 86; `NewType`/`TypedDict`/`Literal` → Chapters 87, 89, 90. `list[int]`
syntax → Chapter 16. Deferred annotations → Chapter 12. `get_type_hints` → Chapter 91. Variance, generic classes,
`ParamSpec` → the rest of Deep I. `collections.abc` generics → Chapter 69. The typed-pipeline seam → Deep U.
