# Chapter 79: `assert` and Optimized Mode

A service validates user input with `assert age >= 0, "age must be non-negative"`, passes its tests, and ships.
In production, run under `python -O` for "performance", the check is *gone*: `assert` statements are stripped
entirely in optimized mode, so `age = -5` sails through and corrupts data downstream. This is not a subtle edge
case; it is the single most dangerous misuse of `assert` in Python. An `assert` is compiled to a check only when
`__debug__` is `True`, which is the default but becomes `False` under `-O`, and then every `assert` is removed.
So any validation, security check, or precondition written as `assert` *silently vanishes* in the exact mode
production often uses. And `assert` buys nothing for it: measured, when it *does* run, an `assert` costs the same
as an explicit `if ...: raise` (17.7 ns versus 17.5 ns), so it is not even a faster check, its only difference
is disappearing.

This chapter continues **Deep O** with `assert` and optimized mode: what `-O` strips, why `assert` is for
internal invariants and never for validation, and the measurement showing it is no cheaper than a real check. It
is a debugging-and-correctness chapter with direct security stakes.

## Section index

- **79.1** `assert` disappears under `-O`
- **79.2** Invariants vs validation
- **79.3** Measurement: `assert` is not a cheaper check
- **79.4** Edges and failure modes
- **79.5** Connections
- **79.6** Exercises
- **79.7** Summary and cross-references

Listings live under `code/ch079/` and are re-executed by `make verify` on both interpreters.

---

## 79.1 `assert` disappears under `-O`

```python
# code/ch079/l01_assert_stripping.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- normal mode (__debug__ True): both checks run ---
  assert check: triggered (AssertionError)
  if check: triggered (ValueError)
  __debug__ = True
--- optimized mode (python -O): the assert is STRIPPED ---
  assert check: NOT triggered (age -5 accepted!)
  if check: triggered (ValueError)
  __debug__ = False
--- the rule ---
  assert: internal invariants / debugging assumptions (may be stripped)
  if ...: raise: input validation and security checks (always run)
```

The listing runs the same two checks in two interpreter modes. In **normal mode**, `__debug__` is `True`, and
both the `assert`-based check and the `if`-based check trigger on the bad input `-5`. Under **`python -O`**,
`__debug__` is `False`, and the difference is stark: the `assert` check is **NOT triggered**, the invalid `-5` is
*accepted*, while the `if`-based check still fires. The `assert` was compiled out of the bytecode entirely, as if
the line were deleted; the `if ...: raise` is a normal statement that always runs.

This is exactly the trap. Code that relies on `assert` for a real check passes every test (tests run in normal
mode) and then *fails open* in production under `-O`, the worst kind of failure, silent and only in the
deployed configuration. The `-O` flag (and `-OO`, which also strips docstrings, and the `PYTHONOPTIMIZE`
environment variable) is used precisely where people want "production performance", so the assumption "we never
run with `-O`" is unsafe.

---

## 79.2 Invariants vs validation

The fix is not "never use `assert`", it is to use it for what it is *for*. `assert` documents an **internal
invariant**: a condition the programmer believes is *always* true if the code is correct, "this list is non-empty
here because I just appended", "this branch is unreachable", "this dict has the key because I set it above". Such
an assertion is a *debugging aid* and *executable documentation*: it catches programming errors during
development and states an assumption to the reader, and it is *acceptable* for it to be stripped in an optimized
production run, because if the code is correct, it never fires anyway.

**Validation** is different: checking *external* input (user data, API arguments, file contents, network
messages) that *might* be bad regardless of whether your code is correct. That check must *always* run, in every
mode, because the bad input is a real, expected possibility, not a programming error. Validation, and every
security check (authorization, bounds, sanitization), must be an explicit `if ...: raise` (`ValueError`,
`TypeError`, a domain exception), never an `assert`.

The distinction is *who* the check guards against: `assert` guards against *your own bugs* (and may be turned off
once you trust the code); `if ...: raise` guards against *the world* (and must never be turned off). The rule:
**never use `assert` for anything whose failure a user or attacker can cause; use it only for invariants whose
failure means your code is wrong.** A quick test: if the assertion could fail due to *input* rather than a *bug*,
it must not be an `assert`.

---

## 79.3 Measurement: `assert` is not a cheaper check

**Methodology.** `code/ch079/bench_assert.py`. A passing check written as `assert` versus `if ...: raise`, in
normal mode (so both run). `min` per call; ratio relative to `if-raise`. CPython 3.13.5, Apple M3 Pro, macOS
27.0, arm64.

| a passing check (normal mode) | min per call | ratio |
|---|---|---|
| `if ...: raise` (always runs) | **17.5 ns** | 1.00x |
| `assert` (normal mode) | **17.7 ns** | **1.01x** |

When it runs, an `assert` costs **the same** as the equivalent `if ...: raise`, both evaluate the condition. So
`assert` is *not* a faster way to check; there is no performance reason to prefer it for a check you actually
need. Its *only* performance difference is that `-O` strips it to zero cost, and that "optimization" is exactly
the danger: zero cost *and* zero checking.

The rule the measurement settles: **do not justify `assert`-for-validation as a speed win, there is none.** When
the check must run, `assert` is no cheaper than `if ...: raise`; when `-O` makes `assert` free, it also makes it
absent. So use `assert` only where you are *content for the check to vanish* (an internal invariant that should
never fire in correct code), and use `if ...: raise` for everything that must hold regardless. The tiny cost of a
real check is not worth trading for a validation that disappears in production, and the §79.3 parity shows you
are not even saving anything by doing so. As across the book, the correct construct is not slower; here it is
*identical* in cost and *categorically* safer.

---

## 79.4 Edges and failure modes

**`assert` for input validation or security.** §79.1. Stripped under `-O`, so the check fails open in
production. Use `if ...: raise`. This is the core bug.

**`assert` with a side effect.** An `assert` whose expression *does* something (`assert log.info("x") or True`,
`assert queue.pop()`) changes behavior when stripped, the side effect disappears under `-O`. Never put side
effects in an assertion.

**`assert (cond, "message")` (a tuple).** Writing `assert (x > 0, "msg")` asserts a *non-empty tuple*, which is
always truthy, so it *never fails*. The comma form is `assert x > 0, "msg"` (no parens). The parenthesized tuple
is a silent always-pass bug; linters catch it.

**Assuming tests cover the `-O` behavior.** Tests almost always run in normal mode, so an `assert`-as-validation
passes CI and fails only under `-O` in production. Test the `-O` path, or better, do not depend on `assert` for
anything a test would need to verify runs.

**`-OO` and docstrings.** `-OO` strips `assert` *and* docstrings (`__doc__` becomes `None`), which breaks code
that introspects docstrings (some CLI/help tooling, doctest). Know that optimized mode removes more than asserts.

**Relying on `assert` in library code.** A library cannot control whether its *consumer* runs with `-O`, so a
library that validates its public inputs with `assert` is broken for `-O` users. Libraries must validate with
`if ...: raise`.

---

## 79.5 Connections

**Backward.** The exception raised by a real check (`raise ValueError`) is Chapter 6. The `if`/comparison the
explicit check uses is Chapters 2-3. The security stakes connect to the validation boundary of the Deep O
security chapters (76-78).

**Forward.** Testing (unit tests that assert *in test code*, where `assert` is correct and pytest rewrites it) is
Deep O's testing material, note the distinction: `assert` in a *test* is fine (tests run in normal mode and
frameworks rewrite it); `assert` in *production code for validation* is the bug. Type checking and runtime
validation (`pydantic`, `dataclasses`) are alternatives to hand-written validation. The `-O` flag and bytecode
are Chapter 66 / Deep J.

**Across books.** The invariant-vs-validation distinction is a boundary Book II enforces before untrusted input
reaches **Book III**. A **Book III** service validates every external input (request bodies, model parameters,
tool arguments) with explicit `if ...: raise` (or a schema validator), so nothing depends on `-O` being off,
while using `assert` freely for internal invariants in code paths it controls. The §79.1 fail-open behavior is
exactly the silent production vulnerability, valid in tests, gone in `-O`, that **Deep U** guards against at the
input seam.

---

## 79.6 Exercises

**1. Watch it vanish.** Reproduce §79.1: write an `assert`-based check and an `if`-based check, run both normally
and under `python -O`, and show the `assert` disappears. Explain the role of `__debug__`.

**2. Classify checks.** For several conditions (a user's age is non-negative, a list you just built is non-empty,
an API token is valid, an internal counter is consistent), decide `assert` or `if ...: raise` and justify each by
the invariant-vs-validation test.

**3. Measure the (non-)saving.** Run §79.3's benchmark and confirm `assert` and `if-raise` cost the same when
they run. Explain why `assert` is not a faster check and what its only real difference is.

**4. Catch the tuple bug.** Write `assert (x > 0, "msg")` and show it never fails even for `x <= 0`. Explain why,
and give the correct form.

**5. The design question.** Python strips `assert` under `-O` so invariants cost nothing in production. Argue why
this makes `assert` right for invariants and wrong for validation. Your answer must use the §79.1 fail-open
behavior and §79.3 parity, and state the test for which checks may be `assert`.

---

## 79.7 Summary and cross-references

- **`assert` is stripped entirely under `-O`** (`__debug__` is `False`): the check, and any side effect in it,
  disappears. Code that validates with `assert` **fails open** in optimized production.
- **Use `assert` only for internal invariants** (conditions true if your code is correct, acceptable to strip);
  use **`if ...: raise`** for all input validation and security checks (must always run).
- **Measured:** when it runs, `assert` costs the **same** as `if ...: raise` (17.7 ns vs 17.5 ns), so it is no
  cheaper, its only difference is vanishing under `-O`.
- **Edges:** no side effects in asserts; `assert (cond, "msg")` (tuple) never fails; tests do not cover the `-O`
  path; libraries must not `assert`-validate public inputs; `-OO` also strips docstrings.

**Cross-references.** Exceptions (`raise`) → Chapter 6. `if`/comparison → Chapters 2-3. Deep O security
validation → Chapters 76-78. Testing and pytest `assert` rewriting → Deep O. `-O` and bytecode → Chapter 66,
Deep J. The input seam → Deep U.
