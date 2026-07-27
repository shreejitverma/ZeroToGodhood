# Chapter 73: Zero-Cost Exceptions

A piece of Python performance folklore, "avoid `try`/`except` in hot code, it is slow", was *true* for two decades and is now *obsolete*, and this chapter is about the change that made it so.
Since Python 3.11, exception handling is **zero-cost**: a `try` block that does *not* raise adds essentially **no** runtime overhead (measured **~1.02x**, free within noise).
The old model set up and tore down exception-handling state on *every* `try` block entry (a real per-entry cost); the new model moves that information **out of line**, into a separate table consulted *only when an exception actually propagates*, so the *happy path* (no exception) pays nothing.

The mechanism is visible in the code object (Chapter 54): a function with a `try` carries a **`co_exceptiontable`** (the out-of-line exception info), while a plain function's is empty, and the try body's bytecode has no inline setup/teardown.
This has a real, practical consequence: it *validates the Pythonic EAFP style* (Easier to Ask Forgiveness than Permission), wrap the normal case in `try`/`except` and handle the rare failure, because the guard is free on the path that does not fail.
But the other half of the lesson stands: **raising** an exception is still costly (measured **~67 ns**: unwind the stack, build and match the exception), so exceptions remain for the *exceptional*, not for hot-loop control flow.

**This is a Deep H chapter on interpreter mechanics.**
It builds on the code object (Chapter 54, the `co_exceptiontable`), corrects a performance myth with measurement, and connects to the exceptions-as-control-flow design that pervades Python.

## Section index

- **73.1** Out-of-line exception tables and EAFP
- **73.2** Guard freely, raise rarely
- **73.3** Measurement: try-with-no-raise versus raising
- **73.4** Edges and failure modes
- **73.5** Connections
- **73.6** Exercises
- **73.7** Summary and cross-references

Listings live under `code/ch154/` and are re-executed by `make verify` on both verification interpreters.

---

## 73.1 Out-of-line exception tables and EAFP

```python
# code/ch154/l01_exceptions.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- the exception info is OUT-OF-LINE, not inline bytecode ---
  a try function has a co_exceptiontable : True
  a plain function's is empty            : True
  so the try body runs with no inline setup/teardown overhead
--- the try body runs normally when nothing is raised ---
  with_try() returns : 1   (the try path, no exception)
--- EAFP: try the operation, handle the rare failure ---
  eafp_get('a') (hit)  : 1
  eafp_get('z') (miss) : None
  the try/except is free on the hit path (zero-cost)
--- but RAISING is costly: exceptions are for exceptional cases ---
  raising + catching does real work (unwind, build the exception),
  so do NOT use exceptions as control flow in a hot loop (the benchmark)
--- the rule ---
  a try block is free when nothing raises (out-of-line table), so use EAFP
  freely; but raising is costly, reserve exceptions for the exceptional
```

**The exception info is out of line.**
A function containing a `try` carries a **`co_exceptiontable`** (a table mapping bytecode ranges to their exception handlers), and this table is *separate* from the executable bytecode; a plain function's exception table is *empty*.
The consequence, and the source of zero-cost: the try body's bytecode has *no inline setup/teardown instructions*.
In the old (pre-3.11) model, entering a `try` executed a `SETUP_FINALLY`-style instruction that pushed handler state onto a block stack, and leaving it popped that state, real work on *every* try entry, whether or not an exception occurred.
The new model emits *no* such instructions; the handler ranges live in the out-of-line table, which the interpreter consults *only* when an exception is *raised* and needs to find its handler.
So on the *happy path*, a `try` block runs its body exactly as if the `try` were not there.

**The try body runs normally.**
`with_try()` returns `1`, the try path, executed with no overhead because nothing raised.

**This validates EAFP.**
Python's idiomatic **EAFP** style, *try the operation and handle the rare failure*, rather than LBYL (Look Before You Leap, *check first, then do*), is now also the *fast* style.
`eafp_get` tries `d[key]` (assuming the key is there, the common case) and catches `KeyError` for the rare miss.
Because the `try` is free on the *hit* path (which is most of the time), EAFP costs nothing in the common case, *and* it is cleaner (no redundant `if key in d:` check before the access, which would look the key up *twice*).
So the Pythonic style and the fast style now coincide: **wrap the normal case in `try`/`except` freely.**

---

## 73.2 Guard freely, raise rarely

The two halves of the measurement give a single, clear rule for exceptions.

**Guard freely: a `try` block is free when nothing raises.** §73.1, §73.3.
Wrapping code in `try`/`except` costs nothing on the path that does not raise, so:

- **Use EAFP** for operations that usually succeed: dict/attribute access with a fallback, parsing that usually works, an operation valid for most inputs. Try it, catch the rare failure. This is cleaner *and* free.
- **Do not avoid `try`/`except` for performance.** The old advice is obsolete. A `try` around a loop, or in a hot function, adds no overhead if it does not raise. Write clear error handling without a speed penalty.
- **Prefer EAFP over LBYL** where the check would duplicate work or introduce a race. `try: x = d[k]` beats `if k in d: x = d[k]` (which looks up `k` twice), and it avoids the time-of-check-to-time-of-use race (the key could vanish between the check and the access in concurrent code).

**Raise rarely: raising is costly.** §73.3.
*Raising* an exception does real work: unwinding the stack to find the handler (consulting the exception table), constructing the exception object (with its traceback, Chapter 54's frames), and matching it against `except` clauses. This is *tens of nanoseconds* per raise, orders of magnitude more than the free guard. So:

- **Do not use exceptions as ordinary control flow in a hot loop.** A `raise` per element (using `StopIteration`-style control flow by hand, or exceptions to signal a common condition) pays the raise cost per element, which adds up. For a condition that occurs *often*, a plain conditional (`if`) is far cheaper than raising.
- **Exceptions are for the exceptional.** The asymmetry, cheap to guard, costly to raise, is the design: the language optimizes for the case where exceptions are *rare* (the happy path is free) and accepts a cost when they *do* occur (which should be seldom).

The rule: **guard freely (a `try` is free on the happy path, so use EAFP), but raise rarely (raising is costly, reserve exceptions for genuinely exceptional conditions).**
This resolves the old tension: you no longer trade clarity for speed in error handling, wrap the normal case freely, just do not *trigger* exceptions as routine control flow.

---

## 73.3 Measurement: try-with-no-raise versus raising

**Methodology.** `code/ch154/bench_exceptions.py`.
A loop with a `try`/`except` that never raises versus the same loop without the `try`; and the cost of raising and catching an exception per iteration.
`min` of 5 runs.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| exception operation | cost |
|---|---|
| loop with `try` (never raises) | 15.2 us |
| loop without `try` | 15.0 us (**1.02x**, free) |
| raising + catching | **~67 ns per raise** |

The `try` block adds **~1.02x** (free within noise) when nothing raises, and *raising* costs **~67 ns** per exception (66 ns on 3.14.6, both identical in shape).

The two numbers are the rule quantified.
The **~1.02x** is zero-cost exceptions: the out-of-line table (§73.1) means the happy path has no overhead, so the old "avoid `try` for speed" advice is *measurably* wrong now, a `try` is free.
The **~67 ns** is why raising is still for the exceptional: constructing and propagating an exception is real work (tens of nanoseconds), so a `raise` in a hot inner loop (a million raises is ~67 ms of pure overhead) is a genuine cost, where the equivalent `if` check is a few nanoseconds.

The practical guidance is therefore *asymmetric and clear*: **guard with `try`/`except` freely (it is free unless it raises), and use EAFP as the idiomatic, fast style; but do not `raise` as routine control flow in a hot path (raising is costly).**
This is a Deep H performance theme, and it corrects a specific piece of obsolete folklore with measurement: the interpreter's evolution (zero-cost exceptions, 3.11) *changed the performance model*, and advice from before that change (avoid `try`) is now wrong.
It also fits the broader Deep H pattern, the interpreter optimizes the *common* case (here, the no-exception path) and accepts cost on the *rare* case (raising), the same philosophy as the specializing interpreter (optimize the common types seen) and constant folding (do the constant work once).
The lesson for writing Python: lean into EAFP and clear error handling without fear of a `try`-block tax, while keeping exceptions for the exceptional, exactly the style the language now rewards on both clarity and speed.

---

## 73.4 Edges and failure modes

**"Avoid `try` for speed" is obsolete (since 3.11).** §73.1, §73.3.
A `try` block is free on the happy path. Do not contort code to avoid it. Older advice and older Python (pre-3.11) had a real per-`try` cost; current Python does not.

**Raising is costly; do not use it as hot-loop control flow.** §73.2, §73.3.
~67 ns per raise. For a condition that occurs often, a plain `if` is far cheaper. Reserve exceptions for the exceptional.

**EAFP versus LBYL is a real choice.** §73.2.
EAFP (try, catch the rare failure) is cleaner and avoids double-lookups and check-then-act races; LBYL (check first) can duplicate work and race. Prefer EAFP for usually-succeeding operations, but LBYL when the check is cheap and the failure common (avoiding the raise cost).

**`StopIteration` is exceptions-as-control-flow, but handled specially.**
Iteration uses `StopIteration` to signal exhaustion (Deep F), a raise per iterator exhaustion, but the interpreter special-cases the iteration protocol so the common `for` loop does not pay a Python-level raise per element. Do not generalize from this to "raising is cheap"; it is not.

**A `try`/`finally` (or `with`) still runs the cleanup.**
Zero-cost applies to the *no-exception* path's overhead; a `finally` block (or a context manager's `__exit__`, Chapter 33) still *runs* on both paths, that is its purpose, and its cost is the cleanup code, not exception machinery.

**Broad `except` hides bugs.**
Free or not, a bare `except:` or `except Exception:` that swallows everything hides errors (Chapter on exceptions). Catch *specific* exceptions; the zero-cost property is about performance, not a license for broad catches.

**Exception construction cost includes the traceback.**
Part of the raise cost is building the traceback (walking frames, Chapter 54). Re-raising or constructing exceptions in tight loops compounds this. If you must signal frequently, a sentinel return value is cheaper than an exception.

**The cost is version-specific in magnitude.**
The ~67 ns raise cost and the zero-cost guard are current-Python figures; the *shape* (free guard, costly raise) is stable since 3.11, but exact numbers vary by version and continue to improve.

---

## 73.5 Connections

**Backward.**
The `co_exceptiontable` is part of the code object (Chapter 54). Exception construction builds a traceback from the frame stack (Chapters 54, 31). Exceptions-as-control-flow is one of Python's founding designs. EAFP is the Pythonic idiom throughout the standard library.

**Forward.**
The specializing interpreter (Chapter 17) and the general "optimize the common case" philosophy are the rest of **Deep H**. `StopIteration` and the iteration protocol (special-cased raising) are Deep F. Context managers and `finally` (Chapter 33) build on the exception machinery. Exception groups (`except*`) are a timeline topic.

**Across books.**
Zero-cost exceptions shape **Book I**'s error-handling style: hot paths can use EAFP and clear `try`/`except` without a performance penalty, so error handling is written for *clarity* (try the operation, handle the failure) rather than contorted to avoid `try` blocks. The order-book system uses EAFP freely in its hot paths (a `try` around an operation that almost always succeeds costs nothing), but is careful *not* to use exceptions as routine control flow in the matching loop (where a condition occurs constantly, an `if` replaces a raise), the §73.2 asymmetry applied: guard freely, raise rarely. The measurement, a free guard and a costly raise, is the design principle that lets Python's expressive error handling be fast, and knowing it lets an engineer write clear, idiomatic error handling in performance-critical code without fear.

---

## 73.6 Exercises

**1. See the out-of-line table.** Reproduce §73.1: confirm a `try` function has a non-empty `co_exceptiontable` and a plain function does not, and that the try body runs normally. Explain how out-of-line handler info enables zero-cost.

**2. Measure the two costs.** Reproduce §73.3. Confirm a `try` that never raises is free (~1.0x) and raising costs tens of nanoseconds. Explain the asymmetry and what raising does.

**3. EAFP versus LBYL.** Implement a dict lookup with a default both ways (EAFP `try`, LBYL `if k in d`), measure both on hits and misses, and explain when each wins (hit-heavy favors EAFP; miss-heavy pays the raise cost).

**4. The hot-loop trap.** Write a loop that uses `raise`/`except` to handle a *common* condition, measure it, then replace the raise with an `if`, and measure the speedup. Explain why exceptions are for the exceptional.

**5. The design question.** Zero-cost exceptions make guarding free but raising costly, an asymmetry. Argue why this is the right design (optimize the common no-exception path), how it validates EAFP, and what it implies for hot-path error handling. Why was the old "avoid `try` for speed" advice reasonable before 3.11 and wrong now?

---

## 73.7 Summary and cross-references

- Since Python 3.11, exception handling is **zero-cost**: a `try` block that does not raise adds **no** overhead (**measured ~1.02x**), because the handler info is **out of line** (`co_exceptiontable`, Chapter 54), consulted only when an exception propagates, so the happy path has no inline setup/teardown.
- This **validates EAFP** (try the operation, handle the rare failure): the guard is free on the common success path, and it is cleaner than LBYL (no double-lookup, no check-then-act race).
- **But raising is costly** (**~67 ns**: unwind the stack, build and match the exception with its traceback), so **exceptions are for the exceptional**, not hot-loop control flow.
- **The rule: guard freely, raise rarely.** Wrap normal cases in `try`/`except` without a speed penalty; do not `raise` as routine control flow in a hot path (use an `if`). The old "avoid `try` for speed" advice is **obsolete**.
- **Edges:** `StopIteration`/iteration is special-cased (do not generalize); `finally`/`with` still run cleanup; catch *specific* exceptions (zero-cost is not a license for broad catches); the traceback is part of the raise cost; magnitudes are version-specific (shape stable since 3.11).

**Cross-references.** The code object / `co_exceptiontable` / traceback frames → Chapters 54, 31. Optimize-the-common-case (specializing interpreter) → Chapter 17, the rest of Deep H. `StopIteration` / iteration protocol → Deep F. Context managers / `finally` → Chapter 33. Exceptions-as-control-flow (founding design) → the exceptions chapters.
