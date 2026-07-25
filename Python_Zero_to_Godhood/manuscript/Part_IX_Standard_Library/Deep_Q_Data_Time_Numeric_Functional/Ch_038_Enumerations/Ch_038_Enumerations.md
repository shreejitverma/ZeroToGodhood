# Chapter 38: Enumerations

A codebase represents HTTP statuses as bare integers, `if response == 200`, and reads cleanly until a
subtle bug: somewhere a status of `200` is compared against a *quantity* of `200`, and the comparison
passes because both are just `int`. The intended fix is an enum: `class Status(IntEnum): OK = 200`, which
names the constant and, the folklore says, is safer. Except `IntEnum` inherits the exact footgun it was
meant to fix, `Status.OK == 200` is `True`, and `isinstance(Status.OK, int)` is `True`, so an `IntEnum`
member is still an integer and still compares equal to any integer with its value. The genuinely safe
choice is a plain `Enum`, where `Color.RED == 1` is `False` and members are a closed, self-documenting
type that only compares equal to themselves.

That distinction, and it is a correctness distinction, is the spine of this chapter. Paired with it is a
performance fact that surprises people: the three ways to reach an enum member are not equally cheap.
Attribute access `Color.RED` is **11 ns**, but *value lookup* `Color(1)`, the operation you use to decode
a wire value into a member, is **13x slower** at 149 ns, because it routes through the enum machinery and
a value-to-member map. This chapter, part of **Deep Q**, is the working reference for choosing an enum
base and for knowing which lookup you are paying for.

## Section index

- **38.1** Named singletons, and the `IntEnum` footgun
- **38.2** Three lookups, three costs
- **38.3** Measurement: attribute vs name vs value lookup
- **38.4** Edges and failure modes
- **38.5** Connections
- **38.6** Exercises
- **38.7** Summary and cross-references

Listings live under `code/ch038/` and are re-executed by `make verify` on both interpreters.

---

## 38.1 Named singletons, and the `IntEnum` footgun

```python
# code/ch038/l01_enum.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- members are singletons: identity works ---
  Color.RED is Color.RED : True
  Color(1) is Color.RED  : True
  Color['RED'] is RED    : True
--- Enum vs IntEnum: the equality footgun ---
  Color.RED == 1         : False
  Status.OK == 200       : True
  isinstance(Status.OK,int): True
--- auto() assigns values; the member remembers name and value ---
  Color.GREEN            : <Color.GREEN: 2>
  .name / .value         : GREEN / 2
--- Flag: combinable bit-sets ---
  Perm.R | Perm.W        : Perm.R|W
  Perm.R in (R|W)        : True
  Perm.X in (R|W)        : False
```

An `Enum` turns a set of related constants into a *type* whose members are **named singletons**. There is
exactly one `Color.RED` object, so `Color.RED is Color.RED`, and reaching the same member three ways
(attribute, value lookup, name lookup) returns the *same* object, which is why `is` works everywhere. This
is the first value of an enum over bare constants: the set is closed (only `RED`, `GREEN`, `BLUE` exist),
self-documenting (the member repr is `<Color.GREEN: 2>`, not `2`), and safe to compare by identity.

The `IntEnum` block is the correctness warning. A plain `Enum` member is *not* its value: `Color.RED == 1`
is `False`, because `Color.RED` is a `Color`, not an `int`. But an `IntEnum` member *is* an `int` (it
subclasses `int`), so `Status.OK == 200` is `True` and `isinstance(Status.OK, int)` is `True`. That is
sometimes what you want (drop-in compatibility with code and APIs that expect raw integers, which is why
`http.HTTPStatus` is an `IntEnum`), but it reintroduces the very confusion, an enum comparing equal to a
plain integer, that motivated the enum. **Default to plain `Enum`**; reach for `IntEnum` only when you
genuinely need the member to *be* an integer for interop, and know you have traded type safety for it.

`auto()` assigns values so you do not hand-number members, and `Flag` (with `auto()` powers of two)
supports combinable bit-sets: `Perm.R | Perm.W` is a valid combined member, and `in` tests membership.

---

## 38.2 Three lookups, three costs

There are three ways to reach a member, and they cost differently:

- **`Color.RED`** (attribute access) is the member sitting as a class attribute; it is a plain attribute
  lookup, the fastest.
- **`Color['RED']`** (name lookup) indexes the enum's `_member_map_` by name; a dict lookup plus the
  `__getitem__` dispatch.
- **`Color(1)`** (value lookup) is the decode operation, value to member. It goes through
  `EnumType.__call__` and the `_value2member_map_`, and is the slowest, because calling the class is a
  heavier path than an attribute access.

The one that matters for performance is `Color(value)`, because it is exactly what you do in a hot decode
loop: read an integer off the wire or out of a database column and turn it into a member. §38.3 measures
how much heavier it is, and the answer, 13x, is enough to matter when it is per-message.

---

## 38.3 Measurement: attribute vs name vs value lookup

**Methodology.** `code/ch038/bench_lookup.py`. The three member-access forms on a three-member `Enum`.
`min` per call; ratios within one interpreter. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| access | min per call | ratio |
|---|---|---|
| `Color.RED` (attribute) | **11.5 ns** | 1.00x |
| `Color['RED']` (name) | **29.1 ns** | **2.5x** |
| `Color(1)` (value) | **149.0 ns** | **12.9x** |

Attribute access is **11.5 ns**, essentially a class-attribute lookup. Name lookup is **2.5x** that, a
dict indexing through `__getitem__`. Value lookup, `Color(1)`, is **12.9x** the attribute cost at
**149 ns**, because it invokes the enum metaclass's `__call__`, which checks the value-to-member map and
handles the member-vs-new-value cases. None of these is *slow* in absolute terms, but the 13x spread means
the pattern "decode a wire integer to a member with `Color(x)` on every message" costs meaningfully more
than the constant-time feel of `Color.RED` suggests.

The lesson: know which lookup you are on. For a hot decode path, either accept the value-lookup cost
knowingly, or hoist it, build your own `{value: member}` dict once and index it (a plain dict lookup is
faster than `Color(value)`), or restructure so the member is reached by attribute. As always in Deep Q,
the fix is matching the access pattern to its real cost, not assuming all three forms are the same.

---

## 38.4 Edges and failure modes

**`IntEnum` compares equal to `int`.** §38.1. `Status.OK == 200` is `True`, and two different `IntEnum`
members with the same value compare equal across enums. This defeats the type safety of an enum. Use plain
`Enum` unless integer interop is required; consider `StrEnum` (3.11) for the string analogue with the same
caveat.

**Value lookup is the expensive form.** §38.3. `Color(x)` is ~13x an attribute access. On a hot decode
path, cache a `{value: member}` map instead of calling the enum per item.

**Aliases collapse silently.** Two members with the *same* value are not two members: the second becomes an
*alias* of the first (`Color(1)` returns whichever was defined first). If distinct members must have
distinct values, decorate with `@enum.unique` to turn a duplicate into an error at class-definition time.

**`auto()` values are not a stable wire format.** `auto()` assigns `1, 2, 3, ...` by definition order, so
reordering or inserting members changes the numbers. Never persist `auto()` values or send them on a wire;
assign explicit values for anything that crosses a boundary or a version.

**Mutating or subclassing an enum with members.** An `Enum` with members cannot be subclassed (a deliberate
restriction, extension would break the closed set), and members cannot be added after class creation. Model
the full set at definition time.

**`Flag` with non-power-of-two values.** `Flag` members must be powers of two (use `auto()`); assigning
overlapping bit values makes combinations and `in` tests behave surprisingly. Let `auto()` assign the bits.

---

## 38.5 Connections

**Backward.** The singleton identity that makes `is` work on members is the object-identity model of
Chapter 4 and **Deep A**. The metaclass (`EnumType`/`EnumMeta`) that builds the member map and intercepts
`Color(x)` is Chapter 31 (metaclasses), enum is the standard library's flagship metaclass. The `auto()` and
member-definition machinery uses the descriptor protocol of Chapter 4.

**Forward.** `match` statements over enum members (exhaustive, readable dispatch) are Chapter 15. Type
checkers use `Enum` for exhaustiveness checking, the typing angle is Chapter 16. Serializing enums across a
boundary (by value, with an explicit stable mapping) is **Deep R**.

**Across books.** Enums are how Book II names the closed sets that cross into **Book III**: a message kind,
a model state, a routing decision. A **Book III** pipeline decodes a wire integer to an enum member at
ingest, and because §38.3 showed `Color(x)` is the expensive lookup, the hot decoders cache a value-to-
member map. The closed-set, singleton, `match`-friendly nature of enums is what makes the cross-boundary
protocol both safe and exhaustively checkable. **Deep U** owns the protocol seam.

---

## 38.6 Exercises

**1. Expose the IntEnum footgun.** Define an `IntEnum` and a plain `Enum` with the same values. Show that
the `IntEnum` member compares equal to a bare integer and the plain `Enum` member does not. Then show two
different `IntEnum` classes whose members compare equal by value, and explain why this defeats the enum's
purpose.

**2. Measure the lookups.** Reproduce §38.3's benchmark and confirm the attribute/name/value ordering.
Then build a `{value: member}` dict and show that indexing it is faster than `Color(value)`. Explain what
`Color(value)` does that the dict lookup skips.

**3. Catch a duplicate.** Define an enum with two members sharing a value and show the second is an alias.
Then add `@enum.unique` and show it becomes an error. Explain when you want aliases and when you want
`@unique`.

**4. Build a Flag.** Model a permission set with `Flag` and `auto()`, combine members with `|`, and test
membership with `in`. Then assign a non-power-of-two value to a member and show a combination misbehaves.
Explain why `Flag` values must be powers of two.

**5. The design question.** Python offers plain `Enum`, `IntEnum`, `StrEnum`, and `Flag` rather than one
enum type. Argue why. Your answer must address the safety cost of `IntEnum`/`StrEnum` comparing equal to
their raw types, when that interop is worth the lost type safety, and why the default should be the plain
`Enum` that only compares equal to itself.

---

## 38.7 Summary and cross-references

- An **`Enum`** turns related constants into a type of **named singletons**: the set is closed, self-
  documenting, and safe to compare with `is`. Reaching a member three ways returns the same object.
- **Default to plain `Enum`.** An **`IntEnum`** member *is* an `int` (`Status.OK == 200` is `True`), which
  reintroduces the integer-confusion the enum was meant to prevent; use it only for genuine integer interop.
- **Measured:** the three member accesses cost differently, `Color.RED` (attribute) **11.5 ns**,
  `Color['RED']` (name) **2.5x**, `Color(1)` (value) **12.9x**. Value lookup is the decode operation and
  the expensive one; cache a `{value: member}` map on hot paths.
- **Edges:** duplicate values become silent aliases (use `@unique`); `auto()` values are not a stable wire
  format; enums with members cannot be subclassed.

**Cross-references.** Object identity → Chapter 4 and Deep A. The enum metaclass → Chapter 31. `match` over
members → Chapter 15. Typing and exhaustiveness → Chapter 16. Serialization → Deep R. The protocol seam →
Deep U.
