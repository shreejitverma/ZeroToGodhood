# Chapter 93: Union and Optional

`Optional[int]` does not mean "an optional argument". It means "an `int` *or* `None`", exactly `int | None`,
and confusing the two, thinking `Optional` marks a parameter as having a default, is a common beginner error.
The modern spelling is the `|` operator: `X | Y` (PEP 604, 3.10+) is a union, equivalent to `Union[X, Y]`, and
`Optional[X]` is just `X | None`. Unlike most typing constructs, which are erased and static-only, `X | Y` is a
*real runtime object* you can pass to `isinstance`: `isinstance(x, int | str)` works. But that runtime
usefulness hides a cost trap: writing the union *inline*, `isinstance(x, int | str)`, *builds a new union
object on every call*, **3.8x** slower than checking against a *precomputed* union (38 ns versus 10 ns), and the
precomputed union is even faster than an `(int, str)` tuple. The cost is in *constructing* the union, not
*checking* it.

This chapter continues **Deep I** with union types: the `|` syntax, why `Optional` is `| None`, how unions
narrow, and the inline-vs-precomputed `isinstance` cost. It is the "one of several types" construct that,
unusually, is both a static annotation and a runtime object.

## Section index

- **93.1** `X | Y`, `Optional`, and narrowing
- **93.2** The inline-union cost
- **93.3** Measurement: precomputed vs tuple vs inline
- **93.4** Edges and failure modes
- **93.5** Connections
- **93.6** Exercises
- **93.7** Summary and cross-references

Listings live under `code/ch093/` and are re-executed by `make verify` on both interpreters.

---

## 93.1 `X | Y`, `Optional`, and narrowing

```python
# code/ch093/l01_union.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- X | Y is equivalent to Union[X, Y] ---
  (int | str) == Union[int, str] : True
  Optional[int] == (int | None)  : True
  Optional means 'or None', not 'optional argument'
--- X | Y is a real runtime object: usable in isinstance (3.10+) ---
  isinstance(5, int | str)   : True
  isinstance('a', int | str) : True
  isinstance(1.5, int | str) : False
--- a union narrows in the checker; at runtime you branch/isinstance ---
  describe(42)  : 'int:42'
  describe('hi'): 'str:hi'
--- the rule ---
  X | Y is the modern union; Optional[X] is X | None
  usable in isinstance, but precompute the union for a hot loop
  (building `int | str` inline allocates a union object per call)
```

The equivalences are exact: `int | str` *equals* `Union[int, str]`, and `Optional[int]` *equals* `int | None`.
The `|` syntax (PEP 604) is the modern, import-free spelling; `Union`/`Optional` from `typing` are the older
equivalents. The key clarification: **`Optional[X]` means `X | None`**, a value that is either an `X` or `None`,
*not* a parameter that may be omitted. A parameter is made optional by giving it a *default* (`def f(x: int | None
= None)`); `Optional` only describes the *type*.

`X | Y` is also a genuine *runtime* object, so `isinstance(x, int | str)` works (3.10+), returning `True` for an
`int` or `str` and `False` otherwise. And a union *narrows*: inside `if isinstance(x, int):`, the checker knows
`x` is an `int` (not the full `int | str`), and in the `else` it is a `str`. At runtime you handle a union by
*branching* (isinstance, or matching on a discriminator); statically, the checker follows those branches to
narrow the type in each.

---

## 93.2 The inline-union cost

`X | Y` being a runtime object is convenient and has a subtle cost. Each time the expression `int | str` is
*evaluated*, it *constructs* a `types.UnionType` object (like `list[int]` constructing a `GenericAlias`, Chapter
92). In an *annotation*, that happens once (or never, under deferred annotations, Chapter 12). But in an
`isinstance` *call written inline*, `isinstance(x, int | str)`, the union is rebuilt *on every call*, because the
expression is re-evaluated each time. So a hot loop doing `isinstance(x, int | str)` per iteration pays the
union-construction cost every iteration, for a union that never changes.

The fix is to *build the union once*. Assign it to a module-level constant, `NUMERIC = int | float`, and check
`isinstance(x, NUMERIC)`, so the union object is constructed a single time and reused. Measured (§93.3), the
precomputed union is not just faster than the inline one, it is faster than an `(int, str)` *tuple* too, because
once the union object exists, the membership check is efficient. So the ranking is: precomputed union (fastest) >
tuple > inline union (slowest).

The rule: **use `X | Y` freely in annotations (free or once), but for repeated `isinstance` checks, precompute
the union** (a module constant) rather than building it inline per call. For a *one-off* check the difference is
nanoseconds and irrelevant; the trap is only a *hot loop* rebuilding the same union. This is the union analogue
of Chapter 92's "don't build `list[int]` in a loop": the *type* is free, the runtime *object* that represents it
costs to construct, so construct it once. (A tuple `(int, str)` is also fine and needs no `|`; either the
precomputed union or the tuple avoids the inline cost.)

---

## 93.3 Measurement: precomputed vs tuple vs inline

**Methodology.** `code/ch093/bench_union.py`. `isinstance` against a precomputed union, an `(int, str)` tuple,
and an inline `int | str`. `min` per call; ratios relative to the precomputed union. CPython 3.13.5, Apple M3
Pro, macOS 27.0, arm64.

| `isinstance(5, ...)` | min per call | ratio |
|---|---|---|
| precomputed union | **9.9 ns** | 1.00x |
| `(int, str)` tuple | **18.8 ns** | 1.90x |
| inline `int | str` | **37.6 ns** | **3.80x** |

The **precomputed** union is fastest at **9.9 ns**, the union object already exists and the check is efficient. A
**tuple** is **1.9x** that. The **inline** union is **3.8x** the precomputed one (and ~2x the tuple), because it
*builds a fresh union object every call* before checking, the construction, not the check, is the cost. So the
same logical test, "is `x` an `int` or `str`", costs 4x more written the natural inline way than with the union
hoisted out.

The rule: **for repeated runtime type checks, precompute the union (or use a tuple); reserve inline `X | Y` for
annotations and one-off checks.** In annotations, write `int | str` freely, it is the clearest syntax and costs
nothing at runtime (deferred, or evaluated once). In a *hot `isinstance` loop*, hoist the union to a constant and
gain ~4x. The measurement is the same Deep I refrain: the *type-level* union is free; the *runtime object* costs
to build, so build it once. Do not let the convenience of `isinstance(x, int | str)` become a per-iteration
allocation.

---

## 93.4 Edges and failure modes

**Reading `Optional` as "optional argument".** §93.1. `Optional[X]` is `X | None` (a type), not a default. Make a
parameter optional with a default value; use `Optional`/`| None` for the type.

**Inline union in a hot `isinstance` loop.** §93.2. Rebuilds the union per call (3.8x). Precompute it as a
constant, or use a tuple.

**Forgetting to handle `None`.** A `X | None` value can be `None`, and using it as an `X` without checking is the
classic `AttributeError: 'NoneType' has no attribute ...`. The checker flags an unguarded use; handle the `None`
branch explicitly (narrow with `if x is not None:`).

**Over-broad unions.** A parameter typed `int | str | bytes | None | list` accepts almost anything and conveys
little; it often signals a design that should be split or use a Protocol/overload. Keep unions small and
meaningful.

**`X | Y` before 3.10 in runtime position.** The `|` operator on types is 3.10+; on older versions it works only
in *deferred* (string) annotations or via `Union`. For runtime `isinstance` on old versions, use a tuple.

**Union of a type and its subclass.** `int | bool` is redundant (`bool` is an `int` subclass), and some unions
collapse or narrow surprisingly. Know your type relationships; a union of overlapping types may not mean what you
expect.

---

## 93.5 Connections

**Backward.** The `types.UnionType`/`GenericAlias` construction cost parallels Chapter 92's subscription. `None`
handling and narrowing connect to `match` (Chapter 15) and truthiness (Chapter 6). Deferred annotations (why
annotation unions are free) are Chapter 12. The `isinstance` object-model check is Chapter 4.

**Forward.** Discriminated (tagged) unions using `Literal` discriminators (Chapter 90) for efficient narrowing,
`overload` for signature-level unions, and exhaustiveness checking are the rest of **Deep I**. `match` statement
narrowing over unions is Chapter 15.

**Across books.** Unions and `Optional` are how Book II types "this may be absent or one of several shapes" at the
boundaries into **Book III**. A **Book III** API types a nullable field as `X | None` and a polymorphic payload
as a discriminated union the checker narrows, handling each branch, and its hot validation paths precompute any
runtime union checks rather than rebuilding them per record. The §93.1 `Optional`-means-`None` clarity and the
§93.2 inline cost are both places sloppy union handling leaks bugs or overhead, which **Deep U** guards against at
the schema seam.

---

## 93.6 Exercises

**1. Prove the equivalences.** Reproduce §93.1: show `int | str == Union[int, str]` and `Optional[int] == int |
None`, and that a union works in `isinstance`. Explain what `Optional` does and does not mean.

**2. Measure the inline cost.** Run §93.3's benchmark and confirm the inline union is slower than a precomputed
one (and a tuple). Explain that the cost is constructing the union, not checking it.

**3. Precompute a union.** Take a hot loop doing `isinstance(x, int | str)` and hoist the union to a constant,
showing the speedup. Explain when this matters and when it does not.

**4. Handle the None.** Write a function taking `X | None`, use the value unguarded (checker flags it), then
narrow with `if x is not None:` and show it type-checks. Explain the narrowing.

**5. The design question.** `X | Y` is both a static annotation and a runtime object, unlike most typing
constructs. Argue the benefits and the cost that duality creates. Your answer must use the §93.3 measurement, the
`Optional`-is-`None` clarification, and the precompute rule.

---

## 93.7 Summary and cross-references

- **`X | Y`** (PEP 604, 3.10+) is a union, equal to **`Union[X, Y]`**; **`Optional[X]`** is **`X | None`** (a
  type that may be `None`), *not* an optional argument.
- A union is a **real runtime object**: `isinstance(x, int | str)` works, and it **narrows** in the checker
  (inside `isinstance` branches).
- **Measured:** a **precomputed** union isinstance is fastest (9.9 ns); an **inline** `int | str` is **3.8x**
  slower because it *builds the union object every call*, the cost is construction, not the check. A tuple sits
  between.
- **Use `X | Y` freely in annotations** (free/once); for repeated `isinstance` checks **precompute the union**
  (or use a tuple); always handle the `None` branch of `X | None`.

**Cross-references.** Runtime type objects (`GenericAlias`) → Chapter 92. Narrowing and `match` → Chapter 15.
Deferred annotations → Chapter 12. `isinstance`/object model → Chapter 4. Discriminated unions, `overload`,
exhaustiveness → the rest of Deep I. The schema seam → Deep U.
