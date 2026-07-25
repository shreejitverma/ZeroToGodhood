# Chapter 54: Warnings

A library deprecates a function, adds `warnings.warn("use new_api instead", DeprecationWarning)`, ships it,
and is surprised when users keep calling the old function and report no warning. The warning works, but
**`DeprecationWarning` is silent by default**: Python's default filters ignore it in ordinary execution,
showing it only under `-W`, in `__main__`, or in test runners. So the deprecation the author dutifully added
is invisible to exactly the end users it was meant to reach. The flip side is the fix for the author's *own*
tests: `simplefilter("error")` (or running with `-W error`) turns warnings into raised exceptions, so a
deprecation that would otherwise be silent *fails the test suite* and cannot be ignored. Warnings are governed
by *filters*, and knowing the default filter behavior is the difference between a warning that is seen and one
that is not.

There is a performance corollary too: `warnings.warn` inspects the call stack to locate the warning's source,
and it does so **even when the filter is `ignore`**, so a warning in a hot loop costs ~19x a no-op even in
production where it is silenced. This chapter continues **Deep S** with the `warnings` system, its filters,
their defaults, and the cost of emitting a warning.

## Section index

- **54.1** Filters decide the fate of a warning
- **54.2** The default that surprises, and the filter that saves tests
- **54.3** Measurement: `warn` is not free when ignored
- **54.4** Edges and failure modes
- **54.5** Connections
- **54.6** Exercises
- **54.7** Summary and cross-references

Listings live under `code/ch054/` and are re-executed by `make verify` on both interpreters.

---

## 54.1 Filters decide the fate of a warning

```python
# code/ch054/l01_warnings.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- 'always': every warning is recorded ---
  two identical warns -> recorded: 2
--- 'once': duplicates are deduplicated ---
  two identical warns -> recorded: 1
--- 'ignore': silenced entirely ---
  two identical warns -> recorded: 0
--- 'error': a warning becomes a raised exception ---
  warn under 'error' -> raised: DeprecationWarning
  (run tests with -W error to make silent deprecations fail)
```

`warnings.warn(message, category)` emits a warning; a **filter** decides what happens to it, and the listing
demonstrates the four actions via `catch_warnings(record=True)` (the standard way to capture warnings, in
tests especially). **`always`** records every emission (two identical warns produce two records).
**`once`** deduplicates (two produce one), and the related default `default` shows one per unique source
location. **`ignore`** silences entirely (zero records). **`error`** turns the warning into a *raised
exception*, the `warn` call under `error` raises `DeprecationWarning` instead of returning.

`catch_warnings` is a context manager that saves and restores the filter state, so tests can set a filter,
capture warnings, and assert on them without leaking filter changes to other tests. `record=True` collects the
warnings into a list of `WarningMessage` objects (with `.message`, `.category`, `.filename`, `.lineno`) instead
of printing them, which is how you assert "this code warned about X."

---

## 54.2 The default that surprises, and the filter that saves tests

The default filter set is deliberately quiet for *end users* and can be made loud for *developers*, and the
two most important consequences are the ones the chapter opened with.

**`DeprecationWarning` is ignored by default** in normal execution. The rationale is sound, an end user
running an application should not be spammed with deprecation notices about libraries they cannot change, so
Python's default filters suppress `DeprecationWarning` (and `PendingDeprecationWarning`, `ImportWarning`) except
when triggered directly in `__main__`, and test frameworks (`pytest`, `unittest`) re-enable them so developers
*do* see them. The trap is the library author who tests their deprecation interactively, sees nothing, and
concludes it does not work, or worse, the user who never sees a deprecation until the function is removed. Know
that your audience determines visibility: developers and CI see deprecations; end users do not.

**`error` makes warnings fail loudly**, which is the developer-side lever. Running tests with `-W error`
(or `filterwarnings = error` in pytest config) turns every warning into an exception, so a `DeprecationWarning`
from a dependency, or your own code using something deprecated, *fails the build* instead of scrolling past.
This is the recommended CI posture: treat warnings as errors so deprecations are addressed while there is time,
before the deprecated thing is removed and the code breaks. The `error` filter converts a silent, easy-to-
ignore signal into a hard, must-fix one.

The general model: filters are matched in order against `(category, message, module, lineno)`, and you
compose them, ignore a specific noisy warning from one library, error on your own package's deprecations,
default for the rest. `warnings.filterwarnings(action, ...)` adds a specific rule; `simplefilter(action)`
sets a blanket one.

---

## 54.3 Measurement: `warn` is not free when ignored

**Methodology.** `code/ch054/bench_warn_cost.py`. `warnings.warn` under an `ignore` filter (nothing is shown)
versus a no-op call. `min` per call; ratio relative to the no-op. CPython 3.13.5, Apple M3 Pro, macOS 27.0,
arm64.

| operation | min per call | ratio |
|---|---|---|
| no-op call | **11 ns** | 1.00x |
| `warnings.warn` (ignored) | **205 ns** | **18.6x** |

Even though the filter is `ignore` and nothing is printed, `warnings.warn` costs **205 ns, ~19x** a no-op,
because it inspects the call stack to determine the warning's source location (module and line) so filters can
match and deduplicate by location. That stack inspection happens *before* the filter decides to ignore the
warning, so the cost is paid regardless of the outcome. The filter silences the *output*, not the *work of
producing the warning*.

The rule: **do not emit warnings inside a hot loop.** A deprecated function should `warn` *once per call site*
(or once total, via a module-level guard), not once per iteration of a loop inside it. If you find yourself
warning in a tight loop, hoist the `warn` out, or gate it so it fires once, because the ~200 ns is paid on
every call even in production where the warning is suppressed. Warnings are a developer-time signal; keep their
runtime cost off the hot path.

---

## 54.4 Edges and failure modes

**Assuming a `DeprecationWarning` is visible.** §54.2. It is ignored by default for end users. Test with
`-W error` or in a framework that surfaces it, and document the deprecation; do not rely on the warning alone
reaching users.

**`warn` in a hot loop.** §54.3. ~19x a no-op even when ignored (stack inspection). Warn once, not per
iteration.

**Wrong `stacklevel`.** By default `warnings.warn` reports *its own* line as the source, not the caller's. For
a deprecated function, pass `stacklevel=2` (or use `warnings.warn(..., stacklevel=...)`) so the warning points
at the *user's* call site, not the internal `warn` line. A wrong `stacklevel` makes the warning unactionable.

**Leaking filter state.** Calling `simplefilter`/`filterwarnings` at import time mutates global state for the
whole process, which can surprise other code. In tests use `catch_warnings` (which saves/restores); in
libraries do not set global filters at all, leave the policy to the application.

**Catching warnings is not thread-safe.** `catch_warnings` manipulates global filter state, so using it to
capture warnings in one thread affects others. Do not rely on `catch_warnings` for per-thread warning capture
in concurrent code.

**Using warnings for control flow or errors.** A warning is a diagnostic, not an exception. If a condition
should stop execution, raise; if it is genuinely just advisory, warn. Do not `warn` for something the caller
must handle, and do not swallow a real error as a warning.

---

## 54.5 Connections

**Backward.** The exception machinery `error` filters turn warnings into is Chapters 6 and 21 (exception
groups). The stack inspection `warn` performs is the frame introspection of Chapters 49 and 22. The
`catch_warnings` context manager is the protocol of Chapter 5.

**Forward.** `logging` (Chapter 52) is the sibling diagnostic channel, and `logging.captureWarnings(True)`
routes warnings *into* logging, useful in production. `sys.monitoring` (Chapter 22) is the lower-level event
system. Deprecation policy across releases (PEP 387, the deprecation-and-removal cycle) is a **Deep S**
process topic.

**Across books.** Warnings are how Book II signals API evolution to the code that carries into **Book III**. A
**Book III** library that deprecates a parameter or function emits a `DeprecationWarning` with a correct
`stacklevel`, and the consuming application runs its CI with `-W error` so those deprecations are fixed before
the next major version removes them, exactly the §54.2 discipline. Treating warnings as errors in CI is what
keeps the cross-book upgrade path from breaking silently. **Deep U** owns the release/upgrade seam.

---

## 54.6 Exercises

**1. Reproduce the filter actions.** Use `catch_warnings(record=True)` to show `always`, `once`, `ignore`, and
`error` behave as in §54.1. Explain what each does and when you would choose it.

**2. Expose the silent default.** Emit a `DeprecationWarning` in a plain script and show it is not printed,
then run with `-W default` (or `error`) and show it appears. Explain why the default suppresses it and who is
meant to see it.

**3. Measure the cost.** Run §54.3's benchmark and confirm `warnings.warn` is far more expensive than a no-op
even when ignored. Explain what work it does regardless of the filter, and why warning in a hot loop is a bug.

**4. Fix the stacklevel.** Write a deprecated function that warns with the default `stacklevel` (pointing at
itself) and then with `stacklevel=2` (pointing at the caller). Show the difference in the reported location.
Explain why the caller's location is the actionable one.

**5. The design question.** Python makes `DeprecationWarning` silent by default but lets developers turn all
warnings into errors. Argue why this two-audience design is right. Your answer must address who each default
serves (end users vs developers/CI), why `-W error` in CI is the recommended posture, and why a warning must
not be used where an exception is required.

---

## 54.7 Summary and cross-references

- **Filters decide a warning's fate:** `always` (every time), `once`/`default` (deduplicated), `ignore`
  (silenced), `error` (raised as an exception). Capture warnings in tests with `catch_warnings(record=True)`.
- **`DeprecationWarning` is ignored by default** for end users (shown under `-W`, in `__main__`, and in test
  runners). Run CI with **`-W error`** so deprecations fail the build instead of scrolling past.
- **Measured:** `warnings.warn` costs **~19x** a no-op (205 ns vs 11 ns) *even when ignored*, because it
  inspects the call stack for the source location. **Do not warn in a hot loop;** warn once.
- **Edges:** set `stacklevel` so the warning points at the caller; do not set global filters in libraries; a
  warning is a diagnostic, not an exception.

**Cross-references.** Exceptions and `error` filters → Chapters 6, 21. Frame introspection → Chapters 49, 22.
Context managers → Chapter 5. `logging` and `captureWarnings` → Chapter 52. Deprecation policy → Deep S. The
upgrade seam → Deep U.
