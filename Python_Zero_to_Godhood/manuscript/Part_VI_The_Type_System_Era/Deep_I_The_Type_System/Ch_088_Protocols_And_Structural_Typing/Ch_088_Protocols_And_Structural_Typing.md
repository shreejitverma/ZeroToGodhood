# Chapter 88: Protocols and Structural Typing

Python's duck typing, "if it has `close()`, treat it as closeable", was always a runtime idea with no way to
*express* it to a type checker. `Protocol` (PEP 544) fixes that: it makes duck typing *checkable*. A `Protocol`
types by *shape*, any class with the right methods matches, *no inheritance required*, so you can statically type
a third-party `File`, a stdlib object, or your own class *without touching it*. This is **structural** typing, and
it is more flexible than the **nominal** typing of an `ABC` (which matches only classes that *inherit* from it).
But there is a sharp catch when you make a `Protocol` `runtime_checkable` and use `isinstance`: the check verifies
that the method *names* are present, *not* their signatures. A class whose `close(self, mode, extra)` has the
wrong signature *passes* `isinstance(x, Closeable)`, then fails when actually called. And the structural check is
**1.82x** the cost of a nominal `ABC` check (133 ns versus 73 ns), because it inspects each method rather than
walking the MRO.

This chapter continues **Deep I** with `Protocol`: structural versus nominal typing, why Protocols type classes
you do not own, and the `runtime_checkable` gap, slower *and* shallower than it looks. It formalizes the duck
typing the language has always had.

## Section index

- **88.1** Structural vs nominal
- **88.2** The `runtime_checkable` signature gap
- **88.3** Measurement: structural costs more
- **88.4** Edges and failure modes
- **88.5** Connections
- **88.6** Exercises
- **88.7** Summary and cross-references

Listings live under `code/ch088/` and are re-executed by `make verify` on both interpreters.

---

## 88.1 Structural vs nominal

```python
# code/ch088/l01_protocol.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- Protocol: structural, matches by shape (no inheritance) ---
  RealFile is Closeable          : True
  (RealFile does not inherit anything: it just HAS close())
--- the gap: runtime_checkable checks NAMES, not signatures ---
  WrongClose is Closeable        : True
  (its close(self, mode, extra) has the wrong signature, yet passes!)
--- ABC: nominal, matches only by inheritance/registration ---
  FileABC is CloseableABC        : True
  HasCloseNoInherit is CloseableABC : False
  (has close() but does not inherit: does NOT match)
--- the rule ---
  Protocol: structural typing for shapes/duck typing (incl. classes you
            do not own); rely on a static checker for signature safety
  ABC: nominal, explicit opt-in via inheritance (no name-collision false hits)
```

The contrast is between *shape* and *lineage*. `RealFile` matches `Closeable` (a `Protocol` with a `close`
method) even though it inherits *nothing*, it matches *structurally*, because it *has* the method. This is duck
typing made checkable: a static checker will accept *any* object with a `close(self) -> None` where a `Closeable`
is expected, including classes from libraries you cannot modify. An `ABC`, by contrast, matches *nominally*:
`FileABC` matches `CloseableABC` because it *inherits* from it, and `HasCloseNoInherit`, which has an identical
`close` method but does *not* inherit, does *not* match. The `ABC` requires explicit opt-in; the `Protocol` does
not.

That difference decides which to use. **Protocols** are for typing *behavior* across an open set of classes,
especially ones you do not own, "anything closeable", "anything with a `read`". **ABCs** are for a *closed*
hierarchy you control, where explicit inheritance documents the relationship and prevents accidental matches.

---

## 88.2 The `runtime_checkable` signature gap

The middle block is the trap. Making a `Protocol` `runtime_checkable` lets you use `isinstance(x, Closeable)` at
runtime, but that check is *shallow*: it verifies only that `x` has attributes with the Protocol's method *names*,
not that those methods have the right *signatures* or *return types*. So `WrongClose`, whose method is
`close(self, mode, extra)`, three required arguments instead of zero, *passes* `isinstance(x, Closeable)`, and
then raises `TypeError` the moment your code calls `x.close()` with no arguments. The `isinstance` said "yes, this
is closeable" about an object that is *not* usable as one.

This is a genuine gap, not a bug: `isinstance` cannot cheaply verify signatures (it would have to introspect and
compare parameters, Chapter 49, for every check), so `runtime_checkable` deliberately checks only presence. A
*static* checker does *not* have this gap, mypy/pyright verify the full signature, so `WrongClose` would be
*rejected* statically where a `Closeable` is expected. The gap exists only for the *runtime* `isinstance`, which
is why it is dangerous: the static tooling is precise, and the runtime check people reach for is not.

The rule: **use Protocols for *static* structural typing (where the checker verifies signatures for free), and
treat `runtime_checkable` `isinstance` as a *presence* check only, never as proof the object's methods have the
right signatures.** If you need a runtime guarantee that an object is genuinely usable, call the method and handle
the failure, or validate the signature explicitly (Chapter 49), do not trust the `isinstance`. And prefer to
avoid `runtime_checkable` isinstance in favor of the static check plus, at boundaries, actually *using* the object
(EAFP, Chapter 6): if it quacks when you make it quack, it is a duck; `isinstance` only checks that it *has a
`quack` attribute*.

---

## 88.3 Measurement: structural costs more

**Methodology.** `code/ch088/bench_isinstance.py`. `isinstance` against a `runtime_checkable` `Protocol` (three
methods) versus against an `ABC` (nominal). `min` per call; ratio relative to the `ABC`. CPython 3.13.5, Apple M3
Pro, macOS 27.0, arm64.

| `isinstance` check | min per call | ratio |
|---|---|---|
| `isinstance(x, ABC)` (nominal) | **73 ns** | 1.00x |
| `isinstance(x, Protocol)` (structural) | **133 ns** | **1.82x** |

The nominal `ABC` check is **73 ns**, essentially an MRO/`__subclasshook__` walk. The structural `Protocol` check
is **133 ns**, **1.82x** more, because it must confirm the object has *each* of the Protocol's methods (a
`getattr`/`hasattr` per method), so its cost grows with the *number of methods* in the Protocol. And, per §88.2,
that extra work only checks *names*, so it is slower *and* weaker, more cost for a shallower guarantee.

The rule: **prefer static structural typing over `runtime_checkable` `isinstance`.** The static check is *free*
at runtime (erasure, Chapter 86), *precise* (verifies signatures), and catches mismatches before running; the
runtime `isinstance` is *slower*, *shallower* (names only), and *scales with the Protocol size*. When you
genuinely need a runtime type test, an `ABC` (nominal) is both faster and free of the name-collision false
positive, at the cost of requiring explicit inheritance. So: `Protocol` for static structural typing (the common,
recommended use); `ABC` when you need a fast, precise *runtime* `isinstance` over a hierarchy you control; and
`runtime_checkable` `isinstance` only when you accept it is a presence-only check. As throughout Deep I, the
static tool is the cheap and precise one; the runtime check costs more and guarantees less.

---

## 88.4 Edges and failure modes

**Trusting `runtime_checkable` `isinstance` for usability.** §88.2. It checks method *names*, not signatures, so a
wrong-signature class passes and then fails when called. Use it as a presence check only; rely on static checking
or actually calling the method.

**`isinstance` cost scaling with Protocol size.** §88.3. Each method is a lookup, so a large `runtime_checkable`
Protocol is slow to check. Keep runtime-checked Protocols small, or use an `ABC`.

**`Protocol` for a closed hierarchy.** If you *own* all the implementers and want explicit opt-in, an `ABC` (or
plain inheritance) documents the relationship and prevents accidental structural matches. Use `Protocol` for open
sets / third-party classes.

**Non-method members in `runtime_checkable`.** `runtime_checkable` only reliably checks *methods*; data attributes
and properties are checked inconsistently (an instance may not have the attribute until set). Prefer method-only
Protocols for runtime checks.

**Explicit inheritance from a `Protocol`.** You *can* inherit from a `Protocol` (to get its method stubs or to be
explicit), but it is not required for matching, structural typing does not need it. Do not add inheritance
thinking it is necessary; add it only for documentation or default implementations.

**Forgetting the static checker.** Like all typing (Chapter 86), a `Protocol` does nothing without mypy/pyright.
Its main value, precise structural checking, is a *static* feature; without a checker it is just documentation
(and the `runtime_checkable` isinstance, with its gap).

---

## 88.5 Connections

**Backward.** Structural typing formalizes the duck typing and EAFP of Chapter 6. The `ABC` and `__subclasshook__`
machinery is the metaclass/ABC material of Chapters 4 and 31. The method-presence check is the attribute lookup of
Chapter 4. Type erasure (why static Protocol checks are free) is Chapter 86. `runtime_checkable`'s cost was also
touched in Chapter 16.

**Forward.** `TypeVar`/generics (generic Protocols), `overload`, and the rest of the static toolkit are the rest
of **Deep I**. The `collections.abc` Protocols (`Iterable`, `Sized`, `Container`) that the language itself uses
are Chapter 69 and Deep I. Signature introspection (for a real runtime signature check) is Chapter 49.

**Across books.** Protocols are how Book II types the pluggable boundaries into **Book III** without coupling to
concrete classes. A **Book III** system types its retriever, embedder, and store slots as Protocols (`class
Retriever(Protocol): def search(self, q: str) -> list[Doc]: ...`), so any object with the right shape, a
third-party client, a fake for tests, plugs in and is *statically* checked, with no inheritance required. The
§88.2 gap is why it relies on the *static* check for signature safety and treats any `runtime_checkable`
`isinstance` as presence-only, which **Deep U** enforces at the plugin seam.

---

## 88.6 Exercises

**1. Match by shape.** Reproduce §88.1: define a Protocol and show an unrelated class with the right methods
matches it (no inheritance), while an ABC requires inheritance. Explain structural vs nominal.

**2. Expose the gap.** Show a class with a wrong-signature method passing `runtime_checkable` `isinstance` and then
failing when called. Explain why `isinstance` misses it and a static checker would not.

**3. Measure the cost.** Run §88.3's benchmark and confirm the structural check is slower than the nominal one.
Add methods to the Protocol and show the check gets slower. Explain the per-method lookup.

**4. Choose the tool.** For several cases (type an open set of file-like objects, a closed hierarchy you own, a
runtime type test), pick Protocol or ABC and justify each. Explain the opt-in vs structural axis.

**5. The design question.** Protocols make duck typing checkable but `runtime_checkable` checks names only. Argue
how to use Protocols safely. Your answer must use the §88.2 gap and §88.3 cost, and explain why the static check
is the precise one and the runtime check is presence-only.

---

## 88.7 Summary and cross-references

- **`Protocol`** types by **shape** (structural): any class with the right methods matches, **no inheritance**,
  so it types classes you do not own, duck typing made checkable. An **`ABC`** types by **lineage** (nominal):
  only classes that inherit/register match.
- **`runtime_checkable` `isinstance` checks method NAMES, not signatures:** a wrong-signature class passes and
  then fails when called. A *static* checker verifies the full signature; the runtime check does not.
- **Measured:** structural `isinstance(x, Protocol)` is **1.82x** a nominal `isinstance(x, ABC)` (133 ns vs 73 ns)
  and scales with the number of methods, slower *and* shallower.
- **Use Protocols for static structural typing** (precise, free at runtime); use an **ABC** for a fast, precise
  runtime `isinstance` over a hierarchy you own; treat `runtime_checkable` `isinstance` as **presence-only**.

**Cross-references.** Duck typing/EAFP → Chapter 6. ABC/metaclass machinery → Chapters 4, 31. Attribute lookup →
Chapter 4. Type erasure → Chapter 86. `runtime_checkable` cost → Chapter 16. `collections.abc` → Chapter 69.
Signature introspection → Chapter 49. `TypeVar`/generics → the rest of Deep I. The plugin seam → Deep U.
