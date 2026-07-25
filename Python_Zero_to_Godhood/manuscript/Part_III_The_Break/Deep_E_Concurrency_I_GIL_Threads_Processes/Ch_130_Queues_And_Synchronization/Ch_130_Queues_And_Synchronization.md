# Chapter 49: Queues and Synchronization

Chapter 46 established that the GIL does not make code thread-safe: shared mutable state needs a lock.
But hand-managing locks is where concurrency bugs breed, forgotten acquisitions, wrong lock order (deadlock), a critical section that raises and never releases.
The standard library's answer is a set of **higher-level coordination tools** that encapsulate the locking so you rarely touch a raw `Lock`: `queue.Queue` for handing work between threads, `Event` for signalling, `Semaphore` for capping concurrency, and `Condition`/`Barrier` for the rest.
The most important is **`queue.Queue`**, a thread-safe FIFO that *is* the producer/consumer pattern: producers `put` work, consumers `get` it (blocking until there is work), and no explicit lock appears anywhere.

The chapter's measurement makes the trade concrete, and it is the volume's amortization theme once more.
`queue.Queue` is built on a `collections.deque` plus locks and condition variables, and that coordination machinery costs **~21x** a bare `deque` operation.
That is not a reason to avoid `Queue`, it is a reason to understand what you are buying: the 21x pays for **blocking** (a `get` that waits without busy-looping), bounded capacity, and completion tracking.
When you need those, `Queue` is exactly right; when you only need a fast thread-safe FIFO, a `deque` (whose `append`/`popleft` are atomic in CPython) is far cheaper.

**This is Deep E's coordination chapter.**
It builds on Chapter 46 (the race that motivates synchronization) and completes the threading story before Deep E turns to shared memory and beyond. The primitives here are the safe alternative to the raw `Lock` of Chapter 46 and the deadlock-prone hand-rolled coordination Chapters 46-47 warned against.

## Section index

- **49.1** `queue.Queue`, `Event`, and `Semaphore`
- **49.2** Choosing a coordination tool
- **49.3** Measurement: what `queue.Queue`'s machinery costs
- **49.4** Edges and failure modes
- **49.5** Connections
- **49.6** Exercises
- **49.7** Summary and cross-references

Listings live under `code/ch130/` and are re-executed by `make verify` on both verification interpreters.

---

## 49.1 `queue.Queue`, `Event`, and `Semaphore`

```python
# code/ch130/l01_queue_sync.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- queue.Queue: thread-safe producer/consumer (no explicit locks) ---
  consumer processed items in order : [0, 10, 20, 30, 40]
--- threading.Event: one thread signals, others wait ---
  event coordination order : ['setting', 'released']   (waiter released only after set)
  event.is_set()           : True
--- threading.Semaphore(2): cap concurrent holders at 2 ---
  three non-blocking acquires of Semaphore(2) : [True, True, False]   (2 succeed, 1 fails)
--- the rule ---
  use queue.Queue to hand work between threads (blocking, no locks);
  Event to signal, Semaphore to cap concurrency; prefer these over raw Locks
```

**`queue.Queue`** is the workhorse, and it eliminates explicit locking.
A producer `put`s items; a consumer `get`s them; `get` **blocks** until an item is available (no busy-waiting, no polling, the thread sleeps until woken), so the consumer processes items **in order** (`[0,10,20,30,40]`) as they arrive.
The **sentinel** pattern (`put(None)` to signal "no more work") is the idiomatic shutdown.
Everything is thread-safe internally, no `Lock` appears in the code, which is the point: `Queue` *is* the synchronized hand-off, so you express "producer makes work, consumer takes it" directly and correctly, without the race-prone shared list plus lock you would otherwise write.

**`threading.Event`** is a one-bit signal for coordinating *timing* rather than passing data.
Threads `wait()` (blocking) until another thread `set()`s the event, then all waiters proceed. The output shows the ordering enforced: the waiter appends `"released"` only *after* the setter's `set()`, so `["setting", "released"]` is deterministic. Use `Event` for "start when I say go", "the resource is ready", "shutdown requested".

**`threading.Semaphore(n)`** caps how many threads may hold it at once, a concurrency limiter.
`Semaphore(2)` allows two acquisitions; the third fails (non-blocking) or blocks (blocking). The output shows `[True, True, False]`. Use it to bound concurrency: at most N simultaneous connections, N in-flight requests, N workers touching a rate-limited resource.

These three cover most coordination needs, and none requires you to write a `Lock`. The standard library also provides `RLock` (re-entrant lock), `Condition` (wait for a predicate), and `Barrier` (all threads rendezvous), for the cases these do not.

---

## 49.2 Choosing a coordination tool

The decision is about *what kind* of coordination you need, and the tools map cleanly to intents.

- **Pass work between threads -> `queue.Queue`.** The producer/consumer hand-off. Thread-safe, blocking, ordered, with completion tracking (`task_done`/`join`). This is the default for "one thread produces, another consumes", and it removes the need for a shared list plus lock. Use `LifoQueue`/`PriorityQueue` for stack/priority order.
- **Signal an event -> `threading.Event`.** "Wait until something happens." One thread flips the bit, others waiting proceed. For start/stop signals and readiness flags.
- **Limit concurrency -> `threading.Semaphore`.** "At most N at once." A counter with a cap. For connection pools, rate limits, resource bounds.
- **Protect a critical section -> `threading.Lock`** (Chapter 46). The lowest-level tool, for a short exclusive region around shared mutable state, when no higher-level tool fits.
- **Wait for a predicate -> `threading.Condition`.** "Wait until the buffer is non-empty / the state is X." When a simple `Event` is too coarse (you need to re-check a condition on wake).
- **Rendezvous N threads -> `threading.Barrier`.** "All N wait here, then all proceed together." For phased parallel algorithms.

The overarching guidance: **prefer the highest-level tool that fits, and reach for a raw `Lock` last.**
A `queue.Queue` is safer than a shared list plus a `Lock` (it cannot be used wrong the way a forgotten `acquire` can); an `Event` is clearer than a lock-protected boolean flag; a `Semaphore` is clearer than a hand-counted limit.
Each higher-level primitive encapsulates a locking pattern that is easy to get wrong by hand, which is why the standard advice, echoing Chapters 46-48, is to build on `queue.Queue` and `concurrent.futures` rather than raw threads and locks.
The raw `Lock` is not deprecated, it is the primitive the others are built from, but in application code it should be the exception, used only for the short critical sections the higher-level tools do not cover.

---

## 49.3 Measurement: what `queue.Queue`'s machinery costs

**Methodology.** `code/ch130/bench_queue.py`.
A `put`+`get` pair on a `queue.Queue` versus an `append`+`popleft` pair on a `collections.deque`, `min` of 5 runs, 2,000,000 pairs.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| put + get pair | ns | vs deque |
|---|---|---|
| `collections.deque` `append`+`popleft` | 30 | 1.0x |
| `queue.Queue` `put`+`get` | 623 | **21x** |

`queue.Queue` is **21x** more expensive than a bare `deque` (19x on 3.14.6), and understanding *why* tells you when each is right.
`queue.Queue` is *built on* a `collections.deque`, but wraps it in **locks and condition variables** to provide: a `get` that **blocks** until an item is available (waking via a condition variable, not busy-polling), a `maxsize` that blocks `put` when full, and `task_done`/`join` for completion tracking.
`collections.deque`'s `append` and `popleft` are already **atomic** in CPython (thread-safe for single-item operations, no lock needed), with *none* of that blocking machinery.

So the 21x is the price of the **coordination features**, not thread-safety per se (the `deque` is also thread-safe for these ops).
The choice follows:

- **Use `queue.Queue`** when you need its **blocking producer/consumer semantics**: a consumer that *waits* for work (the common case, and the reason `Queue` exists), a bounded queue for backpressure, or `join` to await completion. The 21x is negligible next to the thread coordination and IO it enables, and correctness (no busy-wait, no race) is worth far more than the nanoseconds.
- **Use `collections.deque`** when you need only a **fast thread-safe FIFO** and will handle availability yourself (or never block, e.g. a lock-free-enough single-producer/single-consumer with your own signalling). It is 21x cheaper because it does less.

This is the amortization theme in its coordination form: **pay for the blocking machinery only when you use it.**
For a high-throughput queue where the consumer is never idle (always work waiting), the `deque`'s cheapness matters; for the typical producer/consumer where the consumer *waits* for sporadic work, `Queue`'s blocking is exactly what you want and its overhead is irrelevant next to the waiting.
As throughout Deep E, the right tool depends on the workload's shape, and knowing the cost lets you choose deliberately rather than reaching for `Queue` reflexively (or avoiding it needlessly).

---

## 49.4 Edges and failure modes

**`queue.Queue` blocks; size it and use timeouts.** §49.1.
`get()` blocks forever on an empty unbounded queue with no more producers, hang. Use the sentinel pattern to signal shutdown, or `get(timeout=...)`, and set `maxsize` for backpressure so a fast producer cannot exhaust memory.

**The sentinel-per-consumer subtlety.**
With multiple consumers, you need one sentinel *per consumer* (each consumer that reads a sentinel stops; one sentinel stops only one consumer). Or use `task_done`/`join` plus a separate shutdown `Event`.

**`deque` is atomic for single ops, not for compound ones.** §49.3.
`d.append`/`d.popleft`/`len(d)` are individually thread-safe, but a *sequence* like "if `d`: `d.popleft()`" is a compound operation that can race (the item may be gone between the check and the pop). For check-then-act, use `Queue` (which blocks correctly) or a lock.

**`Event` is level-triggered and one-shot until cleared.**
Once `set()`, `wait()` returns immediately for everyone until `clear()`. It signals a *state*, not an *edge*; if you need "each occurrence", a `Queue` or `Condition` fits better.

**`Semaphore` must be released.**
An acquired semaphore not released (especially on an exception path) leaks a permit, eventually blocking everyone. Use it as a context manager (`with sem:`) so it releases on exception.

**`Condition` requires the wait-in-a-loop idiom.**
`Condition.wait()` can wake spuriously, so you must re-check the predicate in a `while` loop, not an `if`. This is a classic bug; prefer `Queue` when it fits.

**These are thread tools, not process tools.**
`queue.Queue`, `Event`, `Semaphore`, `Lock` coordinate *threads* in one process (shared memory). For *processes*, use `multiprocessing.Queue`/`Event`/`Semaphore` (which pickle and use pipes/OS primitives, Chapter 47), different objects with similar APIs but process-boundary semantics.

**Deadlock still possible with multiple primitives.**
Combining several locks/semaphores can deadlock (Chapter 46's lock-ordering trap). The higher-level tools reduce but do not eliminate this; keep coordination simple and prefer a single `Queue` hand-off over a web of locks.

---

## 49.5 Connections

**Backward.**
These tools encapsulate the `Lock` of Chapter 46, providing race-free coordination without hand-locking. `queue.Queue` is built on `collections.deque` (Deep Q), whose atomic operations are what makes it thread-safe. The blocking behaviour relies on the GIL and OS condition variables. The sentinel/producer-consumer pattern is the safe alternative to the shared-state races of Chapter 46.

**Forward.**
`concurrent.futures` (Chapter 48) internally uses queues to dispatch work, and is the higher-level tool that often replaces hand-written producer/consumer entirely. `multiprocessing.Queue`/`Event`/`Semaphore` (Chapter 47 / Deep E) are the process-boundary counterparts. `asyncio.Queue` (Deep F) is the single-threaded async counterpart. Lock-free structures and the memory model under free-threading are **Deep L**.

**Across books.**
Producer/consumer with `queue.Queue` is a core **Book I** pattern: a market-data thread produces ticks into a queue, and processing threads consume them, with the queue providing thread-safe hand-off and natural backpressure (a bounded queue slows the producer when consumers fall behind). The order-book system uses `queue.Queue` to move messages between its IO threads and processing threads (blocking consumers that wait for data, the §49.3 case where the overhead is irrelevant), a `Semaphore` to cap concurrent outbound connections, and `Event` for coordinated startup/shutdown, building its concurrency on these high-level primitives rather than raw locks, precisely for the safety §49.2 describes. Where raw throughput on an always-full queue matters (an internal ring buffer), it drops to a `deque` for the §49.3 speed.

---

## 49.6 Exercises

**1. Producer/consumer.** Reproduce §49.1's `queue.Queue` pattern. Then add a second consumer and show you need two sentinels. Explain why `get()` blocking (not polling) is better than a busy-wait loop.

**2. Signal and cap.** Use an `Event` to make several worker threads start simultaneously on a "go" signal, and a `Semaphore` to limit how many run a rate-limited section at once. Explain what each primitive coordinates.

**3. The deque race.** Show that `d.append`/`d.popleft` are individually safe but "`if d: d.popleft()`" races between two threads (an `IndexError` or lost item). Fix it with a `Queue` or lock. Explain the compound-operation hazard.

**4. Measure the trade.** Reproduce §49.3. Confirm `queue.Queue` is ~21x a `deque`. Then build a producer/consumer where the consumer *waits* for sporadic work and show the `Queue`'s overhead is irrelevant (the waiting dominates). Explain when the 21x matters and when it does not.

**5. The design question.** The standard library offers a ladder of coordination tools from raw `Lock` up to `queue.Queue` and `concurrent.futures`. Argue why "prefer the highest-level tool that fits" is the right default, using the §49.1 no-explicit-locks benefit and the §49.3 cost. When is dropping to a raw `Lock` or `deque` justified?

---

## 49.7 Summary and cross-references

- The standard library provides **higher-level coordination tools** that encapsulate locking: **`queue.Queue`** (thread-safe, blocking producer/consumer, the default for handing work between threads, no explicit locks), **`Event`** (one-bit signal, `wait`/`set`), **`Semaphore(n)`** (cap N concurrent holders), plus `RLock`/`Condition`/`Barrier`.
- **Prefer the highest-level tool that fits; reach for a raw `Lock` last.** A `Queue` is safer than a shared list plus lock; an `Event` clearer than a lock-protected flag.
- **Measured:** `queue.Queue` `put`+`get` is **21x** a `collections.deque` `append`+`popleft`, because `Queue` adds locks and condition variables for **blocking** get/put, `maxsize`, and completion tracking, while `deque`'s ops are already atomic in CPython. Use `Queue` when you need the blocking semantics; use `deque` for a bare fast thread-safe FIFO.
- **Edges:** size queues and use timeouts (blocking can hang); one sentinel per consumer; `deque` is atomic per-op but not for check-then-act; release semaphores (use `with`); `Condition.wait` needs a re-check loop; these are thread tools (use `multiprocessing.*` for processes).

**Cross-references.** The race that motivates this / raw `Lock` → Chapter 46. `collections.deque` → Deep Q. `concurrent.futures` (uses queues internally) → Chapter 48. `multiprocessing.Queue` (process boundary) → Chapter 47. `asyncio.Queue` → Deep F. Lock-free / free-threaded memory model → Deep L.
