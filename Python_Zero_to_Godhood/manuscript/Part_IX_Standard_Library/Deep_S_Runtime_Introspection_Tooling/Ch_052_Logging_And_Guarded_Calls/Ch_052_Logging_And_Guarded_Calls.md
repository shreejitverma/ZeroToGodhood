# Chapter 52: Logging and the Cost of a Disabled Call

Chapter 12 established the lazy-logging rule: write `log.debug("value=%s", x)`, not `log.debug(f"value={x}")`,
so that when `DEBUG` is disabled the message is never formatted. That rule is correct and important, and it is
also incomplete, because it defends only against the *formatting* cost. It does nothing about the *argument
evaluation* cost. `log.debug("value=%s", expensive())` still calls `expensive()` in full every time, even when
`DEBUG` is off and nothing is logged, because Python evaluates a function's arguments *before* the function
runs. Measured, a disabled `debug` call whose argument is a real computation costs **16,400 ns**; guarded with
`log.isEnabledFor(logging.DEBUG)` so the argument is skipped, it costs **47 ns**, a **344x** difference. The
lazy-`%` form saved the formatting; only the guard saves the work of building the argument.

That distinction, and when to reach for the `isEnabledFor` guard, is this chapter's subject. It continues
**Deep S** with the `logging` module's performance model, completing Chapter 12's lazy-formatting rule with
the argument-evaluation rule the eager-evaluation semantics of Python make necessary.

## Section index

- **52.1** A disabled call still evaluates its arguments
- **52.2** Lazy formatting vs the `isEnabledFor` guard
- **52.3** Measurement: the cost of an unguarded expensive argument
- **52.4** Edges and failure modes
- **52.5** Connections
- **52.6** Exercises
- **52.7** Summary and cross-references

Listings live under `code/ch052/` and are re-executed by `make verify` on both interpreters.

---

## 52.1 A disabled call still evaluates its arguments

```python
# code/ch052/l01_logging.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- lazy-% form: message not formatted, but the ARGUMENT is evaluated ---
  expensive() called       : 5 times (though nothing was logged)
--- isEnabledFor guard: the argument is not evaluated at all ---
  expensive() called       : 0 times (guard skipped it)
--- the guard only matters when the argument is EXPENSIVE ---
  cheap literal args need no guard (log.debug('hello') is already near-free)
  guard expensive-to-compute args; leave cheap ones to lazy-% (Chapter 12)
```

The listing makes the eager-evaluation fact observable with a side-effect counter. `expensive()` increments a
counter each time it runs. With `DEBUG` disabled, `log.debug("value=%s", expensive())` in a loop of five
still calls `expensive()` **5 times**, the counter proves it, even though nothing is logged. The lazy-`%` form
successfully avoided *formatting* the message (that work never happened), but `expensive()` was evaluated to
produce the argument *before* `log.debug` was even entered, because that is how Python calls functions:
arguments first, call second.

Wrapped in `if log.isEnabledFor(logging.DEBUG):`, the same loop calls `expensive()` **0 times**, the guard
checks the level *before* evaluating anything, and since `DEBUG` is off, the whole body, including
`expensive()`, is skipped. The guard is the only construct that prevents the argument from being computed.

---

## 52.2 Lazy formatting vs the `isEnabledFor` guard

Two different costs hide behind a log call, and two different techniques address them:

- **Formatting cost** (interpolating the message string). Addressed by the **lazy-`%` form** (Chapter 12):
  passing `"value=%s", x` instead of an f-string means `logging` formats the message only if the record is
  actually emitted. This is the right default for *every* log call, and it costs nothing to adopt.
- **Argument-evaluation cost** (computing the values you pass). Addressed only by the **`isEnabledFor`
  guard**: because Python evaluates arguments eagerly, the only way to avoid computing an argument for a
  disabled level is to not reach the call at all.

The two compose. Use lazy-`%` everywhere; add an `isEnabledFor` guard *only* around calls whose arguments are
expensive to build (a database query, a serialization, a large computation, a `repr` of a big structure). For
a cheap literal or a simple variable, the guard is pointless, the argument costs nothing to evaluate, and
`log.debug("hello")` is already near-free (47-70 ns, essentially the level check). Guarding every log call
would clutter the code for no benefit on the vast majority that pass cheap arguments; guarding the few with
expensive arguments is where §52.3's 344x lives.

The judgment, then, is per call: **is the *argument* expensive to compute?** If yes, guard it. If no, the
lazy-`%` form alone is sufficient. This mirrors the book's general rule, spend effort where the measurement
says it matters, not uniformly.

---

## 52.3 Measurement: the cost of an unguarded expensive argument

**Methodology.** `code/ch052/bench_guard.py`. `DEBUG` disabled. Three forms of a disabled `debug` call: guarded
with `isEnabledFor`, a cheap literal, and unguarded with an expensive argument (`expensive()`). `min` per call;
ratios relative to the guarded form. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| disabled `DEBUG` call | min per call | ratio |
|---|---|---|
| guarded (`isEnabledFor`) | **47.6 ns** | 1.00x |
| cheap literal (`log.debug("hello")`) | **53.7 ns** | 1.13x |
| unguarded, expensive argument | **16,426 ns** | **344x** |

The guarded call and the cheap-literal call are both ~50 ns, essentially the cost of the level check itself,
and nearly identical, which is the key point: *when the argument is cheap, the unguarded lazy-`%` call is
already as fast as the guarded one*, so no guard is warranted. The unguarded call with an *expensive* argument
is **344x** more, and every nanosecond of that is `expensive()` running to build a value that is immediately
discarded because nothing is logged.

The rule: **use the lazy-`%` form for all log calls (Chapter 12); add an `isEnabledFor` guard only when the
call's arguments are expensive to compute.** In a hot loop that logs at `DEBUG` with a costly argument, the
guard is the difference between paying that cost on every iteration in production (where `DEBUG` is off) and
paying nothing. Reserve it for exactly that case; do not guard cheap log calls, and do not skip the lazy-`%`
form thinking a guard replaces it (they address different costs).

---

## 52.4 Edges and failure modes

**Unguarded expensive log arguments.** §52.3. `log.debug("%s", expensive())` runs `expensive()` even when
`DEBUG` is off, 344x the guarded cost here. Guard calls with expensive arguments using `isEnabledFor`.

**Over-guarding cheap calls.** §52.2. Wrapping every `log.debug` in `isEnabledFor` clutters code and helps
nothing when the argument is cheap (the guarded and unguarded costs are equal). Guard only expensive
arguments.

**Using f-strings in log calls.** The f-string is formatted *eagerly*, defeating lazy formatting even for
cheap-to-emit records. Use the `"%s"`, args form (Chapter 12); the guard does not fix an f-string's eager
formatting.

**Side effects in log arguments.** Because arguments are always evaluated, a log argument with a side effect
(`log.debug("did %s", do_thing())`) runs that side effect regardless of level, a subtle bug if the code
assumes disabled logs do nothing. Keep log arguments pure.

**`logging.disable()` vs level.** `logging.disable(level)` globally suppresses records at or below a level,
independent of per-logger levels; it changes what `isEnabledFor` returns but not the eager-evaluation
semantics. Understand which knob you are turning.

**Configuring logging in a library.** A library should *not* call `basicConfig` or add handlers to the root
logger, that is the application's job. Libraries get a logger via `logging.getLogger(__name__)` and add a
`NullHandler`, leaving configuration to the app. Misconfiguring from a library produces duplicate or
misrouted logs.

---

## 52.5 Connections

**Backward.** The lazy-`%`-versus-f-string formatting rule this chapter completes is Chapter 12 (measured 107x
there). The eager argument evaluation that makes the guard necessary is Python's call semantics from Chapters
2 and 5. The `isEnabledFor` level check is a cheap attribute/comparison (Chapter 2).

**Forward.** Structured logging, log routing, and handlers/formatters at scale are further **Deep S** and
operational material. `sys.monitoring` (Chapter 22) is the lower-level event mechanism; `warnings` is the
sibling diagnostic channel. Async-aware logging and context propagation connect to `contextvars` (later Deep
S) and Chapters 10-11.

**Across books.** Guarded, lazy logging is how Book II instruments the paths that carry into **Book III**
without the instrumentation becoming the cost. A **Book III** serving path logs rich `DEBUG` diagnostics
(token counts, retrieved-document summaries, timing) guarded by `isEnabledFor`, so in production (DEBUG off)
those expensive-to-build diagnostics cost nothing, while a developer can flip the level to see them. The
§52.3 measurement is why the hot path can afford to *contain* expensive debug logging that is dormant in
production. **Deep U** owns the observability seam.

---

## 52.6 Exercises

**1. Prove eager evaluation.** Reproduce §52.1 with a side-effect counter and show a disabled `debug` call
still evaluates its argument, and that `isEnabledFor` prevents it. Explain why the lazy-`%` form does not help
here.

**2. Measure the guard.** Run §52.3's benchmark and confirm the unguarded expensive call is far costlier than
the guarded one, while the cheap-literal call needs no guard. Explain why guarding cheap calls is pointless.

**3. Find the expensive arguments.** In a small program, identify which log calls pass expensive arguments and
guard exactly those. Explain your criterion and why guarding the others would be over-engineering.

**4. Catch a side-effect bug.** Write a log call whose argument has a side effect and show the side effect
runs even at a disabled level. Explain why log arguments must be pure.

**5. The design question.** Python evaluates log arguments eagerly, forcing the `isEnabledFor` guard for
expensive arguments, where some languages defer log arguments as lazy thunks. Argue the trade-offs. Your
answer must use the §52.3 measurement, explain why lazy-`%` and the guard address different costs, and say
why the guard should be applied selectively rather than everywhere.

---

## 52.7 Summary and cross-references

- A **disabled log call still evaluates its arguments** (Python is eager). The lazy-`%` form (Chapter 12)
  avoids *formatting*; only an **`isEnabledFor` guard** avoids *evaluating* an expensive argument.
- **Measured:** an unguarded `log.debug("%s", expensive())` with `DEBUG` off costs **344x** the guarded call
  (16,426 ns vs 47.6 ns); a cheap-literal call is already as fast as the guarded one, so it needs no guard.
- **The rule:** lazy-`%` for *every* log call; add `isEnabledFor` *only* around calls with expensive
  arguments. Keep log arguments pure (they always run).
- **Libraries** configure nothing, get `logging.getLogger(__name__)`, add a `NullHandler`, and leave setup to
  the application.

**Cross-references.** Lazy-`%` vs f-string formatting → Chapter 12. Eager call semantics → Chapters 2, 5.
`sys.monitoring` → Chapter 22. `contextvars` and async logging → the rest of Deep S and Chapters 10-11. The
observability seam → Deep U.
