# Chapter 70: Generator Coroutines

Chapter 69 used a generator as a *producer*, values flow out. But `yield` is two-way: `value = yield result`
sends `result` *out* to the caller and receives the caller's next `value` *in* through `.send()`. That single
fact turns a generator into a **coroutine**, a function that suspends, receives data, and resumes with its
state intact, held in ordinary local variables across every suspension. A running-average coroutine keeps
`total` and `count` as locals and yields the current average each time you `send` it a number, no state object,
no update method, just a natural sequential state machine. And it is not slower for the privilege: sending 1000
values into a coroutine costs about the **same** (0.94x) as calling a class's update method 1000 times, because
both pay one call per value. The coroutine's advantage is not speed but *expressiveness*, and, via `.close()`
and `.throw()`, cleanup and error injection the class must build by hand.

This chapter continues **Deep F** with the coroutine side of generators: `send` (two-way communication),
`close` (cleanup via `GeneratorExit`), and `throw` (exception injection). This is the mechanism `asyncio` was
built on before native `async`/`await` (Chapters 10-11), and understanding it demystifies both.

## Section index

- **70.1** `send`, `close`, `throw`
- **70.2** State machine without the boilerplate
- **70.3** Measurement: coroutine vs class
- **70.4** Edges and failure modes
- **70.5** Connections
- **70.6** Exercises
- **70.7** Summary and cross-references

Listings live under `code/ch070/` and are re-executed by `make verify` on both interpreters.

---

## 70.1 `send`, `close`, `throw`

```python
# code/ch070/l01_coroutine.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- send: two-way communication, state kept across suspensions ---
  send 10 -> avg 10.0
  send 20 -> avg 15.0
  send 30 -> avg 20.0
--- close: GeneratorExit runs the finally (cleanup) ---
  events: ['processed 1', 'cleanup ran on close']
--- throw: inject an exception at the suspension point ---
  events: ['got 1', 'handled ValueError, continued', 'got 2']
```

**`send`** is the two-way channel. In `running_average`, `value = yield average` yields the current average and,
when the caller calls `avg.send(10)`, resumes with `value` bound to `10`. The coroutine updates `total` and
`count` (its locals, preserved across the suspension) and loops back to yield the new average. So `send(10)`,
`send(20)`, `send(30)` produce `10.0`, `15.0`, `20.0`, a stateful accumulator whose state lives entirely in
local variables. (Note the *priming*: you must call `next()` once first to run the coroutine to its initial
`yield` before you can `send` a real value, sending into an un-primed generator raises `TypeError`.)

**`close`** stops the coroutine: it raises `GeneratorExit` at the suspension point, so a `try/finally` around the
`yield` runs its cleanup, the `worker` records `'cleanup ran on close'`. This is deterministic teardown for a
coroutine holding a resource. **`throw`** injects an exception at the suspension point: `r.throw(ValueError)`
raises `ValueError` where the coroutine is paused, and because `resilient` wraps its `yield` in `try/except`, it
handles it and *continues* (the events show `got 1`, `handled ValueError, continued`, `got 2`). Together, `send`/
`close`/`throw` make a generator a fully controllable coroutine: feed it, tear it down, and signal errors into
it.

---

## 70.2 State machine without the boilerplate

The coroutine form shines when the logic is *naturally sequential with state*. A class-based accumulator
declares an `__init__` to set up `self.total`/`self.count` and an `update` method that mutates them and returns
the result, the state is explicit fields, the logic is a method. The coroutine holds the *same* state as plain
locals and expresses the logic as a straight-line loop with a `yield` in the middle, the suspension *is* the
"wait for the next value" step, and the locals *are* the state, preserved automatically.

For simple accumulators the difference is stylistic, but as the state machine grows more *sequential* (a parser
that reads tokens one at a time, a protocol that expects a header then a body then a trailer, a pipeline stage
that transforms a stream), the coroutine's advantage compounds: the control flow reads as the *sequence of
steps* (read header; loop reading body; on end, finalize), with state implicit in where execution is suspended,
rather than a class that reconstructs "which step am I in" from explicit state fields on every method call. The
coroutine turns a state machine into ordinary sequential code. And `close`'s `finally` gives cleanup for free,
where the class needs an explicit teardown method the caller must remember to invoke.

The rule: **use a generator coroutine for a naturally sequential, stateful process, an accumulator, a parser, a
pipeline stage, that consumes a stream of inputs; use a class when the state must be a first-class object with a
broader interface** (many methods, inspection, serialization, identity beyond the sequence). The coroutine is
not faster (§70.3), it is *clearer* for sequential state.

---

## 70.3 Measurement: coroutine vs class

**Methodology.** `code/ch070/bench_coroutine_vs_class.py`. Feeding 1000 values into a running-average generator
coroutine (via `send`) versus a class (via an `update` method). `min` per call; ratio relative to the class.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| feed 1000 values | min per call | ratio |
|---|---|---|
| class (`update` method) | **60,010 ns** | 1.00x |
| generator coroutine (`send`) | **56,676 ns** | **0.94x** |

The two are **essentially equal** (the coroutine is a hair faster here, well within run-to-run variation). This
is the important contrast with Chapter 69: there, a generator *producer* beat a class 2x, because the class paid
a `__next__` *method call* per item while the generator resumed a C frame with no per-item call. Here, both the
coroutine's `send` and the class's `update` are *calls per item*, so the per-item cost is the same, and the 2x
advantage disappears. The coroutine that *receives* data pays a call just like the class.

So the measurement makes the point precisely: **choose a coroutine over a class for expressiveness, not
performance.** When the process is a sequential state machine consuming a stream, the coroutine expresses it as
straight-line code with implicit state and free cleanup, at the same cost as a class. When you need an object
with a rich interface, use a class. Neither is a performance decision; the §70.3 parity is what frees you to
choose on clarity. (This is also why native `async`/`await`, which grew out of these coroutines, is about
*expressing* concurrency clearly, not about raw per-call speed, Chapters 10-11.)

---

## 70.4 Edges and failure modes

**Sending into an un-primed generator.** §70.1. `send(value)` before the generator has reached its first `yield`
raises `TypeError`. Prime with `next(gen)` (or `gen.send(None)`) first. A common fix is a priming decorator that
calls `next` for you.

**Forgetting to `close` a resource-holding coroutine.** A coroutine that holds a resource (file, connection) in a
`try/finally` around its `yield` only runs cleanup on `close` (or garbage collection, which is nondeterministic).
Call `close` explicitly, or use it where lifetime is managed.

**`StopIteration` from `send`/`next` at the end.** When a coroutine's function returns, `send`/`next` raises
`StopIteration` (with the return value as `.value`). Handle exhaustion; do not let `StopIteration` leak (PEP
479, Chapter 69).

**`throw` into a coroutine without a handler.** If the coroutine does not catch the thrown exception, it
propagates out of `throw` and the coroutine is finished. `throw` continues the coroutine only if it *handles*
the exception around its `yield`.

**Confusing generator coroutines with native `async` coroutines.** These `yield`-based coroutines are the
*historical* mechanism; modern async uses `async def`/`await` (Chapters 10-11), which is a different, dedicated
object (`@asyncio.coroutine` and `yield from`-based coroutines are deprecated/removed). Use `async`/`await` for
async I/O; use generator coroutines for the synchronous state-machine pattern.

**Two-way `yield` reducing readability.** A `value = yield result` that both sends and receives can be hard to
read if overused. For a pure producer, use plain `yield` (Chapter 69); reserve two-way `yield` for genuine
coroutines.

---

## 70.5 Connections

**Backward.** The producer side of generators (plain `yield`, the iterator protocol) is Chapter 69; this chapter
adds the receiving side. The laziness and single-pass nature carry over from Chapter 9. The `try/finally` that
`close` triggers is the exception/cleanup model of Chapters 6 and 5 (context managers).

**Forward.** `yield from` (delegating to a sub-generator, transparently forwarding `send`/`throw`/`close`) is the
next Deep F chapter, and the bridge to `asyncio`'s original coroutine model. Native `async`/`await` and the event
loop (Chapters 10-11) are the modern descendant. The C-level generator frame that holds the suspended state is a
**Deep J** topic.

**Across books.** Generator coroutines are how Book II expresses streaming, stateful transformations for
**Book III**. A **Book III** pipeline stage that maintains rolling state (a running statistic, a windowed
aggregate, an incremental parser over a token stream) is naturally a coroutine, fed with `send`, torn down with
`close`, at the same cost as a class but far clearer. The §70.2 "state machine without boilerplate" property is
what keeps such stages readable. **Deep U** owns the streaming-stage seam; the async descendant powers the
concurrent I/O.

---

## 70.6 Exercises

**1. Build a coroutine.** Write a running-average (or running-max) coroutine, prime it, and feed values with
`send`. Confirm it maintains state across calls. Explain where the state lives and why priming is required.

**2. Clean up on close.** Write a coroutine that acquires a resource in a `try` and releases it in `finally`, and
show the release runs on `close`. Explain what `GeneratorExit` does.

**3. Recover with throw.** Write a coroutine that catches an injected exception around its `yield` and continues.
Show `throw` handled-then-continues versus `throw` unhandled-then-finished. Explain the difference.

**4. Measure the parity.** Run §70.3's benchmark and confirm the coroutine and class are about equal, then
contrast with Chapter 69's 2x for pure iteration. Explain why the receiving case pays a call per item either way.

**5. The design question.** A generator coroutine expresses a sequential state machine as straight-line code with
implicit state, at the same speed as a class. Argue when to prefer each. Your answer must use the §70.3 parity,
contrast with Chapter 69's producer speedup, and identify the sequential-stream cases where a coroutine is
clearest and the object cases where a class is.

---

## 70.7 Summary and cross-references

- **`yield` is two-way:** `value = yield result` sends `result` out and receives the next value via **`send`**,
  turning a generator into a **coroutine** whose state lives in locals across suspensions. Prime with `next`
  before the first `send`.
- **`close`** raises `GeneratorExit` (runs a `try/finally` for cleanup); **`throw`** injects an exception at the
  suspension point (the coroutine can handle it and continue).
- **Measured:** feeding 1000 values into a coroutine costs about the **same** as a class's update method (0.94x),
  because both pay a call per value, unlike Chapter 69's producer, where the generator was 2x. Choose a coroutine
  for **expressiveness, not speed**.
- **Use a coroutine for a sequential, stateful stream process** (accumulator, parser, pipeline stage); use a
  class for a rich-interface object. These are the historical basis of `asyncio`; use `async`/`await` for async
  I/O.

**Cross-references.** Generator producers and the protocol → Chapter 69. Laziness → Chapter 9. `try/finally` and
context managers → Chapters 6, 5. `yield from` and async → the next Deep F chapter and Chapters 10-11. The
generator frame → Deep J. The streaming-stage seam → Deep U.
