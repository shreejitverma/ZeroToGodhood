# Chapter 35: Numbers - `float`, `Decimal`, `Fraction`

`0.1 + 0.2` is not `0.3`. Every Python programmer meets this eventually, usually as a failing test or a
customer complaint about a penny, and the reflex explanation is "floating point is broken." It is not
broken; it is *binary*. A `float` is an IEEE 754 double, a binary fraction, and `0.1` has no exact binary
representation any more than `1/3` has an exact decimal one, so `0.1 + 0.2` produces `0.30000000000000004`
and the equality fails. That is not a bug to be worked around with `round`; it is a contract to be
understood, and the standard library gives you two exact alternatives when the contract does not fit:
`Decimal` (exact decimal arithmetic) and `Fraction` (exact rational arithmetic). Both are correct where
`float` is not, and both are measurably slower: in this chapter's benchmark, `Decimal` is **8.6x** and
`Fraction` **59x** slower than `float` for the same arithmetic.

But the folklore has a second, staler layer worth correcting, because it drives real code. "Python's
`sum()` accumulates floating-point error, so always use `math.fsum`." That was true once. Since Python
3.12, the builtin `sum()` uses Neumaier compensated summation for floats, and on the same wide-range
input where a hand-written `t += v` loop returns **-1.0**, `sum()` returns **0.0** and `math.fsum`
returns the exact **1e-16**. The naive loop still drifts; the builtin no longer does, mostly. This
chapter, part of **Deep Q**, is the working reference for choosing a number type and for summing floats
correctly on a modern interpreter.

## Section index

- **35.1** Three number types, three contracts
- **35.2** Summation: naive fold vs `sum()` vs `math.fsum`
- **35.3** Measurement: what exactness costs
- **35.4** Edges and failure modes
- **35.5** Connections
- **35.6** Exercises
- **35.7** Summary and cross-references

Listings live under `code/ch035/` and are re-executed by `make verify` on both interpreters.

---

## 35.1 Three number types, three contracts

```python
# code/ch035/l01_numerics.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- float: binary IEEE 754, not exact for decimal fractions ---
  0.1 + 0.2            : 0.30000000000000004
  0.1 + 0.2 == 0.3    : False
--- Decimal: exact decimal arithmetic ---
  D('0.1')+D('0.2')   : 0.3
  == D('0.3')         : True
  1/7 at prec=6       : 0.142857
--- Fraction: exact rational, no rounding at all ---
  F(1,10)+F(2,10)     : 3/10
  == F(3,10)          : True
  (1/3)*3 exactly     : 1
--- float summation: naive fold vs sum() vs math.fsum ---
  values              : [1.0, 1e-16, 1e+16, -1e+16, -1.0]
  exact answer        : 1e-16
  naive t += v fold   : -1.0
  builtin sum()       : 0.0
  math.fsum()         : 1e-16
```

**`float`** is an IEEE 754 double: fast (it runs on the hardware FPU), fixed 53-bit precision, and
*binary*, so any value that is not a sum of powers of two (`0.1`, `0.2`, `0.3`) is stored as the nearest
representable double and is not exact. This is the right type for science, graphics, and machine learning,
where inputs are approximate and speed dominates; it is the wrong type for money.

**`Decimal`** is exact decimal arithmetic with a precision and rounding mode *you* control (a global
`getcontext()`, or a local `localcontext()`). `Decimal("0.1") + Decimal("0.2")` is exactly `Decimal("0.3")`,
because the arithmetic is done in base ten. Note the string constructor: `Decimal("0.1")` is exact, but
`Decimal(0.1)` inherits the float's binary error (it constructs from the already-imprecise double). Use
`Decimal` for money, tax, and billing, anywhere a result must match hand-calculated decimal arithmetic to
the cent.

**`Fraction`** is exact rational arithmetic: a numerator and denominator, both arbitrary-precision
integers, with *no rounding at all*. `Fraction(1, 3) * 3` is exactly `1`, which no `float` or fixed-
precision `Decimal` can promise. Use `Fraction` where you need exact ratios (exact probabilities, unit
conversions, symbolic coefficients) and can afford the cost §35.3 measures.

---

## 35.2 Summation: naive fold vs `sum()` vs `math.fsum`

The last block of the listing is the chapter's folklore correction, and it has three rungs on the same
wide-range input `[1.0, 1e-16, 1e16, -1e16, -1.0]`, whose exact sum is `1e-16`:

- **Naive fold** (`t = 0.0; for v: t += v`) returns **-1.0**. Adding `1e16` swamps the `1.0` and `1e-16`
  terms (they fall below the ULP at that magnitude and vanish), and subtracting `1e16` leaves the `-1.0`,
  so the small terms are lost entirely. This is the loop everyone writes, and it is wrong.
- **Builtin `sum()`** returns **0.0**. Since Python 3.12 (What's New for 3.12; gh-100425), `sum()` uses
  Neumaier compensated summation for floats: it carries a running correction term for the low-order bits
  each addition discards. That recovers the `1.0` terms (which cancel to 0) but not the `1e-16` term,
  which is below the resolution of a *single* compensation word at the `1e16` magnitude. Far better than
  the naive fold, not exactly rounded.
- **`math.fsum()`** returns the exact **1e-16**. It uses Shewchuk's algorithm, tracking multiple partial
  sums, and is *exactly rounded*: its result is the correctly-rounded value of the true sum, always.

The practical reading: the old advice "always use `math.fsum`" is now overkill for most code, because the
builtin `sum()` is already compensated on 3.12+. But two things remain true. A hand-written accumulation
loop is *not* compensated, so if you write `t += v` yourself, you still drift, use `sum()` or `math.fsum`
instead. And when you need a guaranteed exactly-rounded result over pathological dynamic range, `math.fsum`
is still the only builtin that delivers it. In 200,000 random wide-range trials (§35.1's harness), `sum()`
and `math.fsum` never disagreed; the divergence appears only on adversarially-scaled inputs like this one.

---

## 35.3 Measurement: what exactness costs

**Methodology.** `code/ch035/bench_decimal.py`. A fixed arithmetic workload, a 50-term sum of squares,
computed under each number type. `min` per call over repeated batches; ratios within one interpreter.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| type | min per call | ratio |
|---|---|---|
| `float` | **495 ns** | 1.00x |
| `Decimal` | **4265 ns** | **8.6x** |
| `Fraction` | **29,458 ns** | **59.5x** |

`float` is fastest by a wide margin because each operation is a single hardware FPU instruction.
`Decimal` is **8.6x** slower: it is exact decimal arithmetic implemented in C (the `_decimal`
accelerator), and the exactness costs a large constant factor even in C, because each operation
manipulates a variable-length decimal coefficient rather than a fixed 64-bit register. `Fraction` is
**59.5x** slower: it is pure Python over arbitrary-precision integers, and every operation must combine
two numerator/denominator pairs and reduce the result to lowest terms (a `gcd` per operation).

The decision this measures is not "which is fastest" (float always is) but *which contract the problem
requires*, and then whether you can afford it:

- **`float`** where representation error is acceptable and speed matters: numerics, ML, graphics, physics.
- **`Decimal`** where decimal exactness is a correctness requirement: money, tax, billing, any figure a
  human will reconcile against a hand calculation. The 8.6x is almost always worth it at money's data
  rates; you are not summing a billion invoices per second.
- **`Fraction`** where you need exact rationals and no rounding at all: exact probabilities, unit
  conversions, symbolic ratios. The 59x confines it to low-volume exact work, not hot loops.

The mistake the benchmark guards against is both directions: using `float` for money (a correctness bug
that surfaces as off-by-a-penny), and reaching for `Decimal`/`Fraction` in a numeric hot loop where
`float`'s approximation is fine and the constant factor is pure waste.

---

## 35.4 Edges and failure modes

**`Decimal(0.1)` vs `Decimal("0.1")`.** §35.1. Constructing a `Decimal` from a `float` inherits the
float's binary error (`Decimal(0.1)` is `0.1000000000000000055...`). Construct from a *string* (or an
`int`) to stay exact.

**`float` equality.** §35.1. `a == b` on floats is fragile; `0.1 + 0.2 == 0.3` is `False`. Compare with a
tolerance (`math.isclose(a, b)`), never `==`, for computed floats.

**Hand-written summation loops.** §35.2. `t += v` in a Python loop is *not* compensated (only the builtin
`sum()` is). If you must accumulate manually, use `sum()`, `math.fsum`, or carry your own Kahan
compensation. Do not assume your loop inherits `sum()`'s accuracy.

**`Decimal` global context.** `getcontext().prec` is a global (thread-local) setting; changing it affects
all subsequent `Decimal` arithmetic in the thread. For a local precision change, use `localcontext()` as a
context manager so the change is scoped and reverted.

**`Fraction` denominator blowup.** Exact rationals grow: repeatedly combining fractions with large coprime
denominators produces ever-larger numerator/denominator integers, and the arithmetic slows as those
integers grow. For long chains, convert to `float` or `Decimal` once the exact phase is done.

**`float('nan')` and `float('inf')`.** IEEE 754 special values propagate and break ordering (`nan != nan`,
and `nan` compares false to everything). `Decimal` has its own `Decimal('NaN')`/`Decimal('Infinity')` with
signaling variants. Guard for them when parsing external numeric input.

---

## 35.5 Connections

**Backward.** The object model that makes `int` arbitrary-precision (and `Fraction` build on it) is
**Deep A**; Python's `int` has no fixed width, so `Fraction`'s numerator and denominator never overflow,
they just get slower. The `functools`/`math` toolkit that `math.fsum` belongs to is Chapter 34's
neighbor. The immutability of all three numeric types (every operation returns a new object) is the value-
semantics theme of Chapter 4.

**Forward.** The C-level `_decimal` accelerator and the FPU path for `float` are **Deep A** and **Deep T**
(numerical computing). NumPy's fixed-width `float64`/`int64` arrays, which trade Python's arbitrary
precision for SIMD speed and a *different* set of overflow and precision hazards, are **Deep T**. The
hashing that lets `Decimal` and `Fraction` be dict keys (and compare equal to equal `float`/`int`) is
**Deep P**.

**Across books.** The number-type decision is a correctness boundary Book II enforces before data reaches
**Book III**. A billing or metering seam uses `Decimal` so charges reconcile to the cent; a **Book III**
ML feature pipeline uses `float` (and NumPy `float64`) because the model is approximate and throughput
dominates. Choosing the wrong side, `float` money or `Decimal` feature vectors, is a bug in one direction
and 8.6x waste in the other. **Deep U** owns the seam where the two number worlds meet.

---

## 35.6 Exercises

**1. Reproduce the representation error.** Show `0.1 + 0.2 != 0.3` and explain, in terms of binary
fractions, why. Then show `Decimal("0.1") + Decimal("0.2") == Decimal("0.3")` and explain what changed.
Finally show that `Decimal(0.1) != Decimal("0.1")` and explain the constructor trap.

**2. Compare the three summations.** Run §35.1's summation block and confirm naive fold, `sum()`, and
`math.fsum` give different answers on the wide-range input. Then find (or argue you cannot easily find) an
input where `sum()` and `math.fsum` disagree, and explain why the divergence requires extreme dynamic
range.

**3. Measure the cost.** Reproduce §35.3's benchmark and confirm the ordering (float fastest, then
Decimal, then Fraction). Explain each factor: why Decimal is slower than float even in C, and why Fraction
is slower than Decimal.

**4. Money done right.** Implement a small invoice total that sums line items with tax, once in `float`
(and exhibit a penny error) and once in `Decimal` (and show it reconciles). Explain why `Decimal` is the
correct type here and what `localcontext()` buys you for the rounding step.

**5. The design question.** Python offers three exact-or-fast number contracts rather than one. Argue why
a single number type cannot serve money, science, and exact rationals at once. Your answer must address
the speed/exactness trade-off the §35.3 benchmark measures, why `float`'s binary representation is a
feature for numerics and a bug for money, and when `Fraction`'s denominator growth makes it the wrong
choice despite being the most exact.

---

## 35.7 Summary and cross-references

- **`float`** is a fast binary IEEE 754 double and is *not* exact for decimal fractions (`0.1 + 0.2 !=
  0.3`); compare with `math.isclose`, never `==`.
- **`Decimal`** is exact decimal arithmetic (construct from strings, not floats) for money and billing;
  **`Fraction`** is exact rational arithmetic with no rounding for exact ratios.
- **Measured:** for the same arithmetic, `Decimal` is **8.6x** and `Fraction` **59.5x** slower than
  `float`. Choose by the contract the problem requires, then pay for it.
- **Summation, corrected:** a hand-written `t += v` fold drifts (**-1.0** on the wide-range input), but
  the builtin **`sum()` has used Neumaier compensated summation since 3.12** (**0.0**), and **`math.fsum`**
  is exactly rounded (**1e-16**). Use `sum()` or `math.fsum`, never a naive loop, for float sums.

**Cross-references.** Arbitrary-precision `int` and the object model → Deep A. `math.fsum` and the numeric
toolkit → Chapter 34's neighbor. Value semantics and immutability → Chapter 4. NumPy fixed-width numerics
→ Deep T. Numeric hashing → Deep P. The number-type seam → Deep U.
