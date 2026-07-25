# Chapter 84: Comparing Floats in Tests

Chapter 35 showed that `0.1 + 0.2 != 0.3`, so a test that asserts `result == expected` on computed floats is
already wrong, it fails on values that are equal to within rounding. The usual fix, `assertAlmostEqual`, is a
trap of its own: it uses **absolute** tolerance (7 decimal places by default), which is wrong at *both* ends of
the magnitude scale. It is **too strict for large numbers**: `1e16` and `1e16 + 2` are *adjacent representable
floats*, as close as floats can get at that magnitude, yet `assertAlmostEqual` *rejects* them (their absolute
difference, 2, exceeds `0.5e-7`). And it is **too loose for small numbers**: `1e-10` and `2e-10` differ by a
factor of two, relatively very different, yet `assertAlmostEqual` *accepts* them (both round to ~0 at 7 places).
The correct tool is `math.isclose`, which uses **relative** tolerance that scales with the magnitude and is
right at both extremes. It costs a little more than `==` (2x, ~10 ns), which is nothing per assertion.

This chapter continues **Deep O** with float comparison in tests: why `==` and absolute tolerance both fail, why
relative tolerance is correct, and the small cost of getting it right. It is the testing application of Chapter
35's representation lesson.

## Section index

- **84.1** `==`, absolute, and relative
- **84.2** Why relative tolerance is right
- **84.3** Measurement: the cost of a correct comparison
- **84.4** Edges and failure modes
- **84.5** Connections
- **84.6** Exercises
- **84.7** Summary and cross-references

Listings live under `code/ch084/` and are re-executed by `make verify` on both interpreters.

---

## 84.1 `==`, absolute, and relative

```python
# code/ch084/l01_float_testing.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- == fails on computed floats ---
  0.1 + 0.2 == 0.3          : False
  math.isclose(0.1+0.2, 0.3): True
--- absolute tolerance is too STRICT for large numbers ---
  1e16 and 1e16+2 (as close as floats get here)
  assertAlmostEqual passes  : False  (absolute: wrongly rejects)
  math.isclose passes       : True  (relative: correct)
--- absolute tolerance is too LOOSE for small numbers ---
  1e-10 and 2e-10 (2x apart)
  assertAlmostEqual passes  : True  (absolute: wrongly accepts)
  math.isclose passes       : False  (relative: correct)
```

Three comparison strategies, three behaviors. **`==`** reports `0.1 + 0.2 != 0.3`, correct arithmetically (they
*are* different floats) but wrong as a *test* (they are equal to within rounding). **Absolute tolerance**
(`assertAlmostEqual`, "equal to N decimal places") fails in *both directions*: for `1e16` versus `1e16 + 2`, two
adjacent floats that cannot be closer, the absolute difference (2) exceeds the tolerance, so it *wrongly rejects*
equal-to-float-precision values; for `1e-10` versus `2e-10`, a 2x relative difference, both are below the
tolerance, so it *wrongly accepts* clearly-different values. **Relative tolerance** (`math.isclose`) gets both
right: it passes the large adjacent pair (relatively identical) and fails the small 2x pair (relatively far).

The pattern is that absolute tolerance has a *fixed* threshold that is meaningless without knowing the
magnitude: `0.5e-7` is enormous next to `1e-10` and infinitesimal next to `1e16`. Relative tolerance scales the
threshold *with the values*, which is what "close" means for floating point.

---

## 84.2 Why relative tolerance is right

Floating-point precision is *relative*, not absolute: a `float` has ~15-16 significant *digits*, so the gap
between adjacent representable values (the ULP) grows with the magnitude, tiny near zero, large near `1e16`. So
"how close is close enough" must also scale with the magnitude, which is exactly what relative tolerance does.
`math.isclose(a, b, rel_tol=1e-9)` asks whether `abs(a - b) <= rel_tol * max(abs(a), abs(b))`, the tolerance is a
*fraction* of the values, so it means the same thing (~9 significant digits agree) whether the values are `1e-10`
or `1e16`. Absolute tolerance (`abs(a - b) <= 0.5 * 10**-places`) fixes the threshold regardless of magnitude,
so it is only ever correct in a narrow band around `1.0` and wrong everywhere else.

There is one case where absolute tolerance is *necessary*: comparing against *zero* (or values that legitimately
approach zero), where relative tolerance breaks down (everything is "infinitely far" from 0 in relative terms, so
`math.isclose(x, 0.0)` is `False` for any nonzero `x`). For that, `math.isclose` takes an `abs_tol` parameter:
`math.isclose(x, 0.0, abs_tol=1e-12)` compares against zero with an absolute floor. The general recipe is
*relative tolerance, plus an absolute floor for near-zero*, which is what `math.isclose(a, b, rel_tol=...,
abs_tol=...)` and `pytest.approx` provide.

The rule: **compare computed floats with relative tolerance (`math.isclose`, `pytest.approx`, `numpy.isclose`),
not `==` and not `assertAlmostEqual`'s default absolute tolerance.** Reserve `==` for values that are supposed to
be *exact* (integers, bit-identical results, `Decimal`/`Fraction`, Chapter 35), and add an `abs_tol` only when a
value can be legitimately zero. This makes tests correct across magnitude scales instead of accidentally passing
or failing based on where the numbers happen to sit.

---

## 84.3 Measurement: the cost of a correct comparison

**Methodology.** `code/ch084/bench_isclose.py`. `==` versus `math.isclose` on a pair of nearly-equal floats.
`min` per call; ratio relative to `==`. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| compare two floats | min per call | ratio |
|---|---|---|
| `==` (wrong for floats) | **4.6 ns** | 1.00x |
| `math.isclose` (correct) | **9.6 ns** | **2.09x** |

`math.isclose` is **2x** a `==`, ~10 ns versus ~5 ns, because it computes a relative tolerance (a subtraction, a
`max`, a multiply, a compare) instead of a single equality. In absolute terms it is ~5 nanoseconds more, and it
runs *per assertion* in a test, not in a hot loop, so the cost is utterly irrelevant. And `==` is not a cheaper
*correct* option, it is a cheaper *wrong* one: it gives the wrong answer for computed floats.

The rule: **pay the trivial cost for a correct comparison.** The 2x is nanoseconds per assertion, invisible in a
test suite, and it buys a comparison that is right at any magnitude, where `==` is wrong and absolute tolerance
is wrong at the extremes. This is the same shape as the rest of Deep O: the correct construct costs slightly more
and the small cost is never the reason to choose the incorrect one. For a test, the only thing that matters is
that a pass means the numbers agree to the precision you require, and only relative tolerance delivers that
across scales. Use `math.isclose`/`pytest.approx`, set `rel_tol` to the precision your computation guarantees,
and add `abs_tol` for near-zero.

---

## 84.4 Edges and failure modes

**`==` on computed floats.** §84.1. Fails on values equal to within rounding (Chapter 35). Use relative
tolerance.

**`assertAlmostEqual`'s absolute default.** §84.1. Too strict for large magnitudes, too loose for small. Use
`math.isclose`/`pytest.approx`, or `assertAlmostEqual(..., delta=...)` with a magnitude-appropriate delta only
when you know the scale.

**Relative tolerance against zero.** §84.2. `math.isclose(x, 0.0)` is `False` for any nonzero `x` (relative
tolerance degenerates at zero). Provide `abs_tol` when a value can be zero.

**Comparing `NaN`.** `NaN != NaN`, and `math.isclose(nan, nan)` is `False`. If a computation can produce `NaN`,
test for it explicitly (`math.isnan`); do not expect any comparison to treat `NaN` as equal to itself.

**Accumulated error exceeding the tolerance.** A long computation can accumulate rounding beyond `rel_tol`
(Chapter 35's summation error). If a test legitimately needs a looser tolerance, set `rel_tol` to what the
algorithm actually guarantees, do not tighten it below the computation's real precision, or the test flakes.

**Testing exact values with tolerance.** Integers, `Decimal`, `Fraction`, and bit-exact results *should* use `==`,
using tolerance there hides real bugs (an off-by-one that a tolerance swallows). Use tolerance for *computed
floats*, exact comparison for *exact values*.

---

## 84.5 Connections

**Backward.** The float representation that makes `==` wrong, and the relative nature of float precision, are
Chapter 35. The `Decimal`/`Fraction` exact types that *do* use `==` are Chapter 35. The `math` module is a
standard-library staple.

**Forward.** `pytest.approx` (the pytest idiom, with per-comparison tolerances and collection support) and
`numpy.isclose`/`allclose` (array comparison) are Deep O/Deep T testing tools. Property-based testing of numeric
code (hypothesis) is Deep O. The numerical-stability concerns behind the tolerances are Deep T.

**Across books.** Correct float comparison is how Book II tests the numeric code that carries into **Book III**. A
**Book III** test of a scoring, embedding, or metric computation compares expected and actual with `math.isclose`
/`numpy.allclose` at a tolerance matching the computation's precision, so the test is correct whether the values
are probabilities near zero or large logits, and it does not flake on the last representable bit. The §84.1
magnitude-dependent failures of `==` and absolute tolerance are exactly the flaky-or-false tests that erode trust
in a numeric suite, which **Deep U** guards against, and **Deep T** owns the numerical-stability analysis.

---

## 84.6 Exercises

**1. Show all three.** Reproduce §84.1: compare `0.1 + 0.2` and `0.3` with `==` and `math.isclose`, then show
`assertAlmostEqual` failing for a large adjacent pair and passing for a small far-apart pair. Explain the
absolute-vs-relative difference.

**2. Compare against zero.** Show `math.isclose(x, 0.0)` is `False` for small nonzero `x`, then fix it with
`abs_tol`. Explain why relative tolerance needs an absolute floor near zero.

**3. Measure the cost.** Run §84.3's benchmark and confirm `math.isclose` is ~2x `==` but nanoseconds. Explain
why the cost is irrelevant in a test.

**4. Pick the comparison.** For several assertions (an integer count, a computed probability, a `Decimal` money
value, a large computed sum), choose `==` or `math.isclose` and justify each. Explain why exact values should use
`==`.

**5. The design question.** Float precision is relative, so float comparison should be too. Argue why
`math.isclose`'s relative tolerance is the right default and `assertAlmostEqual`'s absolute tolerance is a trap.
Your answer must use the §84.1 magnitude failures and §84.3 cost, and address the near-zero exception.

---

## 84.7 Summary and cross-references

- **`==` fails on computed floats** (Chapter 35); **absolute tolerance** (`assertAlmostEqual` default) is wrong at
  both extremes, too strict for large magnitudes, too loose for small.
- **Relative tolerance** (`math.isclose`, `pytest.approx`) scales with the values and is correct at any magnitude;
  add **`abs_tol`** for comparisons against zero.
- **Measured:** `math.isclose` is **2x** a `==` (9.6 ns vs 4.6 ns), nanoseconds per assertion, the trivial price
  of a correct comparison; `==` is a cheaper *wrong* answer, not a cheaper correct one.
- **Use relative tolerance for computed floats; `==` for exact values** (integers, `Decimal`, `Fraction`, bit-
  identical). Handle `NaN` explicitly; set `rel_tol` to the computation's real precision.

**Cross-references.** Float representation and exact types → Chapter 35. `pytest.approx`/`numpy.isclose` → Deep O,
Deep T. Numerical stability → Deep T. The numeric-test seam → Deep U.
