# Chapter 71: `yield from` Delegation

A generator wraps another generator, and the obvious way to forward its values is a loop: `for x in subgen:
yield x`. For a plain producer that works. But make `subgen` a coroutine, one you `send` values into, and the
wrapper silently breaks: the sent values reach the *wrapper's* `yield`, not `subgen`, so `subgen` receives
`None` every time. The manual loop forwards *values* but not the two-way protocol. `yield from subgen` is the
fix: it delegates *transparently*, forwarding every yielded value, routing `send`/`throw`/`close` straight to
`subgen`, and capturing `subgen`'s **return value** as the value of the `yield from` expression, none of which
the manual loop does. And for deep delegation chains it is faster too, **1.4x** through a depth-50 chain, because
it delegates more directly than a stack of re-yield loops.

This chapter continues **Deep F** with `yield from` (PEP 380): what transparent delegation means, why a manual
re-yield loop is a broken substitute for coroutines, and its efficiency for deep chains. It composes the
generators of Chapter 69 and the coroutines of Chapter 70, and it was the mechanism the original `asyncio`
coroutines were built on.

## Section index

- **71.1** Transparent delegation
- **71.2** Why the manual loop is not equivalent
- **71.3** Measurement: deep delegation chains
- **71.4** Edges and failure modes
- **71.5** Connections
- **71.6** Exercises
- **71.7** Summary and cross-references

Listings live under `code/ch071/` and are re-executed by `make verify` on both interpreters.

---

## 71.1 Transparent delegation

```python
# code/ch071/l01_yield_from.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- yield from captures the sub-generator's return value ---
  [1, 2, "result was: the sub-generator's result"]
--- yield from forwards send() to the sub-generator ---
  yield from : ['echo received A', 'echo received B']
--- a manual re-yield loop does NOT forward send (values are lost) ---
  manual loop: ['echo received None', 'echo received None']  (echo never received the sent values)
--- yield from flattens a nested structure cleanly ---
  flatten([1,[2,[3,4]],5]) : [1, 2, 3, 4, 5]
```

`yield from subgen` does three things a bare `yield` cannot. It **forwards values**: every value `subgen` yields
passes through to the caller (the flatten example delegates recursively to produce `[1, 2, 3, 4, 5]`). It
**captures the return value**: when `subgen` returns (Chapter 70), that return value becomes the value of the
`yield from` expression, `result = yield from leaf_returns()` binds `result` to `"the sub-generator's result"`,
which a `for` loop has no way to capture. And it **forwards the two-way protocol**: `send`/`throw`/`close` from
the caller go straight to `subgen`. The listing sends `"A"` and `"B"` through a `yield from` wrapper, and the
inner `echo` coroutine receives them (`echo received A`, `echo received B`).

The contrast in the third block is the point. The *manual* `for x in echo(...): yield x` wrapper forwards values
but *not* `send`: when the caller sends `"A"`, that value arrives at the wrapper's own `yield x`, where the
`for` loop discards it, and `echo`'s bare `yield` just produces `None`. So `echo` receives `None`, `None`, the
sent values were *lost*. The manual loop is a lossy imitation of delegation.

---

## 71.2 Why the manual loop is not equivalent

The equivalence people assume, `yield from g` is just `for x in g: yield x`, holds *only* for a one-way producer
that no one sends into, throws into, or reads a return value from. The moment any of those is true, the manual
loop is wrong:

- **`send`** reaches the wrapper's `yield`, not the delegate's, so the delegate never receives sent values
  (the listing's `None`s). A coroutine delegated to by a manual loop is deaf.
- **`throw`** raises at the wrapper's `yield`, not inside the delegate, so the delegate cannot handle an injected
  exception, and the wrapper's loop is interrupted instead.
- **`close`** closes the wrapper, not necessarily the delegate cleanly, so the delegate's `finally` may not run
  as intended.
- **The return value** of the delegate is discarded, the manual loop has no expression to capture it.

`yield from` handles *all* of these correctly, it is defined (PEP 380) precisely as the full, transparent
delegation protocol, not sugar for a loop. The mental model: `yield from g` makes the caller and `g` behave as
if `g`'s `yield`s were happening *directly in the caller*, with the wrapper stepping out of the way. That
transparency is why it is the *only* correct way to delegate to a coroutine, and why it became the composition
primitive for the original `asyncio` (`@coroutine` functions delegated with `yield from` before `async`/`await`
replaced them).

The rule: **use `yield from` to delegate to a sub-generator or coroutine; never hand-roll `for x in g: yield
x`.** Even when the delegate is currently a plain producer, `yield from` is clearer and future-proofs the
delegation if the delegate ever becomes a coroutine or grows a return value.

---

## 71.3 Measurement: deep delegation chains

**Methodology.** `code/ch071/bench_yield_from.py`. Consuming a sequence delegated through a **depth-50** chain of
generators, built with `yield from` versus manual `for`-`yield` re-yielding at each level. `min` per call; ratio
relative to `yield from`. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| delegate through 50 levels | min per call | ratio |
|---|---|---|
| `yield from` (depth 50) | **63,861 ns** | 1.00x |
| manual re-yield (depth 50) | **91,205 ns** | **1.43x** |

Through a depth-50 chain, `yield from` is **1.43x** faster. Each value produced at the leaf must travel up
through all 50 levels to the consumer; the *manual* chain suspends and resumes a `for`-`yield` frame at *every*
level per value, while `yield from` delegates more directly (the delegation chain is walked more efficiently
than re-yielding through 50 Python loops). At a single level the two are equal (there is nothing to short-
circuit); the advantage appears and grows with *depth*, which is exactly when delegation chains matter, deeply
composed generator pipelines.

The rule: **`yield from` is both the correct and (for deep chains) the faster delegation.** The correctness
(§71.1-71.2) is the primary reason, it is the only way to transparently forward the coroutine protocol and
capture return values, and the efficiency for deep chains is a bonus. A pipeline of composed generators (a
common shape in streaming code) should delegate with `yield from` at each stage, both because it is right and
because it does not accumulate per-level re-yield overhead. As with the rest of Deep F, the idiomatic construct
is also the better-performing one.

---

## 71.4 Edges and failure modes

**Manual re-yield for a coroutine.** §71.1. `for x in g: yield x` does not forward `send`/`throw`/`close` or
capture the return value. Use `yield from` whenever the delegate is or might become a coroutine, or has a return
value.

**Ignoring the delegate's return value.** `yield from g` *is* an expression; its value is `g`'s return. Writing
`yield from g` as a bare statement discards that. Bind it (`result = yield from g`) when the delegate returns
something meaningful.

**Deep manual chains.** §71.3. Re-yield loops accumulate per-level overhead through a deep chain. `yield from`
delegates more directly; prefer it in composed pipelines.

**`yield from` a non-generator iterable.** `yield from` works on any iterable (it iterates it), but the `send`/
`throw` forwarding only *matters* for generators/coroutines; delegating to a plain list just forwards its values.
Do not expect two-way behavior from a delegate that is not a generator.

**Confusing `yield from` with `await`.** In modern async code, `await` (not `yield from`) delegates to a
coroutine. `yield from`-based coroutines are the *historical* async mechanism (removed/deprecated for async
use); `yield from` remains valid for *generator* delegation. Use `await` for async, `yield from` for generators.

**Exceptions from the delegate.** An exception raised inside the delegate (not injected via `throw`) propagates
through the `yield from` to the caller, as if raised there. Handle it around the `yield from` if the wrapper
should recover; otherwise it ends both.

---

## 71.5 Connections

**Backward.** The producer generators being delegated to are Chapter 69; the `send`/`throw`/`close`/return
protocol `yield from` forwards is Chapter 70. The recursion in the flatten example is ordinary function
recursion (the delegate is a recursive call). The exception propagation is Chapter 6.

**Forward.** Native `async`/`await` (Chapters 10-11) replaced `yield from` for *async* coroutines but is its
direct descendant, `await` is to async coroutines what `yield from` was. Composed generator pipelines are a
streaming pattern in **Deep U**. The C-level delegation is a **Deep J** interpreter topic.

**Across books.** `yield from` is how Book II composes streaming stages into pipelines for **Book III**. A
**Book III** ingest pipeline built from nested generators (a source delegating to a windower delegating to a
batcher) uses `yield from` at each seam, so values flow through transparently, any coroutine control (backpressure
via `send`, cancellation via `close`) propagates correctly, and deep composition does not accumulate re-yield
overhead. The §71.1 send-forwarding is what makes such a pipeline controllable end to end. **Deep U** owns the
pipeline-composition seam.

---

## 71.6 Exercises

**1. Break send with a manual loop.** Reproduce §71.1: delegate to a coroutine with `yield from` and with a
manual `for`-`yield` loop, and show `send` reaches the delegate only through `yield from`. Explain where the
sent value goes in the manual case.

**2. Capture a return value.** Write a sub-generator that `return`s a value, delegate to it with `yield from`,
and capture the return. Show a `for` loop cannot. Explain the `yield from` expression semantics.

**3. Measure deep delegation.** Run §71.3's benchmark and confirm `yield from` beats a manual chain at depth 50,
then reduce the depth to 1 and show they converge. Explain why the advantage is depth-dependent.

**4. Flatten with delegation.** Write a recursive `flatten` using `yield from` for nested lists, and explain why
`yield from` on the recursive call is cleaner than a nested loop.

**5. The design question.** `yield from` is defined as full transparent delegation, not sugar for a re-yield
loop. Argue why the language needed a dedicated construct. Your answer must use the §71.1 send-forwarding and
§71.3 depth measurement, explain what the manual loop cannot do, and connect `yield from` to `await`.

---

## 71.7 Summary and cross-references

- **`yield from subgen`** delegates *transparently*: it forwards yielded values, routes **`send`/`throw`/`close`**
  to `subgen`, and **captures `subgen`'s return value** as the expression's value.
- A **manual `for x in subgen: yield x` loop is not equivalent:** it forwards values but not `send`/`throw` (sent
  values reach the wrapper, so the delegate receives `None`) and discards the return value. Use `yield from` for
  any generator/coroutine delegation.
- **Measured:** through a depth-50 chain, `yield from` is **1.43x** faster than manual re-yielding (64 us vs 91
  us); at one level they are equal. The advantage grows with delegation depth.
- **`yield from` is the correct and (deep) faster delegation;** it was the basis of the original `asyncio`
  coroutines. Use `await` for modern async, `yield from` for generator delegation.

**Cross-references.** Generator producers → Chapter 69; coroutine `send`/`throw`/`close` → Chapter 70. Exceptions
→ Chapter 6. `async`/`await` (the descendant) → Chapters 10-11. Delegation internals → Deep J. The pipeline-
composition seam → Deep U.
