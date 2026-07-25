# Chapter 55: Tracebacks and Error Reporting

A service catches an expected error, a validation failure that happens thousands of times a second, and logs
`traceback.format_exc()` for each. Under load, the error path becomes the bottleneck, and the profiler blames
traceback formatting. It is right: `format_exc()` walks every frame in the traceback and *reads the source
file lines* for each, so it costs **69x** a bare `str(e)` of the exception message (85 us versus 1.2 us
measured). The full traceback is invaluable for an *unexpected* failure you need to debug; producing it for a
*frequent, expected* error is paying for a diagnostic no one reads. Knowing which errors deserve a full
traceback and which deserve a counted one-line message is the difference between an error path that scales and
one that does not.

That, and the exception-chaining that makes tracebacks tell the truth about causation, is this chapter's
subject. It closes **Deep S** with the `traceback` module and error reporting, building on the exception
mechanics of Chapters 6 and 21 (exception groups) with the tooling to *capture, format, and chain* errors for
diagnostics that are both informative and affordable.

## Section index

- **55.1** Capturing and chaining errors
- **55.2** Explicit vs implicit chaining
- **55.3** Measurement: the cost of a full traceback
- **55.4** Edges and failure modes
- **55.5** Connections
- **55.6** Exercises
- **55.7** Summary and cross-references

Listings live under `code/ch055/` and are re-executed by `make verify` on both interpreters.

---

## 55.1 Capturing and chaining errors

```python
# code/ch055/l01_traceback.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- structured access: the frames that led to the error ---
  exception type      : ValueError
  message             : root cause
  frames in traceback : 4
  innermost function  : level_three
--- explicit chaining: raise New from original sets __cause__ ---
  outer               : RuntimeError
  __cause__ (explicit): ValueError
  __context__ set     : True
--- implicit chaining: an error DURING handling sets __context__ ---
  __cause__ (none)    : None
  __context__ (implicit): ValueError
```

The `traceback` module turns a live exception into *inspectable data*. `traceback.extract_tb(e.__traceback__)`
yields the frames that led to the error as `FrameSummary` objects (filename, line number, function name, source
line), so the first block reads the exception's type, message, and the four frames from `main` down to
`level_three` where it was raised, all as structured data you can log selectively or assert on in a test. This
is the programmatic view; `traceback.format_exc()` and `format_exception()` produce the familiar formatted text.
(The listing prints the *structured facts*, frame count, chain types, because the formatted text contains
environment-specific paths and line numbers that vary by machine.)

The other two blocks show **exception chaining**, which records *why* an error happened, not just *that* it
did.

---

## 55.2 Explicit vs implicit chaining

Python links exceptions through two attributes, and the distinction is worth getting right because it changes
what the traceback tells a future debugger.

**Explicit chaining** with `raise NewError(...) from original` sets `__cause__` to the original exception, and
the traceback prints "The above exception was the direct cause of the following exception." This is how you
*translate* an error across an abstraction boundary while preserving its origin: a data layer catches a
`ValueError` from parsing and raises a `RepositoryError from e`, so the caller sees the high-level error *and*
can trace it to the low-level cause. Use `from` whenever you wrap or re-raise as a different type; it is the
difference between a traceback that explains the failure and one that hides it.

**Implicit chaining** happens automatically when an exception is raised *during the handling of another*: if an
`except` block itself raises (without `from`), Python sets `__context__` to the exception being handled and
prints "During handling of the above exception, another exception occurred." This is usually a *bug signal*, an
error in your error handler, and the implicit chain is what surfaces it. Note the listing's detail:
`raise ... from e` sets `__cause__` *and* `__context__` (the explicit cause also being the context), while a
bare `raise` during handling sets only `__context__`. When you deliberately want to *suppress* a context (a
clean translation with no "during handling" noise), use `raise NewError(...) from None`.

The rule: **chain deliberately.** `from cause` when you translate an error and want its origin preserved;
`from None` when the context is noise; and treat an *unexpected* `__context__` in a traceback as a hint that an
error handler itself failed.

---

## 55.3 Measurement: the cost of a full traceback

**Methodology.** `code/ch055/bench_format.py`. Handling an exception (raised through 20 frames) three ways:
catch only, catch and `str(e)`, catch and `traceback.format_exc()`. `min` per call; ratio relative to
`str(e)`. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| handle an exception | min per call | ratio |
|---|---|---|
| catch only | **1222 ns** | 0.99x |
| catch + `str(e)` (message) | **1234 ns** | 1.00x |
| catch + `format_exc()` (full traceback) | **85,262 ns** | **69x** |

Catching the exception and stringifying its *message* is cheap (~1.2 us, essentially the cost of raising and
catching); the message is already on the exception object. `format_exc()` is **69x** more, because it walks
every frame in the traceback and *reads the source file lines* for each frame to build the formatted output.
That file reading is the dominant cost, and it scales with the traceback depth.

The rule: **reserve the full traceback for errors you need to debug; do not format one on a hot, expected
error path.** A frequent, expected exception (a validation failure, a cache miss modeled as an exception)
should be logged as a *counted one-line message* (`str(e)` plus a metric), not a full traceback thousands of
times a second. An *unexpected* failure, the kind you will actually investigate, should log the full traceback
(`format_exc`, or better, let your logging framework attach it via `exc_info=True`), because there you need
every frame. Match the diagnostic richness to how often the path fires and how likely you are to read the
result: rich and rare, cheap and frequent.

---

## 55.4 Edges and failure modes

**`format_exc` on a hot error path.** §55.3. 69x a message string, dominated by source-file reads. Log a
counted message for frequent expected errors; reserve full tracebacks for unexpected ones.

**Losing the cause by not chaining.** Re-raising a different exception type *without* `from` (or catching and
raising fresh) discards the causal link unless implicit context happens to capture it. Use `raise New from
original` to preserve the origin across a translation.

**Unwanted `__context__` noise.** A clean error translation can carry a confusing "during handling of the above
exception" chain. Use `raise New from None` to suppress the context when it is not informative.

**Holding a traceback keeps frames alive.** An exception's `__traceback__` references its frames, and those
reference their locals. Storing an exception (or its traceback) long-term keeps all that alive, a memory leak.
Extract what you need (`traceback.extract_tb`, a formatted string) and drop the exception object; do not stash
live exceptions.

**Logging `str(exception)` and losing the type.** `str(e)` is the message only; `"ValueError: bad input"` needs
`f"{type(e).__name__}: {e}"` or `traceback.format_exception_only(e)`. Logging the bare message can hide *which*
error occurred.

**Reformatting instead of using `exc_info`.** In `logging`, pass `logger.error("failed", exc_info=True)` (or
`logger.exception(...)` inside an `except`) rather than manually `format_exc()`, the framework formats lazily
and only if the record is emitted (Chapter 52), avoiding the cost when the log is filtered.

---

## 55.5 Connections

**Backward.** The exception mechanics, `raise`, `except`, the exception object, are Chapter 6; exception
*groups* and `except*` are Chapter 21. The frames a traceback walks are the same frames `inspect` (Chapter 49)
and profiling (Chapter 51) read. The lazy-logging discipline that `exc_info=True` follows is Chapter 52.

**Forward.** Structured/JSON error logging and error aggregation (Sentry-style grouping by traceback) are
operational **Deep S** and **Deep U** topics. The `sys.excepthook` that formats uncaught exceptions, and custom
exception reporters, are runtime-service material. Rich third-party tracebacks (better formatting, local
variables) build on this module's structured access.

**Across books.** Disciplined error reporting is how Book II surfaces failures to the **Book III** systems it
feeds. A **Book III** serving path chains errors across its layers (`raise InferenceError from provider_error`)
so a failure is traceable to its origin, logs full tracebacks for unexpected failures via `exc_info` but counts
expected ones cheaply, and never stashes live exceptions that pin frames. The §55.3 cost is why the high-rate
error path logs messages, not tracebacks. **Deep U** owns the error-observability seam.

---

## 55.6 Exercises

**1. Read a traceback as data.** Use `traceback.extract_tb` to get the frames of a caught exception and print
the function names from outermost to innermost. Explain what each `FrameSummary` holds and how it differs from
the formatted text.

**2. Chain explicitly.** Catch a low-level error and `raise` a high-level one `from` it. Inspect `__cause__`
and confirm the traceback shows "direct cause." Then use `from None` and show the context is suppressed.
Explain when each is right.

**3. Measure the formatting cost.** Run §55.3's benchmark and confirm `format_exc()` is far costlier than
`str(e)`. Explain what work it does (frame walking, source reading) and why depth matters.

**4. Avoid the leak.** Store a caught exception in a module-level list and reason about what stays alive (its
traceback, frames, locals). Then store only `traceback.format_exception_only(e)` instead and explain why that
is safe.

**5. The design question.** A full traceback is the richest debugging artifact and the most expensive to
produce. Argue for a policy of when to format one. Your answer must use the §55.3 measurement, distinguish
expected high-rate errors from unexpected ones, and explain why `exc_info=True` (lazy) is better than manual
`format_exc` in logging.

---

## 55.7 Summary and cross-references

- **`traceback`** exposes an exception as data (`extract_tb` -> frames) and as formatted text
  (`format_exc`/`format_exception`). Structured access lets you log or assert selectively.
- **Chain deliberately:** `raise New from cause` sets `__cause__` (explicit, "direct cause") to preserve an
  error's origin across a translation; an error raised *during handling* sets `__context__` implicitly (usually
  a handler bug); `from None` suppresses unwanted context.
- **Measured:** `format_exc()` is **69x** a `str(e)` (85 us vs 1.2 us) because it walks every frame and reads
  source. **Reserve full tracebacks for unexpected errors;** log frequent expected errors as counted messages.
- **Edges:** do not stash live exceptions (they pin frames); include the type, not just the message; prefer
  `exc_info=True` (lazy) over manual formatting in logging.

**Cross-references.** Exceptions → Chapter 6; exception groups → Chapter 21. Frames and introspection →
Chapters 49, 51. Lazy logging and `exc_info` → Chapter 52. Error observability and aggregation → Deep S and
Deep U.
