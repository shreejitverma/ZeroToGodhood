# Chapter 16: Typing Protocols and Structural Subtyping (Python 3.8-3.10)

A codebase uses a runtime-checkable protocol to validate plugins: `if isinstance(plugin, Renderable):
register(plugin)`. A plugin ships with a `render` method, passes the check, gets registered, and
crashes in production, because its `render` takes two arguments and the framework calls it with none.
The `isinstance` returned `True` for a plugin that does not actually satisfy the protocol, and here is
why, run and measured:

```python
class BadRender:
    def render(self, a, b):        # the NAME exists; the signature is wrong
        return "..."
# isinstance(BadRender(), Renderable)  ->  True
```

`@runtime_checkable` checks that the attribute *names* exist. It does not, and cannot, check that their
*signatures* match. That gap is the sharp edge of the feature that turned Python's type hints from a
thin annotation layer into a real gradual type *system* over the 3.8-3.10 releases. The centerpiece is
**`Protocol`** (PEP 544): structural subtyping, static duck typing, a class satisfying an interface by
*shape* rather than by inheritance. Around it came a toolbox the modern ecosystem depends on: builtin
generics (`list[int]`, PEP 585), `X | Y` unions (PEP 604), `TypedDict`, `Literal`, and `Final`. This
chapter teaches these as the version features they are; the type system as a discipline, variance in
depth, `TypeIs`/`TypeGuard`, overloads, stubs, mypy versus pyright, is **Deep I**.

## Section index

- **16.1** Nominal versus structural subtyping; `Protocol` (PEP 544)
- **16.2** `@runtime_checkable` and its limits
- **16.3** The 3.8-3.10 typing toolbox
- **16.4** Variance: covariance, contravariance, invariance, and LSP
- **16.5** Type erasure and the gradual-typing boundary
- **16.6** Measurement: typing is erased, but not free
- **16.7** Edges and failure modes
- **16.8** Connections
- **16.9** Exercises
- **16.10** Summary and cross-references

Listings live under `code/ch016/` and are re-executed by `make verify` on both interpreters.

---

## 16.1 Nominal versus structural subtyping; `Protocol` (PEP 544)

**Why this exists.** Classic OO subtyping is *nominal*: `Dog` is an `Animal` only if it *declares*
`class Dog(Animal)`. But Python's runtime has always been duck-typed, "if it has `.render()`, it
renders." Before PEP 544 there was no way to express that contract *statically*: a function taking
"anything with `.render()`" had to be typed `Any`, losing all checking. `Protocol` gives structural
subtyping: a class matches a protocol if it has the right members, no inheritance required.

```python
# code/ch016/l01_protocol.py
@runtime_checkable
class Renderable(Protocol):
    def render(self) -> str: ...

class Book:                                   # no base-class relationship to Renderable
    def render(self) -> str:
        return "Book Text"
```

Verified output (CPython 3.13.5):

```text
--- Book satisfies Renderable structurally, without inheriting it ---
  display(Book())          : Book Text
  isinstance(Book(), Renderable): True
  Renderable in Book.__mro__: False (no inheritance)
```

The listing also prints `Renderable.__protocol_attrs__` as `{'render'}`. A static checker verifies
that `Book` has a `render(self) -> str` with a compatible signature; at runtime, `Protocol` is built by
the `typing._ProtocolMeta` metaclass, which collects the protocol's member names into
`__protocol_attrs__`. `Book` satisfies `Renderable`
with no inheritance relationship (`Renderable` is not in its MRO). This is the senior-engineer
contrast: it is Go's interfaces (implicit satisfaction by method set) brought to Python, but checked
statically, versus Java and C++ where conforming to an interface requires an explicit
`implements`/inheritance declaration.

---

## 16.2 `@runtime_checkable` and its limits

By default a `Protocol` is a static-only construct: `isinstance(obj, SomeProtocol)` raises `TypeError`.
The `@runtime_checkable` decorator enables `isinstance`/`issubclass` by overriding the metaclass's
`__instancecheck__`/`__subclasscheck__` to walk the subject's MRO checking that each protocol attribute
name *exists*. The crucial caveat is the chapter opening, run:

```python
# code/ch016/l02_runtime_checkable.py
class BadRender:
    def render(self, a, b):        # the NAME 'render' exists; the signature is wrong
        return "wrong signature"
```

Verified output (CPython 3.13.5):

```text
--- runtime_checkable verifies attribute NAMES exist, not signatures ---
  isinstance(Book(), Renderable)     : True
  isinstance(BadRender(), Renderable): True <- WRONG signature, still True
  isinstance(NoRender(), Renderable) : False
```

`BadRender` passes because it *has* a `render` attribute; that its signature is `render(self, a, b)`,
which cannot stand in for `render(self) -> str`, is invisible to the runtime check. So
`@runtime_checkable` is a *coarse* gate: it answers "does this object have these attribute names?", not
"does it correctly implement the protocol." Use it for capability dispatch (`isinstance(x,
SupportsClose)`), never as a substitute for the static check, and, as §16.6 measures, keep it out of
hot loops.

---

## 16.3 The 3.8-3.10 typing toolbox

Five additions in this window are now everyday vocabulary, and all are *static contracts over ordinary
runtime objects*:

```python
# code/ch016/l03_typing_toolbox.py
def first(xs: list[int]) -> int:        # PEP 585: no typing.List needed
    return xs[0]
def parse(x: int | str) -> str:         # PEP 604 union
    return str(x)
```

Verified output (CPython 3.13.5):

```text
--- builtin generics (PEP 585): a GenericAlias, not the bare class ---
  first([10, 20])          : 10
  type(list[int])          : GenericAlias
  list[int] is list        : False <- erased means NOT the same object
--- X | Y unions (PEP 604): work in isinstance, unlike old typing.Union ---
  parse(5), parse('z')     : 5 z
  isinstance(5, int | str) : True
  isinstance(1.0, int | str): False
--- TypedDict / Literal / Final: static contracts, ordinary runtime objects ---
  TypedDict at runtime is a plain dict: dict {'title': 'Inception', 'year': 2010}
  Literal arg              : r
  Final (not runtime-enforced): 100
--- you cannot isinstance a PARAMETERIZED generic ---
  isinstance([1], list[int]) -> isinstance() argument 2 cannot be a parameterized generic
  isinstance([1], list)      : True (bare class works)
```

**Builtin generics (PEP 585, 3.9)** let you subscript the builtin containers directly, `list[int]`,
`dict[str, int]`, instead of importing `typing.List`. The subscription produces a `types.GenericAlias`,
which is *not* the bare class (`list[int] is list` is `False`), a fact §16.5 returns to. **`X | Y`
unions (PEP 604, 3.10)** replace `typing.Union[int, str]` and, unlike the old `Union`, work in
`isinstance`. **`TypedDict` (PEP 589)** types a dict with fixed string keys and per-key value types, and
at runtime is a plain `dict`. **`Literal` (PEP 586)** restricts a value to specific constants.
**`Final` (PEP 591)** marks a name non-reassignable to the checker, not enforced at runtime. And you
cannot `isinstance` a *parameterized* generic (`isinstance(x, list[int])` raises); only the bare class
works.

---

## 16.4 Variance: covariance, contravariance, invariance, and LSP

Variance governs how subtyping of a type parameter relates to subtyping of the generic. Let `A <: B`
mean "A is a subtype of B," and `F[T]` a generic:

- **Covariant**: preserves direction, `A <: B` implies `F[A] <: F[B]`. Read-only producers are
  covariant: an `Iterable[Dog]` *is an* `Iterable[Animal]` (you can only read animals out).
- **Contravariant**: reverses direction, `A <: B` implies `F[B] <: F[A]`. Consumers are contravariant:
  a `Callable[[Animal], None]` *is a* `Callable[[Dog], None]` (something that accepts any animal can
  stand where a dog-acceptor is needed).
- **Invariant**: no relationship. `list[T]` is invariant because it is *both* readable and writable: if
  `list[Dog]` were a `list[Animal]`, you could `.append(Cat())` into it and corrupt the element type.

This is the Liskov Substitution Principle made precise: to substitute one function for another,
arguments must be contravariant (accept at least as much) and returns covariant (promise at most as
much). The intuition, "be liberal in what you accept, conservative in what you return," is why `list`
is invariant and `Iterable` is covariant. PEP 695 (Chapter 18) lets the checker *infer* variance, so
you rarely write `TypeVar(..., covariant=True)` by hand anymore. The full treatment is **Deep I**.

---

## 16.5 Type erasure and the gradual-typing boundary

Python's typing is *gradual* and *erased*: annotations are metadata stored in `__annotations__`
(Chapter 12), never checked or enforced by the interpreter. Type *checking* happens entirely outside
the interpreter, mypy or pyright reads the source statically and reports errors; nothing in the
bytecode changes, and the check itself costs the running program nothing.

Two precisions that are easy to get wrong. First, **erased does not mean absent.** `list[int]` is not
`list`; subscription builds a distinct `types.GenericAlias` object (§16.3), and `list[int] is list`
evaluates to `False`. What is erased is *enforcement*, not the object.

Second, **annotations are not free.** Through Python 3.13 an annotation expression is evaluated eagerly
when the `def` executes, so annotating a function does real work at definition time, which §16.6
measures at over 5x. This is why `from __future__ import annotations` existed. PEP 649 (Python 3.14)
replaces eager evaluation with a lazily-invoked `__annotate__` function, which is also why a 3.14
annotation may reference a name that does not exist yet without raising (Chapter 12, §12.3). The cost
model therefore differs by interpreter, and §16.6 gives both numbers.

The corollary: annotations are not validation. `def f(x: int): ...; f("nope")` runs without error.
Runtime enforcement is opt-in via libraries that *read* `__annotations__`, pydantic, `dataclasses`
validators, `beartype`, all **Deep I**. The boundary to internalize: **the checker guarantees
consistency of typed code at build time; the runtime guarantees nothing about types.**

---

## 16.6 Measurement: typing is erased, but not free

Two claims from this chapter's material are testable: that `@runtime_checkable` is slow, and the
widespread belief that annotations have "zero runtime overhead."

**Methodology.** `code/ch016/bench_typing_cost.py`, through `_harness/bench.py`. `min` over 15 batches;
within one interpreter; CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| `isinstance` | ratio |
|---|---|
| nominal (`isinstance(obj, ABCBase)`) | 1.00x |
| `@runtime_checkable` protocol | **1.73x** |

A `@runtime_checkable` isinstance costs roughly **1.7x** a nominal one, because it routes through the
protocol metaclass's `__instancecheck__` rather than a direct MRO test. It is coarse (§16.2) *and*
slower; keep it out of hot loops.

| function definition | 3.13 | 3.14 |
|---|---|---|
| bare `def` | 1.00x | 1.00x |
| annotated `def` | **5.6x** | **3.5x** |

An annotated `def` costs several times a bare one, because the annotations are objects the `def`
statement builds. This is precisely why "annotations have zero runtime overhead" is wrong: type
*checking* is free, but annotation *evaluation* at definition time is not. And the number is
version-specific: on 3.13 the annotations are evaluated eagerly (5.6x); on 3.14, PEP 649 makes them
lazy and cuts the cost to 3.5x, but does *not* zero it, because the `__annotate__` function is still
built at definition time. This is the same PEP 649 change that flipped the forward-reference behavior
in Chapter 12; here it shows up as a definition-time cost that shrank but did not vanish.

The practical takeaway: annotate freely, the cost is at import and is small in absolute terms, but do
not annotate a function you generate a million of in a hot loop believing it is free, and do not put a
`@runtime_checkable` isinstance on a hot path.

---

## 16.7 Edges and failure modes

**`@runtime_checkable` checks names, not signatures.** §16.2. `BadRender` passes. Never treat a passing
protocol isinstance as proof of correct implementation; it is a capability gate only.

**`@runtime_checkable` in a hot loop.** §16.6. It is ~1.7x a nominal isinstance and existence-only. Use
a nominal check or restructure to avoid the per-call cost.

**Annotations as validation.** §16.5. `def f(x: int): ...; f("nope")` runs. Reach for pydantic or a
validator when you need runtime enforcement.

**`isinstance` on a parameterized generic.** §16.3. `isinstance(x, list[int])` raises; only the bare
class works. The `[int]` exists for the checker, not for `isinstance`.

**`list`/`dict` are invariant.** §16.4. A function typed `list[Animal]` correctly rejects a `list[Dog]`
from the checker; type the parameter `Sequence[Animal]` (covariant, read-only) if you only read from
it.

**Assuming annotation cost is version-stable.** §16.6. It is 5.6x on 3.13 and 3.5x on 3.14. Measure on
the interpreter you ship on.

---

## 16.8 Connections

**Backward.** Annotations as metadata, and the `__annotations__` storage, are Chapter 12, whose PEP 649
forward-reference flip is the same change that moves §16.6's number. The `_ProtocolMeta` metaclass is
an application of Chapter 4's metaclass and descriptor machinery. Builtin generics reuse the `|`
operator that Chapter 15 gave `dict`.

**Forward.** PEP 695's inferred variance and the `type` statement are Chapter 18. The full type system,
`TypeIs`/`TypeGuard`, overloads, `ParamSpec`, stubs, mypy versus pyright, and runtime validators
(pydantic, beartype), is **Deep I**. Descriptors and ABCs versus protocols are Chapter 4 and **Deep A**.

**Across books.** `Protocol` is how Book II types a boundary it does not own. A C++ object exposed
through **Book I** (`nanobind`) satisfies a Python `Protocol` structurally, with no inheritance from a
Python base, so the analytics layer can be typed against `SupportsMatch` (say) and accept both a pure-
Python order book and the C++ one interchangeably. A tool result from **Book III** is typed as a
`TypedDict` so the checker validates its shape at the seam without a runtime schema. **Deep M** and
**Deep U** own those boundaries; structural typing is what lets one type annotation span both a Python
and a foreign implementation.

---

## 16.9 Exercises

**1. Break the runtime check.** Reproduce §16.2's `BadRender` and confirm it passes `isinstance` against
a protocol it does not satisfy. Then write the smallest static-checker input (a `.py` a checker would
reject) that catches what the runtime check missed, and explain why the runtime cannot do the same.

**2. Measure the annotation cost on both.** Run §16.6's def benchmark on a 3.13 and a 3.14 interpreter
if you have them. Confirm the 5.6x-to-3.5x drop, and explain, using Chapter 12's PEP 649 mechanism, why
the cost shrank but did not reach 1.0x.

**3. Exploit invariance.** Write a function typed `list[Animal]`, call it with a `list[Dog]`, and show
the checker rejects it (or reason about what mypy would say). Then retype the parameter so the call is
accepted, and explain which variance you invoked and why it is safe here but not for a mutable list.

**4. Build a real protocol dispatcher.** Define a `@runtime_checkable` protocol and use it to dispatch
over a heterogeneous list of objects, some satisfying it and some not. Then measure the dispatch cost
against a nominal `isinstance` version to the standard of §16.6, and decide whether the structural
flexibility is worth the 1.7x for your case.

**5. The design question.** Python chose *erased, gradual* typing: annotations are metadata the runtime
ignores, and checking is external. Argue the trade against a language like Java or Rust where types are
enforced by the compiler and affect runtime representation. Your answer must address the zero-runtime-
enforcement guarantee (§16.5), the annotation-evaluation cost that is *not* zero (§16.6), and why a
gradually-typed language can adopt structural typing (`Protocol`) more easily than a nominally-typed one.

---

## 16.10 Summary and cross-references

- **`Protocol`** (PEP 544) gives **structural subtyping** (static duck typing): conformance by *shape*,
  no inheritance, Go-style interfaces checked statically.
- **`@runtime_checkable`** enables `isinstance`/`issubclass` but verifies **attribute existence only**,
  not signatures, so a wrong-signature class passes; it is coarse and ~1.7x a nominal check.
- The **3.8-3.10 toolbox**, builtin generics (`list[int]`, a `GenericAlias`, *not* the bare class),
  `X | Y` unions (work in `isinstance`), `TypedDict`, `Literal`, `Final`, are **static contracts** over
  ordinary runtime objects.
- **Variance** (covariant producers, contravariant consumers, invariant mutables) follows the **Liskov
  Substitution Principle**; `list` is invariant by necessity.
- Typing is **gradual and erased**: `__annotations__` metadata, checked by external tools, **not**
  runtime validation. **Measured:** annotation *evaluation* costs **5.6x** a bare def on 3.13 and
  **3.5x** on 3.14 (PEP 649 reduces but does not eliminate it), so "zero runtime overhead" is wrong.

**Cross-references.** Annotations as metadata and PEP 649 → Chapter 12. `_ProtocolMeta` and descriptors
→ Chapter 4. `|` at the type level → Chapter 15. PEP 695 inferred variance → Chapter 18. The full type
system and runtime validators → Deep I. The structural-typing boundary to Books I and III → Deep M and
Deep U.
