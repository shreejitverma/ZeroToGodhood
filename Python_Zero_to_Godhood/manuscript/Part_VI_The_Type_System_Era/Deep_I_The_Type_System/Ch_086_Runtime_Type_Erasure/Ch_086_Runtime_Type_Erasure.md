# Chapter 86: Runtime Type Erasure

A developer adds `def charge(amount: int) -> Receipt:` and assumes Python will now reject a string amount. It
will not. `charge("100")` runs exactly as if the annotation were not there, because **Python does not check
type annotations at runtime**. The annotation is *metadata*, stored in `__annotations__` for static type
checkers (mypy, pyright) and introspection tools, and then *ignored* by the interpreter. A function may accept
arguments that violate its parameter annotations, return values that violate its return annotation, and pass a
`list[str]` where a `list[int]` is declared, all without a whisper. This is **type erasure**: annotations exist
at *authoring* time (for tools) and are *erased* from the runtime's behavior. It has a surprising corollary
measured here: annotations are *free*, an annotated-but-unchecked function costs the same as an unannotated one
(16 ns), while a function that *actually validates* its input with `isinstance` costs **1.55x** more, because
only the explicit check does any work.

This chapter opens **Deep I** (the type system) with the foundational fact that everything else rests on:
Python's types are *gradual* and *static-tool-facing*, not runtime-enforced. Understanding erasure, what
annotations do and do not do, is what makes the rest of the type system (generics, protocols, `get_type_hints`)
make sense.

## Section index

- **86.1** Annotations are metadata, not checks
- **86.2** Static checking vs runtime validation
- **86.3** Measurement: free annotations, costed validation
- **86.4** Edges and failure modes
- **86.5** Connections
- **86.6** Exercises
- **86.7** Summary and cross-references

Listings live under `code/ch086/` and are re-executed by `make verify` on both interpreters.

---

## 86.1 Annotations are metadata, not checks

```python
# code/ch086/l01_type_erasure.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- annotations are stored as metadata, not enforced ---
  greet.__annotations__ : {'name': <class 'str'>, 'return': <class 'str'>}
  greet(42)             : 'hi 42'  (int accepted despite name: str)
--- generic parameters are erased: list[int] accepts anything ---
  total([1, 2, 3])      : 6
  total([1.5, 2.5])     : 4.0  (floats in a list[int]: fine)
--- a function can even violate its OWN return annotation ---
  as_int(5) returned    : '5'  (a str, despite -> int)
--- the rule ---
  annotations are for STATIC checkers (mypy/pyright) + introspection
  the runtime ignores them; for runtime guarantees, validate explicitly
  (isinstance, or a validation library like pydantic)
```

The annotations are *there*, `greet.__annotations__` shows `{'name': str, 'return': str}`, and they are *not
enforced*. `greet(42)` passes an `int` where `str` is annotated and runs fine (`'hi 42'`). `total([1.5, 2.5])`
passes floats where `list[int]` is declared and sums them happily. `as_int(5)` returns a `str` despite `-> int`.
The interpreter reads the annotations only to *store* them; it never *acts* on them.

The reason is deliberate design. Python's typing is **gradual**: you can annotate none, some, or all of your
code, and annotated and unannotated code interoperate. Enforcing annotations at runtime would break that (every
call would need a check, mixed code would be inconsistent) and would duplicate what a *static* checker does
better and for free. So annotations are a *contract you assert* and a *tool verifies before you run*, not a
runtime guard. The interpreter's job is to *record* them (for tools and `inspect`, Chapter 49); checking them is
the type checker's job, or yours.

---

## 86.2 Static checking vs runtime validation

Erasure splits "type safety" into two distinct, complementary activities, and conflating them is the source of
most confusion.

**Static checking** (mypy, pyright, run in your editor and CI) reads the annotations *without running the code*
and reports every place a type is violated, `charge("100")` is flagged as passing `str` where `int` is
expected, *before* the program runs. It catches a huge class of bugs, at authoring time, for zero *runtime*
cost, and it is the primary payoff of annotating: types are a *specification* the checker verifies. The catch is
that it only checks what it can *see*: it cannot know the type of data arriving from *outside* the program (a
JSON body, a database row, user input), whose actual type is unknown until runtime.

**Runtime validation** (an explicit `isinstance` check, or a library like `pydantic`/`attrs`) checks the *actual*
value *while running*, and it *does* cost (§86.3). It is necessary exactly where static checking cannot reach:
the *trust boundary*, where untyped external data enters and you must confirm it matches what your typed code
expects. Inside the boundary, static checking suffices; at the boundary, you validate.

The rule: **use static type checking (mypy/pyright in CI) to catch type errors before running, for free at
runtime, and add explicit runtime validation only at trust boundaries** (external input: request bodies, config,
deserialized data). Do not expect annotations to validate anything at runtime (they do not), and do not sprinkle
`isinstance` checks through internal code that a static checker already proves correct, that pays a runtime cost
to re-check what is statically guaranteed. Annotate everywhere (free, tool-verified); validate only where
untyped data crosses in.

---

## 86.3 Measurement: free annotations, costed validation

**Methodology.** `code/ch086/bench_erasure.py`. An annotated-but-unchecked function versus one that validates its
argument with `isinstance`. `min` per call; ratio relative to the annotated one. CPython 3.13.5, Apple M3 Pro,
macOS 27.0, arm64.

| a function call | min per call | ratio |
|---|---|---|
| annotated (unchecked) | **15.9 ns** | 1.00x |
| validated (`isinstance`) | **24.7 ns** | **1.55x** |

The annotated function costs **15.9 ns**, *identical* to an unannotated one, because the annotation does *nothing*
at runtime. The validated function costs **24.7 ns**, **1.55x** more, because it actually runs an `isinstance`
check on every call. So the annotation is *free* precisely *because* it is not enforced: there is no check to
pay for. A runtime guarantee is a *separate*, *explicit* cost you opt into.

The rule the measurement makes concrete: **annotations cost nothing, so annotate freely; runtime validation
costs, so apply it only where needed.** Because annotating is free at runtime and paid back by static checking,
there is no performance reason not to annotate all your code. And because validation costs ~1.5x per call, you
reserve it for the trust boundary rather than the interior, where a static checker already proves the types and a
runtime `isinstance` would be redundant work. This is the efficient division of labor: *static* verification for
free at authoring time everywhere, *runtime* validation, paid, only where the program meets untyped reality.
(Note the exceptions to zero-cost: evaluating an annotation *expression* at function definition has a one-time
cost, addressed by PEP 563/649 deferred annotations, Chapter 12, and calling `get_type_hints` to *resolve*
annotations at runtime does real work, a later Deep I topic. The *ignoring* of annotations during normal calls
is what is free.)

---

## 86.4 Edges and failure modes

**Expecting annotations to validate at runtime.** §86.1. They do not; a wrongly-typed call runs fine. For a
runtime guarantee, validate explicitly (`isinstance`, `pydantic`).

**Trusting external data because it is annotated.** §86.2. A `data: dict[str, int]` parameter does not make the
incoming JSON actually match; deserialized/external data can be anything. Validate at the boundary.

**Redundant `isinstance` inside statically-checked code.** Re-checking types the checker already proves pays a
runtime cost for no benefit. Trust the static check internally; validate only untyped input.

**Assuming generic parameters are enforced.** `list[int]`, `dict[str, User]`, etc. are erased, the runtime sees
`list`, `dict`, with no element-type check. `isinstance(x, list[int])` even raises `TypeError` (you cannot
isinstance a parameterized generic). Check `isinstance(x, list)` and validate elements separately if needed.

**Annotations that fail to evaluate.** A bad annotation *expression* (a forward reference to an undefined name,
evaluated eagerly) can raise at definition time, or `get_type_hints` can fail to resolve it. Deferred evaluation
(PEP 563/649, Chapter 12) mitigates this; know that annotations are still *expressions* even if unenforced.

**Skipping static checking entirely.** Annotations with *no* checker are just documentation, and can silently
drift out of sync with the code (an annotation says `int`, the code returns `str`, nothing complains). Run mypy/
pyright in CI so annotations are *verified*, not merely decorative.

---

## 86.5 Connections

**Backward.** Where annotations are *stored* (`__annotations__`) and read (`inspect`, `get_type_hints`) is Chapter
49. Deferred annotation evaluation (PEP 563/649) and its costs are Chapter 12. The `isinstance` runtime check is
the object-model type test of Chapter 4. Typing basics (`Optional`, generics syntax) are Chapter 16.

**Forward.** The rest of **Deep I**: `Protocol` (structural typing), `TypeVar`/generics, `Union`/`Literal`/
`TypedDict`, `get_type_hints` and annotation resolution, variance, and the `typing` module in depth. Validation
libraries (`pydantic`, `attrs`) that *do* enforce at runtime are a Deep I/Deep O application. Static checkers
(mypy/pyright) and their configuration are a tooling topic.

**Across books.** Erasure is why Book II *both* annotates thoroughly *and* validates at the seams into
**Book III**. A **Book III** service annotates all internal code (statically checked in CI, free at runtime) and
validates *external* input, request bodies, model outputs, tool arguments, with `pydantic` at the boundary,
where the data is untyped and static checking cannot reach. Confusing "it is annotated" with "it is validated" is
exactly the bug that lets malformed external data into typed internals, which **Deep U** guards against at the
input seam. Static typing catches the *internal* type bugs before they ship.

---

## 86.6 Exercises

**1. Break the annotation.** Reproduce §86.1: call an annotated function with the wrong types (arguments and
return) and show it runs anyway. Inspect `__annotations__`. Explain what the runtime does with annotations.

**2. Static vs runtime.** Write a function with a type error, run mypy/pyright (it flags it) and then run the code
(it may or may not fail). Explain what static checking catches that the runtime does not, and vice versa.

**3. Measure the freedom.** Run §86.3's benchmark and confirm the annotated function is as fast as an unannotated
one while validation costs. Explain why annotations are free.

**4. Validate a boundary.** Write a function that deserializes JSON and validate the result matches the expected
types (with `isinstance` or `pydantic`). Explain why the boundary needs validation that internal code does not.

**5. The design question.** Python erases types at runtime, relying on static checkers for verification. Argue the
trade-offs versus a language that enforces types at runtime. Your answer must use the §86.3 cost, the static-vs-
runtime split, and explain where each kind of checking belongs.

---

## 86.7 Summary and cross-references

- **Python does not enforce type annotations at runtime** (type erasure): they are **metadata** in
  `__annotations__` for static checkers and introspection, and the interpreter *ignores* them. A wrongly-typed
  call, or a violated return, runs fine; generic parameters (`list[int]`) are erased to their base type.
- **Type safety splits in two:** **static checking** (mypy/pyright) verifies annotations *before running*, for
  free at runtime, but cannot see external data; **runtime validation** (`isinstance`/`pydantic`) checks *actual*
  values *while running*, and costs.
- **Measured:** an annotated-but-unchecked call is **as fast as unannotated** (15.9 ns); an `isinstance`-validated
  call is **1.55x** more. Annotations are free because they are not enforced.
- **Annotate everywhere (free, statically verified); validate only at trust boundaries** (external input). Run a
  static checker in CI so annotations are verified, not just documentation.

**Cross-references.** `__annotations__`/`inspect` → Chapter 49. Deferred annotations (PEP 563/649) → Chapter 12.
`isinstance`/object model → Chapter 4. Typing basics → Chapter 16. Protocols, generics, `get_type_hints` → the
rest of Deep I. `pydantic` validation → Deep I, Deep O. The input seam → Deep U.
