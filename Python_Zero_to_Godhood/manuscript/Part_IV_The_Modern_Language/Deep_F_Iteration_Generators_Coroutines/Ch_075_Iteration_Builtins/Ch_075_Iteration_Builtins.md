# Chapter 75: The Iteration Builtins

Two forms of Python's oldest iteration builtins are underused, and both replace hand-written loops and
exception handling with a single expression. `iter(callable, sentinel)`, the *two-argument* form of `iter`,
builds an iterator that calls `callable()` repeatedly and stops when it returns `sentinel`, the clean way to
"read until EOF" (`iter(lambda: f.read(1024), b'')`) or "poll until a stop value". And `next(it, default)`
returns the next value or, if the iterator is exhausted, the `default`, so you never write `try/except
StopIteration` for the common "next-or-fallback". The second form is not just cleaner: when exhaustion is the
common case, `next(it, default)` is **2.1x** faster than catching `StopIteration` (57 ns versus 122 ns),
because it returns a value instead of raising and catching an exception.

This chapter closes **Deep F** with the iteration builtins that complete the protocol, `iter`'s two-argument
form and `next`'s default, tying together the manual-iteration mechanics (Chapter 69) with the idioms that let
you avoid writing them by hand. They are the small, sharp tools that make protocol-level iteration read cleanly.

## Section index

- **75.1** `iter(callable, sentinel)` and `next(it, default)`
- **75.2** Avoiding hand-written `StopIteration`
- **75.3** Measurement: default vs catching `StopIteration`
- **75.4** Edges and failure modes
- **75.5** Connections
- **75.6** Exercises
- **75.7** Summary and cross-references

Listings live under `code/ch075/` and are re-executed by `make verify` on both interpreters.

---

## 75.1 `iter(callable, sentinel)` and `next(it, default)`

```python
# code/ch075/l01_iter_builtins.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- iter(callable, sentinel): call until the sentinel is returned ---
  chunks : 5 of sizes [1000, 1000, 1000, 1000, 1000]
  replaces a while-True/read/if-not-break loop
--- a sentinel that is not EOF: poll a source until a stop value ---
  polled until 0 : [3, 1, 4, 1, 5]
--- next(it, default): next value or a fallback, no exception ---
  next(it, -1) : 10
  next(it, -1) : 20
  next(it, -1) : -1
--- the equivalent it replaces ---
  next_or(it, -1) three times : 10 20 -1
```

**`iter(callable, sentinel)`** turns a *callable* into an iterator: each `next()` calls `callable()`, and
iteration stops the moment the call returns `sentinel`. The listing reads a buffer in 1000-byte chunks with
`iter(lambda: buf.read(1000), b"")`, iteration ends when `read` returns the EOF sentinel `b""`, yielding five
chunks. This replaces the ubiquitous `while True: chunk = f.read(n); if not chunk: break; ...` loop with one
expression. The sentinel need not be EOF: the second block polls a source until it returns `0`, stopping there.

**`next(it, default)`** returns the next value, or `default` if the iterator is exhausted, *without raising*.
The listing pulls `10`, `20`, then, on the exhausted iterator, `-1`, no exception, no handler. The last block
shows the hand-written equivalent it replaces: a `try/except StopIteration` wrapper. The builtin default is that
wrapper, built in, and §75.3 shows it is also faster when exhaustion is common.

---

## 75.2 Avoiding hand-written `StopIteration`

The iterator protocol signals exhaustion by *raising* `StopIteration` (Chapter 69). That is the right primitive,
but handling it *directly* is verbose and, done in a loop, slow. The two builtins wrap it for the two most
common patterns.

`iter(callable, sentinel)` replaces the "loop calling a function until a stop value" pattern. Instead of `while
True:` with a manual read, a truthiness check, and a `break`, you write the intent, "call this until it returns
that", as an iterator you can pass anywhere iterables go (`for`, `list`, `sum`, a genexp). It is more declarative
and composable, and it cannot get the break condition subtly wrong.

`next(it, default)` replaces the "get one value or fall back" pattern. Instead of `try: x = next(it); except
StopIteration: x = default`, you write `x = next(it, default)`. Beyond brevity, this matters for *performance*
when exhaustion is frequent: raising and catching an exception is more expensive than returning a value (§75.3),
so a loop that calls `next` on possibly-empty iterators pays the exception cost each time it is empty, which the
default form avoids.

The rule: **use `iter(callable, sentinel)` for call-until-sentinel loops and `next(it, default)` for next-or-
fallback, rather than hand-writing the loop or the `StopIteration` handler.** They are clearer (intent, not
mechanics), composable (real iterators), and, for the `next` default when exhaustion is common, faster. Reserve
explicit `StopIteration` handling for cases these do not cover (e.g. you need to *distinguish* exhaustion from a
legitimately-yielded sentinel/`default` value).

---

## 75.3 Measurement: default vs catching `StopIteration`

**Methodology.** `code/ch075/bench_next_default.py`. "Next value or fallback" via `next(it, default)` versus
`try/except StopIteration`, on an iterator that is exhausted (the fallback branch taken every call). `min` per
call; ratio relative to the default form. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| next-or-fallback (exhausted) | min per call | ratio |
|---|---|---|
| `next(it, default)` | **57 ns** | 1.00x |
| `try/except StopIteration` | **122 ns** | **2.13x** |

When the iterator is exhausted, `next(it, default)` returns the default in **57 ns**; the `try/except` form takes
**122 ns**, **2.1x** more, because it *raises* `StopIteration` and *catches* it, the exception machinery (creating
the exception, unwinding to the handler) is the extra cost. The default form never raises; it returns the
fallback directly.

The rule: **when the exhausted (fallback) path is common, prefer `next(it, default)`, it avoids the exception
cost.** This connects to Chapter 6's exception measurement, exceptions are cheap when *not* raised but real when
raised, so a `try/except StopIteration` in a hot loop over frequently-empty iterators pays that cost repeatedly,
while `next(it, default)` sidesteps it. (When exhaustion is *rare*, the two are close, because the exception is
seldom raised, so this is specifically a hot-fallback optimization.) It is the same principle as the rest of the
book: match the construct to the frequency of the case, and here the built-in default is both cleaner and faster
for the common-exhaustion pattern. With this, Deep F's tour of iteration, from the protocol (69) through
coroutines (70), delegation (71), expressions (72), async (73), and context managers (74), closes on the small
builtins that make everyday iteration read well.

---

## 75.4 Edges and failure modes

**`try/except StopIteration` in a hot loop over empty iterators.** §75.3. Pays the exception cost each empty
call. Use `next(it, default)`.

**A sentinel/`default` that could be a real value.** If the callable in `iter(callable, sentinel)` might
legitimately return the sentinel as *data*, iteration stops early; if `default` in `next(it, default)` collides
with a real value, you cannot tell exhaustion from that value. Choose a sentinel that cannot occur in the data
(a unique object), or handle `StopIteration` explicitly when the distinction matters.

**`iter(callable, sentinel)` needs a zero-argument callable.** The callable is called with *no* arguments, so
bind any parameters with a `lambda` or `functools.partial` (`iter(lambda: f.read(1024), b"")`). Passing a
callable that needs arguments is an error.

**`StopIteration` leaking from a generator.** Inside a generator, a `next()` that raises `StopIteration` does not
end the generator, it becomes `RuntimeError` (PEP 479, Chapter 69). Use `next(it, default)` inside generators to
avoid accidentally raising `StopIteration` there.

**Confusing the two `iter` forms.** `iter(iterable)` (one argument) returns the iterable's iterator;
`iter(callable, sentinel)` (two arguments) builds a call-until-sentinel iterator. They are unrelated operations
sharing a name; pass the right number of arguments.

**Infinite `iter(callable, sentinel)`.** If the callable never returns the sentinel, the iterator never ends
(like any infinite iterator). Bound it (`itertools.islice`) if the callable might not reach the sentinel.

---

## 75.5 Connections

**Backward.** The `StopIteration` these builtins wrap, and the iterator protocol, are Chapter 69. The exception
cost the `next` default avoids is Chapter 6's measurement. The file `read` that `iter(callable, b"")` loops over
is Chapter 40. The `functools.partial` for binding the callable is Chapter 34.

**Forward.** These compose with `itertools` (Chapter 33) and generator expressions (Chapter 72), the iterator
from `iter(callable, sentinel)` flows into any of them. The `walrus` operator (Chapter 14) is an alternative for
some read-until loops (`while (chunk := f.read(n)):`); this chapter's form is the iterator-producing counterpart.

**Across books.** The iteration builtins are how Book II reads streams cleanly for **Book III**. A **Book III**
ingest step reads a source in chunks with `iter(lambda: stream.read(N), b"")` and pulls optional values with
`next(it, default)`, avoiding hand-written EOF loops and `StopIteration` handlers, clearer code and, on the
hot fallback path, faster. The §75.3 exception-avoidance matters when the pipeline probes many possibly-empty
sub-streams. **Deep U** owns the stream-reading seam.

---

## 75.6 Exercises

**1. Read until EOF.** Use `iter(callable, sentinel)` to read a buffer in fixed-size chunks until EOF, and show
it replaces a `while True`/`break` loop. Explain the sentinel and why the callable takes no arguments.

**2. Poll until a stop value.** Use `iter(callable, sentinel)` with a non-EOF sentinel to consume a source until
a stop marker. Explain what happens if the stop value could also be real data.

**3. Next-or-fallback.** Replace a `try/except StopIteration` with `next(it, default)` and confirm they behave
the same. Explain when the default form is preferable.

**4. Measure the exception cost.** Run §75.3's benchmark and confirm `next(it, default)` beats `try/except` when
the iterator is exhausted. Then make exhaustion rare and show the gap narrows. Explain the exception-machinery
cost.

**5. The design question.** Python offers both raw `StopIteration` and the `iter`/`next` builtins that wrap it.
Argue why the wrappers exist. Your answer must use the §75.3 measurement, explain the two common patterns they
capture, and identify when explicit `StopIteration` handling is still necessary.

---

## 75.7 Summary and cross-references

- **`iter(callable, sentinel)`** builds an iterator that calls `callable()` until it returns `sentinel`, the
  clean "read until EOF / poll until stop" idiom, replacing a `while True`/`break` loop with a composable
  iterator.
- **`next(it, default)`** returns the next value or `default` when exhausted, *without* raising, replacing a
  `try/except StopIteration` wrapper.
- **Measured:** on an exhausted iterator, `next(it, default)` is **2.1x** faster than catching `StopIteration`
  (57 ns vs 122 ns), because it avoids raising/catching an exception; the gap narrows when exhaustion is rare.
- **Use these builtins over hand-written loops/handlers;** choose a sentinel/default that cannot be real data,
  and fall back to explicit `StopIteration` only when you must distinguish exhaustion from a value.

**Cross-references.** Iterator protocol and `StopIteration` → Chapter 69; PEP 479 → Chapter 69. Exception cost →
Chapter 6. File reading → Chapter 40. `partial` → Chapter 34. `itertools`/genexps → Chapters 33, 72. Walrus in
read loops → Chapter 14. The stream-reading seam → Deep U.
