# Chapter 101: The Event Loop

Volume 10 told the story of `asyncio` arriving provisional; Volume 11 gave it syntax; Deep F built the coroutine machinery it runs on. This volume is the system itself, and it opens with the object everything else in it compiles down to: a single-threaded loop that polls a selector, queues what became ready, and drains that queue in FIFO order, each entry running **exactly until its next `await`**.

That last clause is the volume's foundation, and it is why this chapter's listing can be verified byte-for-byte on every interpreter in the matrix: **the interleaving is deterministic**. Two tasks alternating beats produce `a0, b0, a1, b1, a2, b2` on every run, forever, because the schedule is written in the code's `await` points, not rolled by a preemptive scheduler. After Deep L's chapters of loss-rate distributions, this is the other end of the concurrency spectrum: a model where Chapter 99's races are not rare, they are *inexpressible* between awaits.

The price and the payoff are both measured here. The loop's iteration costs ~13.5 us on this machine, dominated by the selector syscall, so a **nearly idle loop hands off control 3.2x slower than two threads do**. But the iteration amortises over everything ready: at a thousand ready tasks the switch falls to **584 ns**, and ten thousand concurrent sleepers cost **1.4 KB each** where a thread costs a C stack. The loop is not a faster thread; it is a cheaper *wait*.

**This is a Deep J chapter, and it opens Deep J.**
Volumes 10 and 11 own the release history; Deep F owns `yield`, coroutine objects, and `send`; Deep E owns threads; Deep L owns parallelism. This volume owns `asyncio` as a working system, and this chapter owns the loop.

## Section index

- **101.1** Determinism, starvation, and FIFO, demonstrated
- **101.2** The machinery: what one iteration is
- **101.3** Measurement: the loop's cost model
- **101.4** Edges and failure modes
- **101.5** Connections
- **101.6** Exercises
- **101.7** Summary and cross-references

Listings live under `code/ch182/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 101.1 Determinism, starvation, and FIFO, demonstrated

```python
# code/ch182/l01_the_loop_is_deterministic.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- interleaving happens exactly at await points ---
  two tasks, three beats each : a0, b0, a1, b1, a2, b2
  perfect alternation, every run: the loop resumes ready tasks in
  order, and each one runs EXACTLY until its next await. schedule is
  code, not chance - the property threads can never offer (Ch 99)
--- a task that does not await starves the loop ---
  hog first, no awaits inside : hog0, hog1, hog2, polite
  the hog finished before polite ran at all: 'async' grants no
  preemption, and one loop iteration runs one task until IT yields.
  blocking the loop blocks every task on it (Chapter 107)
--- the ready queue is FIFO, and call_soon shows it raw ---
  call_soon x3, then sleep(0) : first, second, third, after-sleep(0)
  callbacks queued while a task runs execute in queue order at the
  next iteration; sleep(0) parked the task BEHIND them. one queue,
  strictly FIFO per iteration: that is the whole scheduler
```

**The alternation line is the model's signature.**
Each task runs from resume to its next `await asyncio.sleep(0)`, then goes to the back of the ready queue; the loop drains in order; perfect alternation follows, every run. Nothing in Deep E or Deep L can print that line reproducibly. Determinism is not a debugging convenience bolted on, it *is* the concurrency model: between two awaits, a task owns the loop, and every invariant it temporarily breaks is invisible to every other task.

**The starvation line is the same property read as a liability.**
The hog has no `await`, so it runs to completion before `polite` executes at all. `async def` grants no preemption; it grants *interruptibility at marked points*, and a body without marks is a body that owns the loop until it returns. This scales from a tight loop to a 30 ms JSON parse to an accidental blocking `read()`: the loop's tasks all share one thread, and Chapter 107 is the chapter-length treatment of keeping that thread honest.

**And the `call_soon` line shows the scheduler with the abstractions removed.**
Three callbacks queued while the task runs; the task's own `sleep(0)` parks it *behind* them; the drain is strictly FIFO. There is no priority system, no fairness heuristic, no time slicing: one queue, drained in order, once per iteration. Everything this volume builds, tasks, futures, streams, timeouts, `TaskGroup`, compiles down to entries in that queue, which is why the model fits in one chapter and the *system* takes eight.

---

## 101.2 The machinery: what one iteration is

**One iteration, four steps** (the listing's closing block, expanded):

1. **Compute the poll timeout.** The nearest scheduled timer (`call_later`, `sleep`) bounds how long the loop may block; ready callbacks force a timeout of zero.
2. **Poll the selector.** One syscall (`kqueue` here, `epoll` on Linux, Chapter 106) asks the kernel which file descriptors became ready. This is where a truly idle loop *sleeps*, costing nothing until woken.
3. **Queue what the poll unblocked**, plus any timers now due: each becomes a callback in the ready queue.
4. **Drain the ready queue, FIFO.** Each entry is a callback; for a task, the callback is "resume the coroutine at its suspension point and run until the next `await` (or return/raise)". New entries queued during the drain wait for the next iteration, which is what keeps one iteration bounded.

**A task switch is therefore an append plus a frame resume.**
No syscall, no kernel scheduler, no C stack swap: Deep F's coroutine `send` on a frame that Chapter 54 described, plus one deque append. That is why the busy-loop switch floor in §101.3 is half a microsecond. The *iteration*, by contrast, includes step 2's syscall, which is why the idle-loop handoff costs 13.5 us and why the cost model divides the poll across everything it wakes.

**`await` is the compilation boundary between the two worlds.**
Syntactically it marks where the coroutine may suspend (Volume 11); mechanically it delegates down a chain of awaitables until something yields a Future to the loop's machinery (Chapter 102 owns that chain). The loop never sees your `async def`; it sees callbacks and futures, and the entire async/await surface is sugar over step 4.

**One loop, one thread, per thread.**
`asyncio.run` creates a loop, runs one coroutine to completion, and closes it; a loop belongs to the thread that runs it, and everything scheduled on it runs on that thread. Cross-thread entry exists (`run_coroutine_threadsafe`, `call_soon_threadsafe`, Chapter 107) and is explicit, which after Deep L reads as a feature: the loop's world is single-threaded *by contract*, on every build, including 3.14t, and this chapter's listing verifying identically on the free-threaded build is that contract holding.

---

## 101.3 Measurement: the loop's cost model

**Methodology.** `code/ch182/bench_loop_costs.py`.
Self-timed whole runs, `min` of 5. Within-build comparisons; 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. Per-switch cost against loop busyness** (100,000 total `sleep(0)` yields):

| ready tasks | ns per switch |
|---|---|
| 1 | 13,464 |
| 2 | 6,782 |
| 10 | 1,756 |
| 100 | 647 |
| 1,000 | **584** |

The curve is the cost model with numbers: `per-switch = iteration overhead / ready + resume floor`. The intercept, ~13.5 us, is step 2's selector syscall plus loop bookkeeping; the asymptote, ~560-580 ns, is step 4's append-and-resume. The loop amortises its fixed cost across everything ready, so **the busier it is, the cheaper each switch gets**, the opposite slope of every contended structure Deep L measured.

**b. Directed handoff at concurrency two.**

| A wakes B, B wakes A, 100,000 times | per handoff |
|---|---|
| `asyncio.Event` ping-pong | 13,522 ns |
| `threading.Event` ping-pong | 4,229 ns |

**Threads win this shape by 3.2x**, and the number is kept because the folklore says otherwise. A near-empty loop pays the full iteration per wake with nothing to amortise over, and `asyncio.Event` is Python all the way down where `threading.Event` is C over a futex. Low-concurrency request-response between two parties is not what the loop is for.

**c. The standing army.**

| 200 ms concurrent sleepers | wall time | memory per unit |
|---|---|---|
| 10,000 tasks | 340 ms | 1,406 bytes (tracemalloc peak) |
| 1,000 threads | 243 ms | 2,763 bytes visible **+ ~512 KB C stack each** |

Ten thousand concurrent waits completed in 1.7x the sleep duration, at a frame-and-a-half of memory per waiter; the thread column stops at a thousand because ten thousand OS threads is not something to do to a laptop, *which is the result*. A task's unit of concurrency is a suspended frame (Chapter 54); a thread's is a kernel object with a stack. This table is why every high-fan-out network service in Python looks like Chapter 108.

**The three tables are one sentence**: the loop loses in the small, amortises in the middle, and is the only game in town in the large, and none of it applies to CPU-bound work, which cannot await its way to parallelism and belongs to Deep L's primitives via Chapter 100's composition rule. **Book I**'s trading gateway is the same architecture with the constants shrunk: an epoll loop over thousands of connections, handoffs measured in hundreds of nanoseconds, and the identical clause that nothing on the loop thread may block.

---

## 101.4 Edges and failure modes

**Blocking the loop blocks everything, and nothing warns you by default.**
A synchronous `requests.get`, a big `json.loads`, a `time.sleep` inside a coroutine stalls every task on the loop for its duration; §101.1's hog is the minimal case. Debug mode (`PYTHONASYNCIODEBUG=1` or `asyncio.run(debug=True)`) logs callbacks exceeding 100 ms; Chapter 107 owns the fixes (`to_thread`, executors).

**`sleep(0)` is a yield, not a nap.**
It re-queues the task behind everything currently ready, nothing more. Sprinkling it through CPU-bound code makes the starvation intermittent instead of absent, at ~13.5 us a sprinkle on an idle loop; it is a fairness valve for *occasional* long computations, not a license for them.

**Determinism is per-loop, not per-program.**
The schedule is deterministic given the same readiness sequence. Real I/O arrival order is not deterministic, so production interleavings vary *at the granularity of awaits*, a coarser and far more testable nondeterminism than threads' (any-bytecode), but not zero. Tests that fake the I/O (feed readiness in fixed order) recover full determinism, which is why async code is so much more testable than threaded code, Chapter 108 leans on this.

**Callbacks queued during a drain run next iteration.**
A callback that queues itself (`call_soon` from inside a callback) does not starve the poll, the drain is bounded to what was ready when it began, but it does keep the loop from ever sleeping, spinning iterations at ~13.5 us each. The pattern for "run this repeatedly" is a task with awaits, not a self-requeueing callback.

**Timers are lower bounds.**
`call_later(0.05, ...)` fires at the first iteration *after* 50 ms have passed; a long drain or a blocked loop delays it arbitrarily. `sleep(d)` inherits the same clause. Latency-sensitive scheduling on a busy loop needs the busy work off the loop first (Chapter 107); no timer API fixes a stalled step 4.

**One loop per thread; two loops in one thread is an error waiting.**
`asyncio.run` inside a running loop raises; frameworks that need nesting are working against the model. The composition rule is one loop per thread, threads per Chapter 100's table, and explicit `*_threadsafe` bridges between worlds.

**And the loop's constants are platform constants.**
The 13.5 us intercept is a macOS `kqueue` round trip on this machine; Linux `epoll`, Windows IOCP (proactor loop), and `uvloop` all move it, sometimes by a lot. The *shape*, intercept over ready plus floor, survives; re-derive the constants per platform (Chapter 85) before sizing a latency budget.

---

## 101.5 Connections

**Backward.**
The coroutine object, `send`, and suspension are Deep F; the frames being resumed are Chapter 54. The release history, provisional `asyncio` and native syntax, is Volumes 10 and 11. The thread-world this model replaces for waiting, and its Events used as the comparison baseline, are Deep E (Chapter 49). The determinism-versus-races contrast is Chapter 99, and the loop verifying identically on 3.14t is Chapter 93's compatibility story from the other side.

**Forward.**
What `await` actually traverses, coroutines, futures, and the awaitable chain, is Chapter 102. Tasks, scheduling, and cancellation, Chapter 103. Structured concurrency and `TaskGroup` (already used quietly by this chapter's listings), Chapter 104. The async coordination objects whose Python-level cost §101.3b exposed, Chapter 105. The selector under step 2, transports, and streams, Chapter 106. Keeping the loop unblocked, Chapter 107. And the patterns plus the asyncio-versus-threads decision, completing Chapter 100's composition table, Chapter 108, which closes the volume.

**Across books.**
The event loop is the reactor pattern, and **Book I** runs the same design where the stakes are higher: an `epoll` thread that must never block, handlers bounded in the microseconds, and CPU work shipped to worker threads over queues. The two books' loops differ by two orders of magnitude in constants and by nothing in shape, one poll, one drain, one clause, and the shared system's gateway is literally both: `uvloop`-style C loop below, Python handlers above.

---

## 101.6 Exercises

**1. Reproduce the curve.** Run §101.3a on your platform, fit `a/ready + b`, and report your intercept (poll cost) and floor (resume cost). Compare against a Linux box if you have one.

**2. Catch a hog.** Enable debug mode, insert a 150 ms synchronous computation into a task among ten periodic tasks, and capture the slow-callback warning. Then measure the p99 latency impact on the other nine tasks with and without the hog.

**3. Fairness audit.** Write one task that does 1 ms of work per `sleep(0)` and nine that do 10 us. Measure each task's share of a second. Then explain from §101.2's four steps why the loop is fair by *turns*, not by *time*, and what that means for mixed workloads.

**4. Build the smallest loop.** In under 60 lines, implement a toy loop: a ready deque, a timer heap, and `run_until_complete` driving coroutines via `send`. Run this chapter's alternation listing on it unchanged. (Deep F's generator chapters contain every piece.)

**5. Price the bridge.** Measure `run_coroutine_threadsafe` round trips per second from a worker thread into a loop, against `loop.call_soon_threadsafe` with a plain callback, and against a `queue.Queue` handoff to a dedicated loop-side drainer task. Rank and explain.

**6. The design question.** The ready queue is strictly FIFO with no priorities; Twisted, libuv, and most kernel schedulers disagree. Argue CPython's choice: what priorities would do to §101.1's determinism and to starvation analysis (a starved task is now a *policy* outcome, not a bug), what the workaround costs (multiple loops in multiple threads, sized by Chapter 100), and which single scheduling feature you would add if allowed one, defended against the test-reproducibility this chapter demonstrated.

---

## 101.7 Summary and cross-references

- **The model**: one thread, one loop; each iteration polls the selector, queues what woke, and drains the ready queue FIFO, each task running exactly until its next `await`. Everything in asyncio compiles to entries in that queue.
- **Determinism is the foundation**: the interleaving is written in the `await` points, verified byte-identical across 3.13, 3.14, and 3.14t. Between awaits a task owns the loop, no locks needed; a task without awaits owns it abusively (starvation, measured).
- **The cost model, measured**: iteration ~13.5 us (selector syscall) amortised over the ready set, resume floor ~584 ns. Idle-loop handoffs lose to threads **3.2x**; busy-loop switches beat thread switches by ~7x; ten thousand concurrent waiters cost **1.4 KB each** against a thread's C stack.
- **Therefore**: the loop is a cheap *wait*, not a fast *thread*, wrong at concurrency two, unbeatable at concurrency ten thousand, and irrelevant to CPU-bound work (Deep L, via Chapter 100's composition).
- **The clause**: nothing on the loop may block, `sleep(0)` yields but does not absolve, timers are lower bounds, and debug mode is the smoke detector. Chapter 107 is the fire code.

**Cross-references.** Coroutine machinery → Deep F, Chapter 54. Release history → Volumes 10, 11. Threads and Events → Deep E (Chapter 49). Races vs determinism → Chapter 99. Parallelism and composition → Chapter 100. The awaitable chain → Chapter 102. Tasks and cancellation → Chapter 103. `TaskGroup` → Chapter 104. Async primitives' costs → Chapter 105. The selector and streams → Chapter 106. Blocking and executors → Chapter 107. Patterns and the decision → Chapter 108.
