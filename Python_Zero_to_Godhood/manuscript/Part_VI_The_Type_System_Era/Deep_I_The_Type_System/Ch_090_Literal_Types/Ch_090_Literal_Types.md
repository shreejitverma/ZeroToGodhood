# Chapter 90: `Literal` Types

A function takes a mode flag, `"r"`, `"w"`, or `"a"`, and you want the type checker to reject `open_file("x")`
before it runs. `Literal["r", "w", "a"]` does exactly that: it constrains the parameter to those *exact* values,
statically. But like every annotation (Chapter 86), it is *erased* at runtime, a `Literal["r"]` value is a plain
`str`, and `set_mode("x")` *runs fine* at runtime (the checker rejects it; the interpreter does not). The
alternative, an `Enum`, creates *real runtime members* that the interpreter *does* enforce (`Mode("x")` raises),
that you can iterate, compare by identity, and attach behavior to, at a cost: passing an `Enum` member and
reaching its value through `.value` is **2.98x** a plain `Literal` string (85 ns versus 28 ns). So `Literal` and
`Enum` are two answers to "restrict this to a fixed set", one static and free, one runtime and costed.

This chapter continues **Deep I** with `Literal` types: static value-restriction at zero runtime cost, and the
`Enum` contrast that decides which to use. It connects the erasure of Chapter 86 to the runtime enumerations of
Chapter 38.

## Section index

- **90.1** A fixed value-set, static-only
- **90.2** `Literal` vs `Enum`
- **90.3** Measurement: free literal vs runtime member
- **90.4** Edges and failure modes
- **90.5** Connections
- **90.6** Exercises
- **90.7** Summary and cross-references

Listings live under `code/ch090/` and are re-executed by `make verify` on both interpreters.

---

## 90.1 A fixed value-set, static-only

```python
# code/ch090/l01_literal.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a Literal value is a plain str at runtime (erased) ---
  type of a Literal['r'] : str
  equals the plain str   : True
--- the runtime does NOT enforce the Literal set ---
  set_mode('w') (valid)  : 'opened w'
  set_mode('x') (invalid): 'opened x'  (runtime accepts it; the checker rejects it)
--- an Enum creates real runtime members ---
  Mode.W                 : Mode.W
  Mode.W.value           : 'w'
  isinstance(Mode.W, Mode): True
  runtime-enforced: Mode('x') raises : True
  iterable members       : ['R', 'W', 'A']
--- the rule ---
  Literal: a small fixed value-set, static-only, zero runtime cost
  Enum: real members (identity, .value, iteration, runtime-enforced), at a cost
```

A `Literal["r"]` value is a plain `str`: its `type` is `str`, it equals `"r"`, there is no wrapper. The
annotation exists for the *checker*, which verifies that only `"r"`, `"w"`, or `"a"` flow into a `Literal["r",
"w", "a"]` parameter, and rejects `set_mode("x")` *statically*. At *runtime*, the annotation is gone: `set_mode("x")`
returns `"opened x"` happily, because the interpreter never checks the literal set. Static restriction, zero
runtime enforcement, exactly the erasure of Chapter 86.

The `Enum` block is the contrast. `Mode.W` is a *real object*: a distinct member with an identity, a `.value`
(`"r"`), `isinstance(Mode.W, Mode)` is `True`, the set is *iterable* (`[m.name for m in Mode]`), and, crucially,
the runtime *enforces* it, `Mode("x")` *raises* `ValueError`. The `Enum` gives at runtime what the `Literal`
gives only statically.

---

## 90.2 `Literal` vs `Enum`

Both express "one of a fixed set", and they differ on *where the restriction lives* and *what the value is*.

A **`Literal`** is a *static* constraint over a *plain value*. It costs *nothing* at runtime (the value is just a
`str`/`int`/`bool`), the value *is* the underlying literal (no `.value` to unwrap), and it is trivial to write
(`Literal["r", "w", "a"]`). What it does *not* give: any *runtime* guarantee (invalid values pass at runtime),
iteration over the set, identity comparison, or behavior. It is documentation-plus-static-check over a raw value.

An **`Enum`** (Chapter 38) is a *runtime* set of *distinct members*. It *enforces* the set at runtime (constructing
an invalid member raises), supports *iteration* (loop over all members), *identity* comparison (`x is Mode.W`),
`match` exhaustiveness, and *behavior* (methods, `@property`). The cost is that members are *objects* (you reach
the raw value via `.value`), and passing/using them is more expensive (§90.3), and it is more ceremony to define.

The rule: **use a `Literal` for a small fixed value-set where static checking suffices and the value is naturally
a raw `str`/`int`, a mode flag, an HTTP method, an on/off string, a discriminator field, and you want zero runtime
cost.** Use an **`Enum`** when you need *runtime* enforcement (reject invalid values as they arrive), *iteration*
over the members, *identity* comparison, `match` exhaustiveness, or member *behavior*. A quick test: *does the
runtime need to know the set?* If only the *checker* needs it (internal code passing known-good literals),
`Literal` is free and sufficient; if the *runtime* must validate, enumerate, or dispatch on the set (external
input, a menu of options), an `Enum` earns its cost. `Literal` is also ideal for *discriminated unions* (a
`type: Literal["circle"]` field the checker uses to narrow a union), where the value is data, not a runtime
object.

---

## 90.3 Measurement: free literal vs runtime member

**Methodology.** `code/ch090/bench_literal.py`. A function taking a `Literal` string versus one taking an `Enum`
member (and reading `.value`). `min` per call; ratio relative to the `Literal`. CPython 3.13.5, Apple M3 Pro,
macOS 27.0, arm64.

| a fixed-set parameter | min per call | ratio |
|---|---|---|
| `Literal` (plain str) | **28.4 ns** | 1.00x |
| `Enum` (member.value) | **84.7 ns** | **2.98x** |

The `Literal` path costs **28 ns**, exactly a plain-`str` function call, because the `Literal` value *is* a
`str`. The `Enum` path costs **85 ns**, **3x** more, because the argument is a member *object* and reaching its
underlying value goes through a `.value` attribute access, plus the member carries object overhead the raw string
does not. So the runtime enforcement and members of an `Enum` are paid for; the `Literal`'s static-only
restriction is free.

The rule: **`Literal` is the cheaper choice when only static checking is needed; pay for an `Enum` when the
runtime needs the set.** Because a `Literal` is erased to a plain value, it adds nothing to a hot path, a
discriminator field checked millions of times, a mode flag threaded through calls, costs the same as passing the
raw value. An `Enum` is worth its 3x precisely when you use its runtime powers (validation, iteration, identity,
`match`); using an `Enum` merely to restrict a value that only the *checker* needs to constrain pays for
capabilities you do not use. This is the third face of Chapter 86's erasure in Deep I (after `NewType` and
`TypedDict`): the static-only construct is free because it is erased, and you spend on a runtime construct only
when the runtime genuinely needs it.

---

## 90.4 Edges and failure modes

**Expecting a `Literal` to be enforced at runtime.** §90.1. It is not; an invalid value passes at runtime. For
runtime enforcement (external input), use an `Enum`, or validate against the allowed set explicitly.

**`Literal` over a large or open set.** `Literal` is for a *small, closed, known* set of values written in the
annotation. A large set is unwieldy, and an *open* or data-driven set cannot be a `Literal` (it must be
constants). Use an `Enum` or a runtime container for those.

**Needing iteration or identity.** You cannot iterate the values of a `Literal` (they are not a runtime
collection) or compare by identity meaningfully (they are plain values). If you need "all the modes" or `x is
SOME_MODE`, use an `Enum`.

**`Literal` for a discriminated union, done wrong.** A discriminated union relies on each variant having a
*distinct* `Literal` discriminator (`type: Literal["circle"]` vs `Literal["square"]`) so the checker can narrow.
Reusing a discriminator value across variants, or using a non-literal type, breaks the narrowing.

**Mixing `Literal` and `Enum` types.** A `Literal["r"]` (a str) and `Mode.R` (an Enum member) are *different*
types; they do not compare equal (`"r" != Mode.R`, though `"r" == Mode.R.value`). Do not mix the two
representations for the same concept; pick one.

**`IntEnum`/`StrEnum` blurring the line.** `StrEnum` members *are* strings (Chapter 38), which can look like a
`Literal` str but still carry Enum machinery and cost. Know which you have; a `Literal` is a *plain* value, a
`StrEnum` member is an Enum that also is-a str.

---

## 90.5 Connections

**Backward.** `Literal`'s zero runtime cost is Chapter 86's erasure (like `NewType` Chapter 87 and `TypedDict`
Chapter 89). The `Enum` contrast is Chapter 38 (members, iteration, the IntEnum footgun). `match` narrowing on a
`Literal`/`Enum` is Chapter 15.

**Forward.** Discriminated (tagged) unions built on `Literal` discriminators, `overload` resolution using
`Literal` arguments, and the rest of the static toolkit are the rest of **Deep I**. Runtime validation of a
value against an allowed set (`pydantic` with `Literal`) is a Deep I/Deep O boundary concern.

**Across books.** `Literal` is how Book II constrains the small fixed flags and discriminators that flow to
**Book III** without runtime cost. A **Book III** request schema uses `Literal["json", "text"]` for a format
flag and `Literal["gpt", "claude"]` discriminators the checker narrows on, free at runtime, while using an
`Enum` where the *runtime* must enumerate or validate a set (a menu the user picks from, validated at the
boundary). The §90.1 non-enforcement is why external-facing sets are `Enum`s (or validated) and internal
known-good flags are `Literal`s, which **Deep U** applies at the request seam.

---

## 90.6 Exercises

**1. See the erasure.** Reproduce §90.1: pass a valid and an invalid value to a `Literal` parameter and show both
run at runtime, while a checker flags the invalid one. Explain where the restriction lives.

**2. Contrast with Enum.** Show an `Enum` enforcing its set at runtime (`Mode("x")` raises), iterating its
members, and comparing by identity, none of which a `Literal` does. Explain the runtime-member difference.

**3. Measure the cost.** Run §90.3's benchmark and confirm the `Literal` path is cheaper than the `Enum` path.
Explain the `.value` access and member overhead.

**4. Choose the tool.** For several cases (an internal mode flag, a user-selected option validated at input, a set
you iterate, a discriminated-union tag), pick `Literal` or `Enum` and justify each with the "does the runtime need
the set?" test.

**5. The design question.** `Literal` restricts values statically at zero cost; `Enum` restricts at runtime with
members, at a cost. Argue when each is right. Your answer must use the §90.3 cost, the runtime-enforcement
difference, and Chapter 86's erasure.

---

## 90.7 Summary and cross-references

- **`Literal["r", "w", "a"]`** constrains a value to those exact literals for the **static checker**, while at
  runtime the value is a **plain `str`/`int`** (erased, Chapter 86), the runtime does **not** enforce the set
  (an invalid value passes).
- An **`Enum`** creates **real runtime members** (identity, `.value`, iteration, runtime-enforced, `match`,
  behavior), at a cost.
- **Measured:** a `Literal` parameter is **3x** cheaper than an `Enum` member (28 ns vs 85 ns), because the
  `Literal` is a plain value and the `Enum` is an object reached via `.value`.
- **Use `Literal`** for a small fixed value-set needing only static checking (flags, discriminators), free at
  runtime; use an **`Enum`** when the runtime must enforce, enumerate, or dispatch on the set. Test: *does the
  runtime need the set?*

**Cross-references.** Erasure → Chapter 86; `NewType` → Chapter 87; `TypedDict` → Chapter 89. `Enum` → Chapter 38.
`match` narrowing → Chapter 15. Discriminated unions, `overload` → the rest of Deep I. `pydantic` validation →
Deep I, Deep O. The request seam → Deep U.
