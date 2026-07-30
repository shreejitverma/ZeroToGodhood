# Chapter 102: Coroutines and the Awaitable Chain

Chapter 101 said the loop sees only callbacks and futures; your code says `async def` and `await`. This chapter is the machinery between the two, and it is small enough to drive **by hand**: a coroutine is an inert object until something calls `send` on it; its return value travels *inside* `StopIteration`; and `await` is delegation that **flattens**, so ten layers of coroutines still present exactly one suspension to the loop.

The listing proves each clause without an event loop in sight, calling `send(None)` directly and catching the `StopIteration` that carries `42`, then driving a three-layer chain through a hand-written awaitable and watching one resume finish all three layers at once. The benchmark then prices the two quantities the mechanism separates: a **layer** costs ~37 ns, a frame entered and left through the delegation machinery, and a **suspension** costs ~27,000 ns, a full trip through Chapter 101's loop. The design rule falls out at 700x: factor async code as freely as sync code; budget the *loop trips*, not the depth.

**This is a Deep J chapter.**
Deep F owns the engine, generators, `send`, `throw`, and `yield from`; Volume 11 owns the syntax's arrival. This chapter owns the awaitable *protocol*: what `await` accepts, what it traverses, and what each part costs.

## Section index

- **102.1** The protocol, driven by hand
- **102.2** The machinery: delegation, flattening, and the return channel
- **102.3** Measurement: layers against suspensions
- **102.4** Edges and failure modes
- **102.5** Connections
- **102.6** Exercises
- **102.7** Summary and cross-references

Listings live under `code/ch183/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 102.1 The protocol, driven by hand

```python
# code/ch183/l01_the_await_chain.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- a coroutine is inert until driven ---
  calling an async def returns : coroutine
  send(None) ran the body; the RETURN VALUE rides in StopIteration.value : 42
  no loop was involved: the loop is a consumer of this protocol,
  not its owner. Deep F's generators, wearing a contract
--- the awaitable protocol, driven by hand ---
  first send(None) suspended, yielding : 'SUSPEND-TOKEN'
  resuming with a value finished it    : ('resumed with', 'a-result-from-outside')
  that is the whole contract: yield to suspend, StopIteration.value
  to return. Futures, Tasks, and sleep() are all spellings of it
--- await flattens: three layers, ONE suspension ---
  outer -> middle -> inner -> ManualAwaitable, one send reached
  the bottom and surfaced its token        : 'SUSPEND-TOKEN'
  one resume finished ALL THREE layers     : ('resumed with', 'loop-says-go')
  await compiles to delegation (Deep F's yield from): the stack of
  coroutines suspends AS A UNIT and resumes as a unit. depth adds
  frames, never extra trips through the loop (the benchmark prices
  the frames)
--- the failure mode the machinery watches for ---
  create-and-drop a coroutine warns : True
```

**The inertness block is the fact most async bugs trace back to.**
`answer()` executes none of `answer`'s body; it builds a coroutine object, Deep F's generator-shaped frame in suspended-at-start state. `send(None)` runs the body, and the `return 42` surfaces as `StopIteration(42)`, the same return channel `yield from` used, because it *is* that channel. No loop participated: the loop is a consumer of this protocol, not its owner, which is why Chapter 101's toy-loop exercise is possible and why testing coroutines by hand-driving them is a legitimate technique.

**The `ManualAwaitable` block is the whole protocol in six lines.**
`__await__` returns an iterator; each `yield` in that iterator suspends everything above it; the value sent back in resumes it; `StopIteration.value` is the result of the `await` expression. `Future.__await__`, `Task.__await__`, and `asyncio.sleep` are three spellings of exactly this, differing only in what the yielded token means to the loop (a future to watch, Chapter 103).

**The flattening block is the load-bearing measurement setup.**
One `send(None)` on `outer` reached down through `middle` and `inner` to the hand-made awaitable and surfaced its token; one `send` back finished all three layers. The chain suspends **as a unit** and resumes as a unit; intermediate layers add frames, never extra trips through the loop. §102.3 prices the difference at 700x.

**And the warning block is the safety net for the inertness.**
A coroutine created and dropped without being awaited dies undriven, and its destructor warns, because the call site looked exactly like a function call that did its work. `foo()` versus `await foo()` is the async world's most-shipped one-token bug, and "coroutine was never awaited" in the logs is its only symptom.

---

## 102.2 The machinery: delegation, flattening, and the return channel

**`await x` compiles to Deep F's delegation.**
The bytecode obtains an iterator from `x`, a coroutine is its own iterator; otherwise `type(x).__await__(x)`, and then runs the `yield from` protocol against it: forward `send` and `throw` downward, surface every `yield` upward, and catch `StopIteration` to produce the expression's value. The flattening in §102.1 is not an optimisation; it is what delegation *means*: the top of the chain holds one suspended frame stack, and the loop's `send` lands at the bottom in one hop.

**The awaitable taxonomy is three entries and a rule.**
A **coroutine** may be awaited exactly once (a second await raises `RuntimeError`); a **Future/Task** may be awaited by many waiters and is the loop's unit of watching (Chapter 103); and **anything with `__await__`** joins the chain, which is how libraries interoperate without inheriting from asyncio. The rule: whatever reaches the bottom must eventually yield something the driving loop understands, asyncio's loop understands its futures, and yielding anything else to it is the cross-framework incompatibility (§102.4).

**The return channel explains the exceptions too.**
`return v` becomes `StopIteration(v)` internally, which is why a bare `StopIteration` raised *inside* async code would corrupt the protocol, and why PEP 479 (Deep F) made that a `RuntimeError` years before asyncio depended on it. Exceptions other than `StopIteration` propagate up the chain unchanged, `throw` is forwarded downward the same way `send` is, which is what makes `try`/`finally` and `async with` inside coroutines behave normally across suspensions, and what cancellation will ride in on (Chapter 103's `CancelledError`).

**Nothing in this chapter is concurrent.**
Every mechanism here is single-threaded, deterministic, and loop-free, the concurrency arrives only when Chapter 103's Task hands the yielded future to Chapter 101's selector-and-queue. Keeping the layers separate is what makes asyncio explicable at all: Deep F's engine, this chapter's protocol, 103's scheduling, 101's loop.

---

## 102.3 Measurement: layers against suspensions

**Methodology.** `code/ch183/bench_await_depth.py`.
100,000 awaited calls per row, `min` of 5 runs, 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. Depth without suspension.**

| chain | per await | marginal |
|---|---|---|
| 0 extra layers | 39 ns | — |
| 1 extra layer | 73 ns | +34 ns |
| 5 extra layers | 233 ns | +39 ns/layer |
| 10 extra layers | 405 ns | **+37 ns/layer** |

A layer is a frame: creating the coroutine object, entering its frame through the delegation machinery, and unwinding it through `StopIteration`. Thirty-seven nanoseconds is Chapter 55's call-overhead arithmetic in its async costume (the async path carries the extra object and the exception-based return, roughly doubling a plain call), and it is **linear and small**.

**b. The suspension.**

| awaiting a Future | per await |
|---|---|
| already completed (no loop trip) | 179 ns |
| pending, completed by `call_soon` (one loop trip) | **27,139 ns** |

The done-future path never leaves the coroutine stack: `__await__` sees the result and returns it, 179 ns. The pending path parks the entire chain, returns to Chapter 101's loop, runs the queued callback, and resumes the chain: ~27 us on this machine, the loop-iteration constant from Chapter 101 paid going down and coming back. **One suspension costs ~700 layers.**

**The design rule the ratio dictates.**
Write small `async def`s with clear names, exactly as you factor sync code; ten layers cost less than half a microsecond. Spend the optimisation attention where the suspensions are: await things that are usually already complete (the done-future row is why caching and buffering matter doubly in async code), batch small awaits into fewer larger ones (Chapter 106's read sizes), and treat every avoidable loop trip as ~27 us of latency injected into *this* request and queueing delay injected into every other task behind it. **Book I**'s reactor has the same two-tier price list, function calls in nanoseconds, epoll trips in microseconds, and the same conclusion drawn in its handler-design chapter: the loop trip is the unit of budget.

---

## 102.4 Edges and failure modes

**The missing `await` fails silently at the call site.** §102.1.
The call constructs a coroutine and discards it; no body runs; the only symptom is the destructor's `RuntimeWarning`, possibly much later, possibly swallowed by logging config. Treat "coroutine was never awaited" as an error in CI (`-W error::RuntimeWarning` scoped appropriately), because it always means a code path did nothing where it meant to do something.

**A coroutine awaits once.**
The object is its own frame; after completion it is spent, and a second `await` raises `RuntimeError("cannot reuse already awaited coroutine")`. When two consumers need one result, they must share a **Task** (Chapter 103), which is a Future and supports multiple waiters, not the raw coroutine.

**`__await__` must return an iterator, and its yields must speak the driver's language.**
Yielding arbitrary values suspends fine under hand-driving (§102.1) but crashes or hangs under a real loop that expects its own futures. This is also why mixing frameworks' awaitables (asyncio, Trio, Curio) fails at the bottom of the chain even though `await` accepts them syntactically: the protocol is shared, the *token vocabulary* is not.

**`StopIteration` is load-bearing; do not raise it across this machinery.**
PEP 479 turned an accidental leak inside generators into `RuntimeError`, and the same discipline applies around awaitables: an iterator-protocol result channel means user `StopIteration` is protocol corruption. If a value-or-end signal is needed, use a sentinel or an exception of your own.

**`asyncio.iscoroutinefunction` and friends lie at the edges.**
Wrapped callables (`functools.partial`, decorators that return plain functions calling async ones) defeat introspection-based dispatch. The robust test is behavioural, call it and check for a coroutine, or better, design APIs that take *awaitables* rather than sniffing callables.

**Depth is cheap; recursion still is not.**
Thirty-seven nanoseconds a layer comes with a frame per layer on the regular Python stack while running between suspensions; an unbounded-recursive `async def` hits the same recursion limit as sync code (Chapter 54). Deep pipelines are fine; unbounded depth needs the same restructuring it always did.

**And the never-awaited warning depends on collection.**
On the free-threaded build, Chapter 95 taught that some objects die at the next GC rather than at the drop; the listing forces `gc.collect()` for exactly this reason. Warning-based tests must do the same or flake by build.

---

## 102.5 Connections

**Backward.**
The engine, generator frames, `send`/`throw`, `yield from` semantics, and PEP 479, is Deep F, and this chapter is its contract-layer sequel. Frames and the call-overhead arithmetic the layer cost echoes are Chapters 54 and 55. The loop that consumes the protocol, and the iteration constant the suspension price contains, are Chapter 101. The syntax's history is Volume 11.

**Forward.**
The Task, which wraps a coroutine in a Future, drives its `send`s from the ready queue, and routes its yielded futures to the selector, is Chapter 103, along with cancellation, `throw` wearing `CancelledError`. Structured concurrency builds on Tasks, Chapter 104. The coordination objects are Chapter 105; their awaits are exactly §102.3b's pending-future row, which is why their costs surprised in Chapter 101. Streams and the read-size arithmetic that minimises suspensions, Chapter 106.

**Across books.**
`await`'s flattening is stackless-coroutine delegation, and C++20 coroutines made the mirror-image choice: compiler-generated state machines with the *frame* allocation visible and the suspension cheap, where Python keeps frames on the heap and pays the loop trip. **Book I**'s chapter on C++ coroutines measures the same two quantities, layer cost and suspension cost, and lands on the same engineering rule with the constants shifted three orders of magnitude down.

---

## 102.6 Exercises

**1. Drive everything by hand.** Extend the listing: drive `asyncio.sleep(0)` manually with `send` and inspect what it yields; then drive a real `Future` the same way. Identify the token vocabulary asyncio's loop actually speaks.

**2. Price your layers.** Reproduce §102.3a, then repeat with each layer carrying two local variables and a `try/finally`. Report what realistic function bodies do to the 37 ns marginal.

**3. Find a missing await.** Grep a real async codebase for calls to `async def`s whose results are discarded. Build the CI configuration that turns the never-awaited warning into a failure, and count what it catches.

**4. Break the vocabulary.** Write an awaitable that yields a plain string, await it under `asyncio.run`, and capture exactly how the loop reacts. Then explain the error in terms of §102.2's taxonomy.

**5. The done-future dividend.** Build a tiny read-through cache in front of a slow async fetch, returning completed futures on hits. Measure hit-path latency against miss-path and against no-cache, and reconcile with §102.3b's two rows.

**6. The design question.** Python chose stackless coroutines with an explicit `await` at every suspension point, against goroutine-style stackful coroutines where any call may suspend invisibly. Argue the choice: what the explicit marks buy for Chapter 101's determinism and Chapter 99's race analysis (every suspension is visible in the diff), what they cost (the two-color problem, Chapter 107, and the missing-await bug class), and why a runtime with a GIL-shaped history had reasons C and Go did not. Then state which single consequence of the choice this chapter measured, and where the 27 us would go under the alternative.

---

## 102.7 Summary and cross-references

- **The protocol**: a coroutine is inert until `send`; results ride in `StopIteration.value`; `__await__` returns an iterator whose yields suspend and whose completion is the awaited value. Futures, Tasks, and `sleep` are spellings of it; no loop required.
- **`await` is delegation and it flattens**: k layers suspend and resume as one unit, one trip to the loop, verified by hand-driving a three-layer chain.
- **Measured**: a layer costs **~37 ns** (frames, Chapter 55's arithmetic); a real suspension costs **~27,000 ns** (Chapter 101's loop trip, both ways); an already-done future costs 179 ns. **One suspension ~ 700 layers**: factor freely, budget loop trips.
- **The bug class**: a missing `await` does nothing, silently, at the call site; the never-awaited `RuntimeWarning` is the only symptom, and it deserves promotion to an error in CI. Coroutines await once; share Tasks instead.
- **The vocabulary rule**: syntax accepts any awaitable, but the bottom of the chain must yield tokens the driving loop understands, which is where cross-framework mixing actually fails.

**Cross-references.** The engine → Deep F. Frames and call overhead → Chapters 54, 55. The loop and its iteration constant → Chapter 101. Tasks and cancellation → Chapter 103. Structured concurrency → Chapter 104. Coordination objects → Chapter 105. Streams and read sizes → Chapter 106. The two-color problem → Chapter 107.
