# Chapter 74: Generator Context Managers

Chapter 5 built context managers as classes with `__enter__` and `__exit__`. There is a second way, and it is
one of the most elegant uses of a generator for something other than iteration. Decorate a generator that
`yield`s exactly once with `@contextlib.contextmanager`, and it *becomes* a context manager: the code *before*
the `yield` is `__enter__` (setup), the yielded value is the `as` target, and the code *after* the `yield` is
`__exit__` (teardown). One readable function replaces a two-method class, and the `try/finally` around the
`yield` guarantees cleanup even when the body raises, because the exception is *thrown into the generator* at
the `yield` point. The cost of that elegance is speed: the generator form is **3.7x** slower per use than a
hand-written class (450 ns versus 123 ns), because it drives a generator through a wrapper object. For the
overwhelming majority of context managers, wrapping real work, that overhead is nothing; for a context entered
on a hot path, the class wins.

This chapter continues **Deep F** with generator-based context managers: how the single `yield` splits setup
from teardown, how exceptions flow into the generator (enabling cleanup and even suppression), and the
conciseness-versus-speed trade with the class form. It connects the generators of Chapter 69 to the context-
manager protocol of Chapter 5.

## Section index

- **74.1** The `yield` splits setup and teardown
- **74.2** Exceptions flow into the generator
- **74.3** Measurement: generator vs class
- **74.4** Edges and failure modes
- **74.5** Connections
- **74.6** Exercises
- **74.7** Summary and cross-references

Listings live under `code/ch074/` and are re-executed by `make verify` on both interpreters.

---

## 74.1 The `yield` splits setup and teardown

```python
# code/ch074/l01_contextmanager.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- setup runs, body runs, teardown runs (the yield splits them) ---
  events : ['setup db', 'body uses db', 'teardown db']
--- an exception in the body is thrown into the generator; finally runs ---
  events : ['setup file', 'body raises', 'teardown file', 'caught outside']
--- a context manager can SUPPRESS the exception (not re-raise) ---
  events : ['body raises', 'suppressed ValueError', 'execution continued past the with']
```

`@contextlib.contextmanager` transforms a one-`yield` generator into a context manager. In `managed`, everything
before `yield` runs on `__enter__` (`setup db`), the `yield`ed value becomes the `as` target (the body uses it),
and everything after `yield`, here in a `finally`, runs on `__exit__` (`teardown db`). The event order,
`setup`, `body`, `teardown`, is exactly the `with`-block lifecycle, expressed as the top-to-bottom flow of a
single function. The `yield` is the seam where control leaves the setup, runs the body, and returns for
teardown.

This is a genuinely different use of `yield` than Chapters 69-73: the generator does not *produce a sequence*;
it produces *exactly one value* and uses the suspension to *straddle* the `with`-block. It reads far better than
a class, the setup and teardown are adjacent in one function, sharing local variables (the acquired resource is
just a local), instead of split across `__enter__`/`__exit__` with state stored on `self`.

---

## 74.2 Exceptions flow into the generator

The second and third blocks show the mechanism that makes generator context managers *correct*, not just
concise. When the `with`-body raises, `@contextmanager` does not merely resume the generator, it **throws the
exception into it** at the `yield` point (using `generator.throw`, Chapter 70). So a `try/finally` around the
`yield` runs its teardown even on failure (`setup file`, `body raises`, `teardown file`, then the exception
propagates out and is `caught outside`). This is why the `finally` idiom guarantees cleanup: the exception
arrives *at the `yield`*, and the `finally` runs as the generator unwinds.

The third block goes further: because the exception is thrown *into* the generator, the generator can **catch
it** and, by *not re-raising*, **suppress** it. `suppressing` wraps its `yield` in `try/except ValueError`, so a
`ValueError` in the body is caught inside the generator (`suppressed ValueError`) and *execution continues past
the `with`* (`execution continued past the with`), the exception never escapes. This is exactly how
`contextlib.suppress` works, and it is only possible because the exception enters the generator as a real
`throw`. (The class equivalent is `__exit__` returning `True` to suppress; the generator equivalent is catching
and not re-raising.)

The rule: **use `try/finally` around the `yield` for cleanup that must always run, and `try/except` (not re-
raising) only when you deliberately mean to suppress.** A bare `yield` with cleanup *after* it (not in a
`finally`) is a bug: if the body raises, the exception is thrown at the `yield` and the cleanup code after it is
*skipped*. Always guard teardown with `finally`.

---

## 74.3 Measurement: generator vs class

**Methodology.** `code/ch074/bench_cm.py`. Entering and exiting a context manager with an empty body, implemented
as a `@contextmanager` generator versus a class with `__enter__`/`__exit__`. `min` per call; ratio relative to
the class. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| enter/exit a context manager | min per call | ratio |
|---|---|---|
| class `__enter__`/`__exit__` | **123 ns** | 1.00x |
| `@contextmanager` generator | **450 ns** | **3.66x** |

The generator form is **3.7x** slower. The class calls `__enter__` and `__exit__` directly, two method calls;
the `@contextmanager` form wraps the generator in a `_GeneratorContextManager` helper and drives it, `next()` to
run to the `yield` on enter, `next()`/`throw()` to resume past it on exit, so it pays generator creation and
stepping plus the wrapper. The absolute difference is ~330 ns per `with`.

The rule: **prefer `@contextmanager` for its conciseness; the overhead is negligible when the `with`-block does
real work.** A context manager almost always wraps something substantial, opening a file, acquiring a lock,
starting a transaction, holding a resource for the body's duration, against which 330 ns is invisible. So the
readable generator form is the right default. Reach for a class only when the context is *entered on a hot path*
(millions of `with` statements, e.g. a fine-grained lock in a tight loop), where the 3.7x matters, or when the
context manager must be a *rich object* with additional methods, state, or reuse semantics. As elsewhere in Deep
F, the concise idiom is the default and the class is the specialized, faster tool for the hot or rich case.

---

## 74.4 Edges and failure modes

**Cleanup after `yield` without `finally`.** §74.2. If the body raises, the exception is thrown at the `yield`
and code after it is skipped. Put teardown in a `finally`, always.

**More than one `yield`.** A `@contextmanager` generator must `yield` *exactly once*. Yielding twice raises
`RuntimeError` on exit ("generator didn't stop"); never yielding raises `RuntimeError` on enter. Keep it a
single `yield`.

**Accidental suppression.** A broad `except` around the `yield` that does not re-raise silently swallows the
body's exceptions, a subtle bug. Only catch what you *mean* to suppress, and re-raise the rest.

**Hot-path entry.** §74.3. 3.7x a class. For a context manager entered in a tight loop, use a class (or restructure
to enter the context once outside the loop).

**Reusing a `@contextmanager` instance.** The object returned by calling a `@contextmanager` function is single-
use (it wraps one generator); you cannot enter the *same* returned object twice. Call the function again for each
`with`. (`contextlib.contextmanager` is not reentrant; for a reusable/reentrant one, write a class or use
`contextlib`'s reentrant helpers.)

**Async cleanup.** `@contextmanager` is for *sync* context managers. For `async with`, use
`@contextlib.asynccontextmanager` with an async generator (Chapter 73). Do not mix them.

---

## 74.5 Connections

**Backward.** The class-based context-manager protocol (`__enter__`/`__exit__`) is Chapter 5; this chapter is its
generator form. The exception thrown into the generator at `yield` is the `throw` of Chapter 70. The `with`
statement and its guarantees are Chapter 5. File/lock/transaction context managers appear in Chapters 40, 8, 41.

**Forward.** `contextlib.asynccontextmanager` (async version) pairs with async generators (Chapter 73).
`contextlib` utilities (`suppress`, `closing`, `ExitStack`) build on this protocol. The `with`-statement bytecode
(`SETUP_WITH`/`WITH_EXCEPT_START`) is a **Deep J** topic.

**Across books.** Generator context managers are how Book II expresses scoped resources concisely for
**Book III**. A **Book III** pipeline uses `@contextmanager` for readable scoped setup/teardown, a timing span, a
temporary model configuration, a transaction around a batch, with cleanup guaranteed by `finally` even when the
body fails, and drops to a class only for the rare hot-path or rich-object case. The §74.2 exception-into-the-
generator behavior is what makes those cleanups reliable under failure, the property a resource seam depends on.
**Deep U** owns the scoped-resource seam.

---

## 74.6 Exercises

**1. Split with `yield`.** Write a `@contextmanager` that sets up and tears down a (fake) resource, and confirm
the setup/body/teardown order. Explain what the `yield` corresponds to in the class protocol.

**2. Guarantee cleanup.** Make the `with`-body raise and show the `finally`-teardown still runs, then remove the
`finally` and show the teardown is skipped. Explain where the exception is thrown.

**3. Suppress deliberately.** Write a `@contextmanager` that suppresses a specific exception (catches, does not
re-raise) and show execution continues past the `with`. Explain how this mirrors `__exit__` returning `True`.

**4. Measure the overhead.** Run §74.3's benchmark and confirm `@contextmanager` is slower than a class. Explain
the generator-driving cost and why it is negligible for real `with`-blocks.

**5. The design question.** `@contextmanager` trades ~3.7x speed for a far more concise, single-function context
manager. Argue when to use it versus a class. Your answer must use the §74.3 measurement, the exception-into-the-
generator mechanism, and identify the hot-path and rich-object cases where a class is right.

---

## 74.7 Summary and cross-references

- **`@contextlib.contextmanager`** turns a one-`yield` generator into a context manager: code **before `yield`**
  is `__enter__`, the **yielded value** is the `as` target, code **after `yield`** (in a `finally`) is `__exit__`.
- **Exceptions are thrown into the generator** at the `yield`, so `try/finally` guarantees cleanup and
  `try/except` (not re-raising) can **suppress**. Cleanup after a bare `yield` (no `finally`) is skipped on error.
- **Measured:** `@contextmanager` is **3.7x** slower than a class (450 ns vs 123 ns) because it drives a
  generator through a wrapper; negligible when the `with`-block does real work.
- **Prefer `@contextmanager` for conciseness;** use a class for hot-path entry or a rich reusable object; use
  `@asynccontextmanager` for `async with`. Always `yield` exactly once, teardown in `finally`.

**Cross-references.** Class context managers and `with` → Chapter 5. `throw` into a generator → Chapter 70.
File/lock/transaction contexts → Chapters 40, 8, 41. `asynccontextmanager` → Chapter 73. `contextlib` utilities →
Chapter 5. `with` bytecode → Deep J. The scoped-resource seam → Deep U.
