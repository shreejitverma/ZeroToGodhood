# Chapter 107: Blocking and the Bridges

Chapter 101 stated the clause, nothing on the loop may block, and every chapter since has assumed it. This chapter is where the clause meets the installed base: most of Python's libraries are synchronous, most databases ship blocking drivers, and `async def` cannot call them without stalling every task on the loop. This is the **two-color problem**: sync and async functions are different colors, calls only compose within a color, and something must bridge.

The listing proves both halves with event-based order proofs, deterministic on every build. The freeze: a blocking call on the loop waits on a gate that only a queued callback can open, and the callback, *already queued*, cannot run, `work-TIMED-OUT-unreleased` prints before `callback-ran`, every deadlock of this family in one line. The fix: the same code through `asyncio.to_thread` leaves the loop live, the callback fires, the gate opens, `work-done`. And the seam is airtight: `to_thread` carries return values, exceptions, *and* `contextvars` across, and threads re-enter the loop's world through exactly two doors, `call_soon_threadsafe` and `run_coroutine_threadsafe`.

The benchmark prices the doors: **~30 to 42 us per crossing**, against an 85 ns direct call, with the post-only door at 2 us. The rule is Chapter 100's grain rule at the color boundary: free around a 10 ms query, ruinous around a 10 us parser, so **bridge the big, batch the small**.

**This is a Deep J chapter.**
Deep E owns thread pools as machinery; Chapter 100 owns choosing the CPU primitive behind the bridge. This chapter owns the boundary itself: the failure, the doors, and their prices.

## Section index

- **107.1** The freeze and the fix, proven in order
- **107.2** The machinery: pools, future pairs, and the two doors
- **107.3** Measurement: the crossing prices
- **107.4** Edges and failure modes
- **107.5** Connections
- **107.6** Exercises
- **107.7** Summary and cross-references

Listings live under `code/ch188/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 107.1 The freeze and the fix, proven in order

```python
# code/ch188/l01_the_blocking_bridge.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- a blocking call freezes the loop, provably ---
  calling-blocking-work-ON-THE-LOOP, work-TIMED-OUT-unreleased, callback-ran
  the callback was ALREADY QUEUED, and it still could not run: the
  blocking call owns the loop's only thread, so the gate it waits
  for can never open. every deadlock of this family is this shape
  sending-blocking-work-to-a-thread, callback-ran, work-done
  same code, one to_thread: the loop stayed live, ran the callback,
  opened the gate, and the worker finished. to_thread is the
  default bridge for any synchronous call you do not control
--- the bridge carries results, exceptions, and context ---
  return value        : 42
  contextvar in thread: 'req-7'
  exception surfaced  : ValueError('negative')
  to_thread copies the current context (Chapter 103's rule applies)
  and re-raises in the awaiting task: the seam is airtight in both
  directions, which run_in_executor alone does not give you
--- threads re-enter the loop through exactly two doors ---
  door1-callback, coro-ran-door2, door2-returned-DOOR2
```

**The freeze block is a deadlock with a deterministic autopsy.**
The blocking function waits on a `threading.Event` that a queued loop callback will set; the callback cannot run because the blocking function occupies the loop's only thread; the wait times out. The order proof generalises to every member of the family: a blocking driver waiting for a response whose reader-callback is queued behind it, a `future.result()` called on the loop for a future the loop must complete, a synchronous lock whose holder needs the loop to release it. **Anything on the loop that waits for the loop is this listing.**

**The fix block is one function call, and it changes the order, not the code.**
`await asyncio.to_thread(blocking_work, gate)`: the work runs in a pool thread, the loop runs its callback, the gate opens, the work completes. `to_thread` is the default answer for synchronous code you do not control; the finer-grained answers (which pool, what size, process instead of thread) are Chapter 100's table reached through `run_in_executor`.

**The carrier block certifies the seam.**
Return values come back as the await's result; exceptions re-raise in the awaiting task, with the original traceback chained; and `contextvars` set before the call are visible inside the thread, `'req-7'`, because `to_thread` copies the current context, Chapter 103's context rule extended across the color boundary. This is precisely what raw `run_in_executor` does *not* do (no context copy), and the difference is a request-scoped logger working or silently defaulting.

**And the two-doors block is the entire legal interface, exercised.**
From a worker thread: `call_soon_threadsafe` posts a callback and wakes the selector; `run_coroutine_threadsafe` submits a whole coroutine and returns a `concurrent.futures.Future` the *thread* can block on. Everything else in asyncio is single-threaded machinery (Chapter 105's trap), and the listing's clean interleaving, coroutine ran, callback ran, result returned, is what the doors exist to make possible.

---

## 107.2 The machinery: pools, future pairs, and the two doors

**`to_thread` is four pieces glued.**
Capture the current context; submit `context.run(fn, *args)` to the loop's default `ThreadPoolExecutor`; wrap the returned `concurrent.futures.Future` in an asyncio future (`wrap_future`), whose completion is delivered by, this is the subtle part, `call_soon_threadsafe` *from the pool thread* when the work finishes; await the wrapper. Every crossing therefore includes a pool handoff, two future completions, and a selector wakeup, which is where §107.3's ~30 us lives.

**The wakeup is the loop's only cross-thread machinery, and it is a pipe.**
A selector blocked in `kqueue`/`epoll` cannot be woken by setting a flag; the loop keeps a self-pipe (or eventfd) registered, and `call_soon_threadsafe` writes a byte to it after queueing the callback. That byte is the entire difference between `call_soon` (loop-internal, no wakeup needed) and its `_threadsafe` sibling, and why calling the wrong one from a thread *sometimes works*, until the loop happens to be asleep, the classic heisenbug of this boundary.

**Executor choice is policy, not plumbing.**
`run_in_executor(None, fn)` uses the loop's default thread pool (sized `min(32, cpu+4)`); passing a `ProcessPoolExecutor` ships the call to a process instead, with Chapter 98's pickling constraints and Chapter 100's grain arithmetic deciding when that pays. The GIL shapes the thread-pool answer on GIL builds, pool threads parallelise *waiting* and C-releasing calls (Chapter 80), not pure-Python CPU, and the free-threaded build (Chapter 93) quietly upgrades every existing `to_thread` call site into real CPU parallelism, one of 3.14t's least-advertised dividends.

**The doors differ in direction of ownership.**
`to_thread`/`run_in_executor`: the *loop side* owns the operation, and the thread is a servant that must not touch loop objects. `run_coroutine_threadsafe`: the *thread* owns the operation, and the loop is a service; the returned future is a `concurrent.futures.Future`, blocking-`result()` and all, because its consumer is a thread. Confusing the two directions, a thread awaiting nothing, a coroutine blocking on `.result()`, reconstructs the freeze block with extra steps.

---

## 107.3 Measurement: the crossing prices

**Methodology.** `code/ch188/bench_bridge_costs.py`.
2,000 crossings per run, `min` of 5, 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. Loop to thread.**

| crossing | per call |
|---|---|
| direct call (floor) | 85 ns |
| `loop.run_in_executor` | 30,207 ns |
| `asyncio.to_thread` | 32,241 ns |

**b. Thread to loop.**

| crossing | per call |
|---|---|
| `run_coroutine_threadsafe` (round trip) | 41,944 ns |
| `call_soon_threadsafe` (post only) | **2,014 ns** |

**The bridge costs what its parts cost.**
~30 us out (pool submission, future pair, self-pipe wakeup), ~42 us for the thread-side round trip (the same parts plus the thread blocking on the result), and the `to_thread` premium over raw `run_in_executor` is the context copy, 2 us buying the `contextvars` correctness of §107.1. The post-only door at 2 us is **20x cheaper than the round trip**: fire-and-forget notifications, metrics, log lines, "data ready" pokes, should post, not await.

**The rule is the grain rule, restated for colors.**
At 30 us per crossing: a 10 ms query pays 0.3% bridge tax, invisible; a 10 us parse pays 300%, ruinous. The fix is never "make the bridge faster"; it is **move the loop, not the call**: one `to_thread(parse_all, items)` that runs the whole batch inside the thread, instead of `to_thread(parse, item)` per item. This is Chapter 100's granularity table with "boundary" instantiated to the color seam, and Chapter 84's one-crossing-per-batch, now three volumes old and still undefeated.

**Book I** has the same two doors with the same asymmetry, post-to-reactor cheap, round-trip expensive, and its gateway design rule is word-for-word: results flow back in batches, notifications post one way, and nothing in a handler ever blocks on work it dispatched.

---

## 107.4 Edges and failure modes

**The freeze has quiet spellings.**
`requests.get` in a handler, `time.sleep` for pacing, a synchronous ORM call, `pathlib.read_text` on NFS, `subprocess.run`, each stalls every task for its duration, with no exception and no warning by default. Debug mode (`asyncio.run(..., debug=True)`) logs callbacks over 100 ms with tracebacks; production services should soak-test with it on, because a 40 ms freeze never trips the detector and still doubles p99.

**`.result()` on the loop is the freeze with a bow on it.**
A `concurrent.futures.Future` blocked on from a coroutine, typically leaked from an executor or a `run_coroutine_threadsafe` misuse, waits for machinery the blocked loop must run. The direction rule from §107.2 is the audit: loop code awaits; thread code `.result()`s; never crosswise.

**Pool exhaustion converts bridges into latency.**
The default pool has `min(32, cpu+4)` threads; thirty-three concurrent `to_thread` calls queue behind it invisibly. Size a dedicated executor for known-blocking workloads (`loop.set_default_executor`, or pass one explicitly), and bound *admission* with Chapter 105's semaphore so the queue is visible and shed-able instead of silent.

**Blocking work is uncancellable from the loop side.**
Cancelling a task awaiting `to_thread` abandons the *await*; the thread keeps running to completion (there is no safe way to kill it, Deep E). Design bridged calls to be short, idempotent, or cooperatively interruptible (pass a `threading.Event` the sync code polls); Chapter 103's shield semantics decide who awaits the survivor.

**`contextvars` flow in, not back out.**
The thread sees the copied context; values it *sets* are invisible to the awaiting task (a copy is a copy, Chapter 103). Results come back as return values, never as ambient state.

**The executor outlives your interest politely, until shutdown.**
`asyncio.run` waits for the default pool's threads at exit; a bridged call that hangs (network file system, dead DB) hangs interpreter shutdown. Timeouts belong *inside* the sync call (driver timeouts) because, per the cancellation edge, the loop cannot impose one from outside.

**And on the free-threaded build, the bridge gets a promotion.**
`to_thread(cpu_work)` was a GIL-bound serialisation on 3.13 and is real parallelism on 3.14t (Chapter 93), with Chapter 96's sharing rules now applying to whatever the bridged code touches. Audit bridged functions for shared mutable state when migrating; the freeze rules did not change, but the concurrency inside the pool did.

---

## 107.5 Connections

**Backward.**
The clause and the starvation demo are Chapter 101; the future machinery both doors ride is Chapter 102; context capture is Chapter 103's rule; the single-threaded primitives the doors protect are Chapter 105. Thread pools, `concurrent.futures`, and why killing threads is impossible are Deep E; releasing the GIL at C boundaries, which makes pool threads useful on GIL builds, is Chapter 80; the executor-choice table is Chapter 100.

**Forward.**
Chapter 108 assembles the patterns, bounded bridged sections, shutdown sequences that drain pools, and the sync-facade pattern for exposing async libraries to sync callers (`asyncio.run` per call as the reverse bridge, with its loop-per-call price from Chapter 101).

**Across books.**
The two-color problem is named from a famous essay about JavaScript, but its economics are universal: Go erased the colors by making the runtime own all blocking (every call is bridge-free, and the price is a runtime that must intercept every syscall); Rust kept the colors and the explicit executors; **Book I**'s C++ kept them too, with `co_await` and thread-pool offload mirroring this chapter door for door. Python's position, colors kept, bridges cheap enough for I/O grains, is the conservative middle, and this chapter's tables are what "cheap enough" means.

---

## 107.6 Exercises

**1. Reproduce the freeze family.** Rewrite the listing's freeze with (a) `future.result()` and (b) a synchronous `queue.Queue.get()` waiting on loop-side `put`s. Confirm each prints the same order signature.

**2. Find your freezes.** Run a real async service under `debug=True` with the slow-callback threshold lowered to 10 ms; catalogue every hit by library. Fix the top one with `to_thread` and re-measure p99 under load.

**3. Batch the small stuff.** Take 10,000 1 us JSON parses; measure per-item `to_thread`, batched `to_thread(parse_all)`, and inline on the loop. Reconcile the three with §107.3's arithmetic, including the inline option's effect on a concurrent heartbeat task's latency.

**4. Size a pool honestly.** Against a fake 50 ms blocking driver, plot request throughput and p99 versus dedicated-pool size 1 to 64 at fixed offered load. Find the knee, relate it to Little's law, and add semaphore admission control to make overload explicit.

**5. Interrupt the uninterruptible.** Implement a bridged call that polls a `threading.Event` every 10 ms; wire task cancellation to set it (`try/except CancelledError` around the await, per Chapter 103's contract). Demonstrate end-to-end cancellation latency and compare with the abandoned-await default.

**6. The design question.** Go erased function colors by owning the scheduler beneath every call; Python kept colors and sells bridges. Argue Python's position: what erasure costs a language with a C-extension ecosystem (every extension's blocking call must be interceptable, the Chapter 94 wheel problem again in scheduler form), what colors cost daily (this chapter's existence), and how the free-threaded build shifts the balance by making the *thread* side genuinely parallel. Conclude with which single stdlib addition would most shrink this chapter, and defend it against the two-doors discipline.

---

## 107.7 Summary and cross-references

- **The two-color problem**: sync calls stall the loop, provably, a queued callback could not run until the blocking wait timed out. Anything on the loop that waits for the loop is that deadlock; debug mode is the detector, `to_thread` the default fix.
- **The seam is airtight**: `to_thread` carries return values, re-raised exceptions, and copied `contextvars` (its 2 us premium over `run_in_executor`); threads re-enter through exactly two doors, `call_soon_threadsafe` (post, 2 us) and `run_coroutine_threadsafe` (round trip, 42 us).
- **Priced**: ~**30 us per loop-to-thread crossing** against an 85 ns call. Grain rule at the seam: 0.3% tax on a 10 ms query, 300% on a 10 us parse, **bridge the big, batch the small, post don't round-trip for notifications**.
- **Direction discipline**: loop code awaits, thread code `.result()`s; pool threads never touch loop objects; blocking work is uncancellable from outside, so interruption is designed in or foregone.
- **Pools are policy**: size dedicated executors, bound admission with semaphores, and on 3.14t every `to_thread` quietly became real parallelism, with Chapter 96's sharing rules now applying inside.

**Cross-references.** The clause and starvation → Chapter 101. Future machinery → Chapter 102. Context and cancellation contracts → Chapter 103. Loop-affine primitives → Chapter 105. Thread pools and the un-killable thread → Deep E. GIL release at C boundaries → Chapter 80. Executor choice and grain → Chapter 100. Patterns and facades → Chapter 108.
