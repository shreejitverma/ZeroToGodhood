# Chapter 103: Tasks, Futures, and Cancellation

Chapter 102 left a gap on purpose: a coroutine is a protocol object, and *something* must call `send` on it, catch what it yields, and know what the yielded futures mean. That something is the **Task**: a Future with a driver attached, which wraps a coroutine, feeds it resumes from Chapter 101's ready queue, and routes every yielded future to the loop's watching machinery. Tasks are where asyncio's *concurrency* actually lives, and where its most consequential contract lives too: **cancellation**, delivered as a `CancelledError` thrown into the coroutine at its current `await`.

The listing pins the contract down with deterministic order proofs. A task's body starts on the *next* loop iteration, not at `create_task`, unless the eager factory (3.12) is installed, in which case it runs synchronously to its first await, and the benchmark prices that difference at **52x** for tasks that complete immediately (26,899 ns against 517), because the default start is exactly Chapter 102's 27 us suspension, paid before the body runs at all.

And cancellation is walked through all three of its behaviours: the honest path (cleanup in `finally`, re-raise, `cancelled() == True`), the **suppression trap** (catch and swallow, and the canceller is lied to: `cancelled() == False`, a result appears), and `shield`, which cancels the *wait* rather than the *work*.

**This is a Deep J chapter.**
Chapter 102 owns the protocol underneath; Chapter 104 owns the structured API that manages tasks in groups. This chapter owns the Task itself: lifecycle, Future semantics, and the cancellation contract everything above depends on.

## Section index

- **103.1** The Task's contract, proven in order
- **103.2** The machinery: driver, future state, and the cancellation path
- **103.3** Measurement: creation, the eager dividend, fan-out bookkeeping
- **103.4** Edges and failure modes
- **103.5** Connections
- **103.6** Exercises
- **103.7** Summary and cross-references

Listings live under `code/ch184/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 103.1 The Task's contract, proven in order

```python
# code/ch184/l01_tasks_and_cancellation.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- a task starts on the NEXT iteration, not at create_task ---
  default factory : after-create, child-runs, after-yield
  eager factory   : child-runs, after-create
  by default create_task only QUEUES the first send; the eager
  factory (3.12+) runs the body synchronously to its first await,
  which skips a loop trip for tasks that complete immediately
--- a Task is a Future: many awaiters, one result ---
  awaited the same task four times, one execution : True
  the coroutine ran once (the log would show it); the Task caches
  the outcome as Future state, which raw coroutines cannot (Ch 102)
--- the anatomy of cancel() ---
  working, CancelledError-at-await, finally-ran, awaiter-sees-it, cancelled()=True
  cancel() arranges a CancelledError to be THROWN at the task's
  current await; try/finally and context managers run normally on
  the way out; re-raising marks the task cancelled
--- the suppression trap ---
  caught-and-swallowed, result=i-pretend-nothing-happened, cancelled()=False
  swallowing CancelledError makes cancellation LIE: the canceller
  believes it worked, cancelled() says False, and Chapter 104's
  TaskGroup timeouts depend on the error completing its journey
--- shield: cancelling the wait, not the work ---
  wait_for timed out, shielded task still : 'committed'
```

**The start-order block corrects the most common mental model error.**
`create_task` does not run anything; it queues the first `send` and returns. `after-create` precedes `child-runs` under the default factory, which means code between `create_task` and the next `await` runs *before* the task's body, a fact that both enables patterns (register the task somewhere before it starts) and breaks assumptions (the task has not validated its arguments yet). The eager factory inverts the order: the body runs synchronously to its first await, and a body that never suspends never touches the queue at all, §103.3 prices the difference.

**The Future block is why Tasks exist as a distinct type.**
Chapter 102's raw coroutine awaits once and is spent. The Task caches the outcome as Future state, result, exception, or cancelled, so four awaits observed one execution and one answer. Every fan-out API in this volume (`gather`, `TaskGroup`, `wait`) is built on this multiplicity: many waiters, one completion.

**And the three cancellation blocks are the contract, the violation, and the escape hatch.**
The honest path shows the full itinerary: the error appears *at the task's current await*, `finally` runs on the way out, the awaiter sees `CancelledError`, and `cancelled()` reports `True`. The suppression block shows what breaking the contract looks like from outside: the canceller's `await task` returns a *result*, and `cancelled()` says `False`, cancellation reported success to no one. The shield block is the sanctioned exception: `shield(x)` interposes a cancellable wrapper, so a timeout abandons the *wait* while the work runs to completion for someone else to await.

---

## 103.2 The machinery: driver, future state, and the cancellation path

**The Task's driver is twenty lines of concept.**
On each resume, call `coro.send(value)` (or `throw(exc)`); if it returns a future, attach a done-callback that re-queues this driver with the future's outcome; if it raises `StopIteration`, set this Task's result; any other exception sets this Task's exception. That is the whole bridge from Chapter 102's protocol to Chapter 101's queue, and every behaviour in this chapter falls out of it: start-on-next-iteration is "the first `send` is queued, not called"; the eager factory is "call the first `send` inline"; and Future semantics are "the driver's terminal states are Future states".

**Cancellation rides the `throw` rail.**
`task.cancel()` does not stop anything; it *requests*: if the task is waiting on a future, that future is cancelled, and the driver's next resume becomes `coro.throw(CancelledError)` at the suspension point. Everything ordinary about exceptions applies, `finally` blocks, `async with __aexit__`, exception chaining, which is why cleanup "just works" and why the error being *catchable* is both necessary (cleanup needs to intercept it) and dangerous (§103.1's trap). A task that never awaits is a task that cannot be cancelled, cancellation is cooperative at exactly the same points the scheduler is (Chapter 101).

**The bookkeeping around the contract earns its complexity.**
`cancelling()` counts outstanding cancel requests and `uncancel()` decrements it, added in 3.11 so *structured* consumers of cancellation (timeouts, `TaskGroup`) can distinguish "cancelled from outside" from "cancelled by my own timeout machinery"; Chapter 104 depends on this to decide whether a `CancelledError` should propagate or be converted to `TimeoutError`. User code should almost never call `uncancel`; user code *should* re-raise, and the division of labour is exactly that.

**Futures are the loop's watch-list entries; Tasks are futures that drive.**
A bare `Future` is set by someone (`set_result`, from a callback, a thread bridge, a protocol); a Task is set by its own coroutine's completion. Both support many waiters and done-callbacks; both are what `await` ultimately yields to the loop (Chapter 102's token vocabulary). Understanding "Task **is-a** Future" collapses most of the API surface into one mental object.

---

## 103.3 Measurement: creation, the eager dividend, fan-out bookkeeping

**Methodology.** `code/ch184/bench_task_costs.py`.
10,000 tasks per run, `min` of 5, 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. One task, non-suspending body, created and awaited.**

| factory | per task |
|---|---|
| default | 26,899 ns |
| eager (3.12+) | **517 ns, 52x cheaper** |

The default column *is* Chapter 102's suspension price wearing a Task costume: queue the first send, run the loop, resume, and the ~27 us is the same ~27 us. The eager factory runs the body at `create_task`; a body that completes without suspending never touches the ready queue, and the remaining 517 ns is the Task object, its Future state, and a context copy. For services where many tasks complete immediately, cache hits, validation failures, fast paths, the eager factory converts a loop trip per task into nothing, which is why it exists.

**b. Fan-out bookkeeping, 10,000 trivial coroutines.**

| shape | per coroutine | bookkeeping over floor |
|---|---|---|
| sequential awaits (the floor) | 56 ns | — |
| `gather` | 1,870 ns | +1,815 ns |
| `TaskGroup` | 1,676 ns | +1,621 ns |

The floor is Chapter 102's layer arithmetic (an await of a completing coroutine); the fan-out rows add a Task per coroutine, ~1.7 to 1.9 us of object, future, context, and completion bookkeeping. Two readings matter. First, **fan-out has a fixed per-item cost**, so fanning out 10,000 five-microsecond jobs doubles their cost while fanning out 10,000 five-millisecond I/O waits is free, Chapter 101's amortisation lesson at the API layer. Second, `gather` and `TaskGroup` price within 15% of each other: the choice between them is Chapter 104's semantics, error propagation and cancellation scope, not performance.

**Book I**'s task system prices identically in shape: task-object overhead in the hundreds of nanoseconds, a scheduler trip in the microseconds, and its design rule, batch tiny work, spawn real work, transfers verbatim.

---

## 103.4 Edges and failure modes

**Keep a reference to every task you create.**
The loop holds only weak references; a `create_task` result assigned to nothing can be garbage-collected mid-flight, silently killing the work (and on 3.14t, at a GC-timed moment, Chapter 95). `TaskGroup` holds its children for you, one more reason Chapter 104's API is the default; fire-and-forget needs an explicit registry (`task.add_done_callback(registry.discard)` after `registry.add(task)`).

**A task's unretrieved exception surfaces late and loudly.**
If a task fails and nothing ever awaits it or reads `.exception()`, the error is reported at destruction ("Task exception was never retrieved"), far from its cause, timed by the collector. The fix is structural: await your tasks (Chapter 104), or attach a done-callback that logs.

**`cancel()` is a request with a race window.**
Cancelling a task that is about to complete may lose: the task finishes normally and `cancelled()` is `False`. Callers must treat "requested" and "achieved" as different facts, exactly as the suppression trap forces them to, and check the task's final state rather than assume.

**Catching `CancelledError` obligates you.** §103.1.
Clean up and re-raise. Swallowing it breaks `wait_for`, `timeout`, and `TaskGroup` above you (they *interpret* the error's arrival, Chapter 104), leaves `cancelled()` false, and turns shutdown sequences into hangs. `except Exception` does not catch it (it derives from `BaseException`, moved there in 3.8 for exactly this reason), so ordinary error handling composes; only explicit `except CancelledError` or bare `except:` incur the obligation.

**`shield` protects the work, not the caller, and only once.**
The shielded inner task continues, but the caller's `await shield(x)` still raises `CancelledError`; someone must still await the survivor or it becomes a fire-and-forget with the reference edge above. Shield the small committed core (the payment, the commit), never whole handlers, wide shields are how servers stop responding to shutdown.

**The eager factory changes observable order.** §103.1.
Code that depended on "nothing runs until the next iteration", registering before start, patching before start, breaks under eager start. It is a loop-wide setting; enable it as a deliberate, tested decision, not a drive-by optimisation.

**And context is captured at creation.**
Each Task copies the current `contextvars` context when created (eager or not), so values set *after* `create_task` are invisible to the task. Request-scoped state (Deep F's `contextvars`) must be set before the fan-out point, a rule that bites exactly once per codebase.

---

## 103.5 Connections

**Backward.**
The protocol the driver speaks, `send`, yielded futures, `StopIteration` results, is Chapter 102; the queue that runs the driver and the ~27 us trip it pays are Chapter 101. `BaseException`-hood of `CancelledError` and exception machinery generally are Deep A and Chapter 73's zero-cost `try`. `contextvars` is Deep F.

**Forward.**
`TaskGroup`, which owns child references, propagates errors as groups, converts cancellation correctly via `uncancel`, and makes the structured style the default, is Chapter 104. The coordination objects tasks wait on are Chapter 105; streams whose reads are the futures tasks yield, Chapter 106; bridging threads into the loop with futures, Chapter 107; and the fan-out patterns built on `gather`/`TaskGroup` with semaphores and timeouts, Chapter 108.

**Across books.**
Cancellation-as-thrown-exception is the design C++ deliberately rejected (`std::stop_token` is a flag you poll) and Java embraced (interruption), and the trade is the same in every language: exceptions compose with cleanup automatically but can be swallowed; flags cannot be swallowed but every loop must poll. **Book I** uses stop-tokens and pays the polling discipline; this chapter's suppression trap is the price Python pays instead, and both books' shutdown chapters are consequences of the choice.

---

## 103.6 Exercises

**1. Reproduce the orders.** Run the listing, then add a third variant: `await asyncio.sleep(0)` between create and the log line under the default factory. Predict the order first.

**2. Price your fan-out.** Measure §103.3b with bodies of 10 us, 100 us, and 1 ms of real work. Find the body size where Task bookkeeping drops below 5% and state your service's position relative to it.

**3. Build the registry.** Implement correct fire-and-forget: a `spawn(coro)` helper with a strong registry, done-callback removal, and exception logging. Demonstrate the GC kill it prevents (force a collection mid-flight without the registry).

**4. Audit a shutdown.** Write a server-shaped program with five workers; implement shutdown by cancelling all and awaiting with a timeout. Inject the suppression trap into one worker and show the hang; fix it and show the clean exit. Keep the diff as the case study.

**5. Shield the right thing.** Implement "charge card then send email" where the charge must complete once started but the email may be abandoned. Show under timeout injection that charge-completion is guaranteed and exactly-once, and that the email is correctly abandoned.

**6. The design question.** `cancel()` could have been uncatchable (kill) or a pollable flag (stop-token); asyncio chose a catchable exception plus a bookkeeping counter (`cancelling`/`uncancel`) to let *structured* layers reinterpret it. Argue the choice: what `finally`-based cleanup buys over polled flags in a language built on context managers, what the suppression trap costs in practice, and why 3.11 added the counter instead of making the error uncatchable. Then design the lint rule that would catch the trap statically, and state its false-positive rate on real code you know.

---

## 103.7 Summary and cross-references

- **A Task is a Future with a driver**: it feeds `send` from the ready queue, routes yielded futures to the loop, and stores the outcome as Future state, many awaiters, one execution, proven in order.
- **Start is queued, not immediate**, under the default factory; the eager factory (3.12) runs bodies to their first await at `create_task`, measured **52x cheaper (517 ns vs 26,899)** for non-suspending bodies, the suspension price of Chapter 102, avoided.
- **Fan-out bookkeeping is ~1.7 us per task** (`TaskGroup` 1,676 ns, `gather` 1,870 ns over a 56 ns floor): free around real I/O, dominant around trivial work; choose between them on Chapter 104's semantics.
- **Cancellation is a thrown `CancelledError` at the current await**: cleanup runs, re-raising is the contract, `cancelled()` reports the truth only if the error completes its journey. Swallowing it makes cancellation lie; `shield` cancels the wait, not the work; `cancelling`/`uncancel` exist for structured layers, not for you.
- **The reference rules**: hold every task you create (the loop won't), retrieve every exception (or its report arrives via the GC), and set `contextvars` before the fan-out.

**Cross-references.** The protocol and the suspension price → Chapter 102. The queue → Chapter 101. Structured groups and error semantics → Chapter 104. Coordination objects → Chapter 105. Streams → Chapter 106. Thread bridges → Chapter 107. Patterns → Chapter 108. `contextvars` → Deep F.
