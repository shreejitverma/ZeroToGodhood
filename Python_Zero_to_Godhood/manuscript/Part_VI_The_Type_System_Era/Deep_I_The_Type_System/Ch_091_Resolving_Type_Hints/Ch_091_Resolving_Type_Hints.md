# Chapter 91: Resolving Type Hints

The previous Deep I chapters used annotations that the *runtime ignores*. But some runtime code, serializers,
validators like `pydantic`, dependency-injection frameworks, ORMs, actually *needs* the types: it reads a class's
annotations to decide how to (de)serialize each field. And here it hits a wall that the erasure chapters hid.
Under **deferred annotations** (`from __future__ import annotations`, PEP 563, and the direction of PEP 649,
Chapter 12), a class's `__annotations__` are stored as **strings**, `{'value': 'int', 'next': 'Node | None'}`,
not evaluated type objects. To get the *actual* types, you must call `typing.get_type_hints`, which *evaluates*
each annotation string in the right namespace and resolves forward references (like a class referring to
itself). That resolution is **expensive**: **1372x** a raw `__annotations__` access (16 us versus 12 ns). So a
framework that reflects on a type must resolve its hints *once* and *cache* them, never per request.

This chapter continues **Deep I** with `get_type_hints`: why deferred annotations are strings, what resolution
does (and costs), and the caching discipline it demands. It is the reflection-cost companion to `inspect.signature`
(Chapter 49), applied to type hints.

## Section index

- **91.1** Strings in, types out
- **91.2** Why resolution is expensive
- **91.3** Measurement: raw vs resolved vs cached
- **91.4** Edges and failure modes
- **91.5** Connections
- **91.6** Exercises
- **91.7** Summary and cross-references

Listings live under `code/ch091/` and are re-executed by `make verify` on both interpreters.

---

## 91.1 Strings in, types out

```python
# code/ch091/l01_get_type_hints.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- raw __annotations__ are unevaluated STRINGS ---
  Node.__annotations__ : {'value': 'int', 'next': 'Node | None'}
  'value' is a string  : True
--- get_type_hints RESOLVES the strings to real type objects ---
  resolved 'value'     : int
  'value' is the int type : True
--- and it resolves FORWARD references (Node referring to itself) ---
  'next' resolved (not a string) : True
  'next' mentions Node : True
--- a function's hints, resolved ---
  handler hints keys   : ['return', 'tags', 'user_id']
  return is dict       : True
--- the rule ---
  raw __annotations__ is cheap but unresolved (strings under deferral)
  get_type_hints resolves them but is expensive: CACHE the result
```

With deferred annotations, `Node.__annotations__` holds *strings*: `'int'`, `'Node | None'`, not the `int` type
or a `Union`. The annotation expressions were *not evaluated* at class-definition time, which is the *point* of
deferral, definition is cheap, and an annotation can reference a name not yet defined (a **forward reference**,
like `Node` referring to *itself* inside its own body, which would be a `NameError` if evaluated eagerly).

`typing.get_type_hints(Node)` does the evaluation *on demand*: it `eval`s each annotation string in the class's
module and local namespaces, turning `'int'` into the `int` type and `'Node | None'` into the actual union,
resolving the `Node` forward reference to the class. For a function, it returns the resolved parameter and return
types (`handler`'s `return` is the `dict` type). So `get_type_hints` is the bridge from the *stored form*
(strings, cheap, deferred) to the *usable form* (real type objects), and that bridge is where the cost is.

---

## 91.2 Why resolution is expensive

`get_type_hints` is not a dict lookup; it is an *evaluation*. For each annotation, it must locate the correct
namespaces (the object's module globals, and for a class the enclosing/local scopes and the MRO), `eval` the
annotation *expression* (a real compile-and-execute of the string, `'list[int]'` builds a `types.GenericAlias`,
`'Node | None'` builds a union), and resolve every name in it, including forward references that may point to
types defined elsewhere. For a class it walks the *MRO*, merging hints from base classes. That is orders of
magnitude more work than reading the raw `__annotations__` dict, which is why §91.3 measures ~1000x.

This is the *cost* side of deferral's *benefit*. PEP 563/649 make annotations cheap to *store* (strings, or
lazily computed) and robust to forward references, at the price that *using* them requires an expensive
resolution step. For code that *never* reads the types at runtime (the common case, Chapter 86), that price is
never paid, deferral is pure win. But for the frameworks that *do* read them, the resolution is unavoidable and
expensive.

The rule follows directly, and it is the same as `inspect.signature` (Chapter 49): **resolve type hints once per
type and cache the result; never call `get_type_hints` per operation.** A serializer, validator, or DI container
should build the resolved hints for a class *when the class is registered* (or on first use, memoized), and reuse
that cached mapping for every subsequent object, because a type's hints do not change. Calling `get_type_hints`
on every request re-`eval`s the annotations every time, turning a one-time setup cost into a per-request tax,
exactly the anti-pattern Chapter 49 warned about for signatures, and it is even more expensive here.

---

## 91.3 Measurement: raw vs resolved vs cached

**Methodology.** `code/ch091/bench_get_type_hints.py`. Reading raw `__annotations__`, a *cached* resolved-hints
dict, and a *fresh* `get_type_hints(f)` each call, on a function with string annotations. `min` per call; ratios
relative to raw `__annotations__`. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| access a function's types | min per call | ratio |
|---|---|---|
| raw `__annotations__` | **11.5 ns** | 1.00x |
| cached hints (dict access) | **8.3 ns** | 0.72x |
| `get_type_hints(f)` (fresh) | **15,811 ns** | **1372x** |

Raw `__annotations__` is a dict attribute access, **11.5 ns**. A *cached* resolved-hints dict is even cheaper
(**8.3 ns**, a plain dict lookup). A *fresh* `get_type_hints` is **15,811 ns, 1372x** the raw access, because it
`eval`s and resolves every annotation each call. The gap between the fresh resolution and the cached lookup, ~1900x,
is *exactly* the waste of resolving per operation instead of once.

The rule: **resolve once, cache, then read the cache.** The cached-hints row is the target state: after paying the
~16 us resolution *one time* per type, every subsequent access is a ~8 ns dict lookup, faster even than the raw
strings. A framework that reflects on types, `pydantic` building a model's field types, a serializer mapping
fields, a DI container reading constructor parameter types, must memoize `get_type_hints` per class (a dict keyed
by the type, or `functools.cache`), or its per-request cost is dominated by re-resolving annotations that never
change. This is the recurring Deep I/Deep S lesson: rich reflection is a *setup* activity, expensive when
repeated, so you pay it once and cache. (The mainstream libraries do this; if you write reflection yourself,
you must too.)

---

## 91.4 Edges and failure modes

**Calling `get_type_hints` per request.** §91.3. ~1372x a raw access, re-`eval`ing unchanged annotations. Resolve
once per type and cache.

**Forward references that fail to resolve.** `get_type_hints` `eval`s annotations in specific namespaces; if a
referenced name is not importable there (defined in another module, only under `TYPE_CHECKING`, a local scope it
cannot see), resolution raises `NameError`. Ensure referenced types are importable at resolution time, or pass
explicit `globalns`/`localns`.

**`TYPE_CHECKING`-only imports.** Types imported under `if TYPE_CHECKING:` (to avoid a runtime import or a cycle,
Chapter 64) are *not* available at runtime, so `get_type_hints` cannot resolve annotations that use them (unless
deferred and never resolved). If a framework must resolve them, the import cannot be `TYPE_CHECKING`-only.

**Reading raw `__annotations__` expecting types.** Under deferral, `__annotations__` are *strings*; code that
treats them as type objects breaks. Use `get_type_hints` to get types (and cache), or read the strings knowing
what they are.

**PEP 563 vs PEP 649 differences.** The exact stored form (stringified per PEP 563, or lazily computed per PEP
649, Chapter 12) differs by version and settings, but `get_type_hints` is the version-independent way to obtain
resolved types. Do not hand-parse `__annotations__`; use `get_type_hints`.

**`include_extras`.** By default `get_type_hints` strips `Annotated[...]` metadata; pass `include_extras=True` to
keep it (needed by frameworks that use `Annotated` for validation/metadata, e.g. `pydantic`, FastAPI).

---

## 91.5 Connections

**Backward.** Deferred annotations (PEP 563/649), why they are strings/lazy, are Chapter 12. The reflection-cost-
and-cache lesson is Chapter 49 (`inspect.signature`). The forward-reference/`TYPE_CHECKING` interplay is Chapter
64 (circular imports). Erasure (why *most* code never pays this) is Chapter 86.

**Forward.** Validation and serialization libraries (`pydantic`, `attrs`, `dataclasses.fields`) that consume
resolved hints are a Deep I/Deep O application. `Annotated` and metadata-carrying types are the rest of **Deep
I**. Generic and recursive type resolution is a deeper Deep I topic.

**Across books.** Cached hint resolution is how Book II's framework glue reads types once for **Book III**. A
**Book III** serving layer that maps request/response models, or generates tool schemas from function signatures,
resolves each type's hints *at registration* and caches them, so per-request dispatch reads a cached dict, not a
fresh `get_type_hints`. The §91.3 per-request cost is exactly the trap that makes a reflection-heavy framework
slow, which **Deep U** guards against by resolving-and-caching at startup. The tool-schema generation from
signatures (Chapter 49) and type hints is a **Book III** bridge.

---

## 91.6 Exercises

**1. See strings become types.** Reproduce §91.1 (with `from __future__ import annotations`): show `__annotations__`
are strings and `get_type_hints` resolves them, including a self-referential forward reference. Explain what
resolution does.

**2. Measure the cost.** Run §91.3's benchmark and confirm `get_type_hints` is orders of magnitude more expensive
than a raw or cached access. Explain the evaluation work and why caching helps.

**3. Cache the hints.** Wrap `get_type_hints` in `functools.cache` (keyed by the type) and show the amortized cost
collapses to a dict lookup. Explain why a type's hints can be cached forever.

**4. Break a forward reference.** Write an annotation referencing a `TYPE_CHECKING`-only import and show
`get_type_hints` raises `NameError`. Explain why, and how a framework that needs the type must import it at
runtime.

**5. The design question.** Deferred annotations make definition cheap and forward references possible, at the
cost of an expensive resolution step for code that reads types. Argue why this trade is right, and what discipline
it demands. Your answer must use the §91.3 cost, the caching rule, and Chapter 12's deferral.

---

## 91.7 Summary and cross-references

- Under **deferred annotations** (PEP 563/649), `__annotations__` are **strings** (or lazily computed), cheap to
  store and forward-reference-safe. **`typing.get_type_hints`** resolves them to **real type objects**, evaluating
  each annotation and resolving forward references.
- **Resolution is expensive:** it `eval`s each annotation in the right namespaces and walks the MRO for classes.
- **Measured:** a fresh `get_type_hints(f)` is **1372x** a raw `__annotations__` access (16 us vs 12 ns); a
  **cached** resolved-hints dict is a ~8 ns lookup. **Resolve once per type and cache;** never per request.
- **Edges:** forward references and `TYPE_CHECKING`-only imports may fail to resolve (`NameError`); use
  `get_type_hints` (not raw parsing) for version-independent resolution; `include_extras=True` to keep
  `Annotated` metadata.

**Cross-references.** Deferred annotations (PEP 563/649) → Chapter 12. Reflection cost and caching
(`inspect.signature`) → Chapter 49. Forward refs/`TYPE_CHECKING` → Chapter 64. Erasure → Chapter 86. `pydantic`/
validation → Deep I, Deep O. Tool-schema generation → Deep U (Book III bridge).
