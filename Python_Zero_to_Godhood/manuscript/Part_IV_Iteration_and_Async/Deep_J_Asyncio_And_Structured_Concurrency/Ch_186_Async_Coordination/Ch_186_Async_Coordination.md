# Chapter 105: Async Coordination

Deep E spent chapters on locks because threads interleave anywhere; Chapter 99 measured what forgetting one costs. This chapter opens with the heresy Chapter 101's determinism earns: **most async code needs no locks at all.** Four tasks incremented a shared counter four hundred thousand times, unlocked, and the count is exact, on every build, including the free-threaded one, because a task owns the loop between its awaits and call-free sequences cannot interleave. The same code lost a third of its updates to threads in Chapter 99.

What still races is precisely one shape: **an invariant held open across an `await`**, and here the model produces its party trick. The listing's read-await-write race prints `balance = 1`, the *same lost update, every run, on every interpreter*, because the schedule is deterministic. A reproducible race, printable in a verified book, is something Deep E could never offer, and it is why async races are findable in tests where thread races are distributions.

The tools for that one shape are this chapter's subject: `asyncio.Lock` for invariants that cross awaits, `Queue(maxsize)` for backpressure nobody has to remember to write, `Semaphore` as a concurrency budget, all single-threaded machinery, none of it thread-safe, priced at a few hundred nanoseconds of Python-level bookkeeping each.

**This is a Deep J chapter.**
Deep E owns the thread cousins; Chapter 49 owns `queue.Queue`. This chapter owns the async coordination model: when the loop itself is the lock, when it is not, and what the objects cost.

## Section index

- **105.1** The loop as the lock, and the one race that remains
- **105.2** The model: wakeups, backpressure, budgets
- **105.3** Measurement: the price list
- **105.4** Edges and failure modes
- **105.5** Connections
- **105.6** Exercises
- **105.7** Summary and cross-references

Listings live under `code/ch186/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 105.1 The loop as the lock, and the one race that remains

```python
# code/ch186/l01_async_coordination.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- between awaits, nothing preempts: unlocked and exact ---
  4 tasks x 100,000 unlocked increments : 400,000
  Chapter 99's benchmark lost a third of these on the free-threaded
  build; here the count is exact BY THE MODEL: a task owns the loop
  between its awaits, so call-free sequences cannot interleave
--- but an invariant held ACROSS an await races, deterministically ---
  two unlocked read-await-write increments : balance = 1  (one update LOST)
  the same two increments under asyncio.Lock : balance = 2
  the async race is DETERMINISTIC - it printed the same lost update
  it will print on your machine - which is why it is findable in a
  test where a thread race is a distribution (Chapter 99). the rule:
  lock exactly the invariants that stay open across an await
--- Queue(maxsize): backpressure is built in ---
  maxsize=2 : put-0, put-1, got-0, put-2, got-1, put-3, got-2, got-3
  the producer stalled at put-2 until the consumer drained one: a
  bounded queue makes the fast side wait for the slow side, which
  is flow control nobody has to remember to write
--- Semaphore: concurrency as a budget ---
  6 tasks through Semaphore(2), max in flight : 2
```

**The unlocked 400,000 is the model's dividend, stated as a number.**
It is exact for a stronger reason than Chapter 99's GIL-build zeros (which were an implementation accident of safe-point placement): here atomicity-between-awaits is the *semantics*. The listing runs identically on 3.14t, where the same code under threads lost 21 to 33% per run. Single-threaded cooperative scheduling converts most of Deep E's locking discipline into dead weight, which is the second reason (after Chapter 101's cheap waits) that I/O-heavy servers moved to this model.

**The deterministic race is the chapter's centrepiece.**
`read, await, write` with two tasks: both read 0 before either writes, and the final balance is **1**, printed exactly, every run. The await is the only preemption point, so the interleaving is fixed by the schedule, and so is the corruption. Two consequences follow. Practically: the rule for async locking is auditable, **grep for state read before an `await` and written after it**; nothing else needs a lock. Philosophically: async races are ordinary bugs with reproducers, not Chapter 99's probability distributions, and a failing test stays failing.

**The queue and semaphore blocks are flow control as data structures.**
The bounded queue stalled its producer at `put-2` until the consumer drained one, backpressure by construction, where an unbounded handoff grows without limit until something else fails (Chapter 49's warning, solved at the type level by `maxsize`). The semaphore admitted two of six tasks at a time, `max in flight : 2`, which is Chapter 108's bounded-fan-out pattern reduced to its single working part.

---

## 105.2 The model: wakeups, backpressure, budgets

**Every async primitive is the same small machine.**
A deque of waiters, each waiter a future; `acquire`/`put`/`wait` either succeeds immediately or parks the caller by awaiting a fresh future on that deque; `release`/`get`/`set` pops a waiter and completes its future, which re-queues the parked task via Chapter 101's ready queue. No condition variables, no futexes, no memory barriers, the loop's single-threadedness is the mutual exclusion, and the objects merely manage *who wakes next* (FIFO, preserving Chapter 101's fairness-by-turns).

**That is why they are cheap, and why they are not thread-safe.**
Cheap: an uncontended `async with lock:` is a flag check and two method calls, no syscall possible, §105.3 prices it at 211 ns. Not thread-safe: the internal deques and flags are touched without any protection *because the loop provides it*; a second thread touching the same object corrupts it on any build (and on 3.14t, Chapter 96's rules make it visibly worse). The bridge for threads is Chapter 107's `call_soon_threadsafe` family, full stop.

**Backpressure is the queue's real feature, not its buffering.**
`await q.put(x)` on a full queue suspends the producer, which recursively suspends whatever feeds the producer, propagating "slow down" upstream through the natural await chain, flow control with no code. The design decision is the bound itself: unbounded queues defer the problem to memory; `maxsize=0`-style rendezvous couples stages tightly; the useful sizes are small multiples of the consumer's batch, and Chapter 106's stream buffers apply the identical logic one layer down.

**A semaphore is a budget, and budgets compose with structure.**
`Semaphore(n)` bounds in-flight concurrency wherever the fan-out happens; inside a `TaskGroup` it bounds the group's parallelism while the group bounds its lifetime, the two dimensions of control that Chapter 108's patterns combine. `BoundedSemaphore` additionally treats over-release as the bug it is, and is the right default for budget semantics.

---

## 105.3 Measurement: the price list

**Methodology.** `code/ch186/bench_primitive_costs.py`.
100,000 operations per run, `min` of 5, 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. Uncontended acquire/release.**

| primitive | per pass |
|---|---|
| no lock (floor) | 16 ns |
| `threading.Lock` | 63 ns |
| `asyncio.Lock` | 211 ns |
| `asyncio.Semaphore` | 345 ns |

**b. Same-thread queue hand-off (put + get).**

| structure | per pair |
|---|---|
| `collections.deque` (floor) | 23 ns |
| `asyncio.Queue` (`_nowait`) | 196 ns |
| `queue.Queue` | 581 ns |

**The async objects are pure Python and price like it.**
211 ns for an uncontended async lock against 63 for the C thread lock: the async object pays attribute lookups, a context-manager protocol, and waiter-deque bookkeeping in bytecode. Yet `asyncio.Queue` *beats* `queue.Queue` three-fold, because the thread queue pays a real lock and condition machinery per operation while the async queue, protected by the loop, pays none. The ordering is not "async is slow" or "async is fast"; it is **you pay for exactly the machinery the model requires**, and this model requires wakeup bookkeeping only.

**Calibration, in the volume's own units.**
Every number in both tables is noise next to one suspension (27,000 ns, Chapter 102) or any real I/O; all of them are real if the primitive decorates an inner loop that never suspends, where the model already provides atomicity for free. The rule from §105.1 sizes usage correctly by itself: primitives guard *across-await* invariants and bound flow, and across-await code has already paid for a suspension that dwarfs the primitive.

**Book I**'s comparison row is instructive: its spinlocks and MPMC queues cost nanoseconds because they buy exclusion on *preemptive* parallel hardware with atomics. This chapter's objects cost hundreds of nanoseconds and buy only ordering on a machine that cannot race between awaits at all. Cheaper problems have cheaper locks; the expensive part was already paid by the model's restriction (one thread, explicit yields), which is the recurring trade of this volume.

---

## 105.4 Edges and failure modes

**None of these objects is thread-safe, and the failure is silent.** §105.2.
A thread calling `q.put_nowait` on an asyncio queue mutates unprotected deques; symptoms range from lost wakeups to corrupted state, and no build warns. The bridge is Chapter 107's; the audit is "no asyncio object is ever named in a function that runs off-loop".

**The unlocked dividend evaporates if a call hides an await.**
`counter += self.adjust()` is safe only while `adjust` is synchronous; the day it becomes `async` (and the call site gains its `await`), the read-modify-write now spans a suspension, §105.1's race, introduced by a signature change three files away. The convention that contains this: functions that touch shared invariants stay synchronous, or take the lock themselves.

**Lock across await, yes; lock around I/O, carefully.**
Holding an `asyncio.Lock` across a slow network await serialises every waiter behind that latency (the loop stays free; the *waiters* do not). Prefer copying state out, awaiting unlocked, and reconciling, the same shrink-the-critical-section discipline as Deep E, with the await as the expensive region.

**Unbounded queues are deferred outages.**
`asyncio.Queue()` with a fast producer grows until memory pressure becomes the flow control (Chapter 95's collector as backpressure is not a design). Choose `maxsize` deliberately; treat `put_nowait` + `QueueFull` as the explicit-drop variant for lossy streams.

**`Condition` exists, and is almost always the wrong first tool.**
Its wait/notify protocol reintroduces the lost-wakeup class the simpler objects avoid; most uses are better spelled as a Queue (hand off the datum) or an Event (publish the edge). Reach for it only when waiters filter on a predicate over shared state, and re-check the predicate in a loop, same as Deep E taught.

**Fairness is FIFO per object, and starvation is still possible.**
Waiters wake in arrival order, but a released-and-immediately-reacquired lock (tight loop holding it across its own awaits) can keep the queue long. The semaphore-as-budget pattern, or restructuring so the hot task batches its holds, is the fix; there is no priority parameter to reach for (Chapter 101's design question, echoed).

**And on the free-threaded build, the temptation returns.**
Chapter 100 legitimises threads again, so async code increasingly *coexists* with real parallelism. The line holds: asyncio objects for coordination *within* the loop's world; Deep E/L machinery between worlds; and the boundary crossed only by the two `_threadsafe` doors.

---

## 105.5 Connections

**Backward.**
The determinism that makes the unlocked block exact and the race reproducible is Chapter 101; the suspension the primitives park on is Chapter 102's future machinery; task wake-ups ride Chapter 103's driver. The thread cousins, and the discipline this chapter mostly retires, are Deep E (Chapters 46, 49) and Chapter 99; the thread-queue price paid for preemption is Chapter 49's design.

**Forward.**
Streams (Chapter 106) are these queues specialised for bytes, with the same backpressure story at the transport layer. The `_threadsafe` bridge and executor futures are Chapter 107. Chapter 108 composes semaphore budgets, bounded queues, and task groups into the service patterns, with this chapter's price list as its parts catalogue.

**Across books.**
The single-threaded-reactor lock is a classic: Node has no locks at all, Nginx workers share nothing, and **Book I**'s per-core shards run lock-free within a shard for exactly this chapter's reason, one owner, no preemption, no lock. The across-await race is likewise universal: every reactor language rediscovers that `await` is where invariants escape, and the audit rule (state open across a yield point) transfers verbatim.

---

## 105.6 Exercises

**1. Reproduce the party trick.** Run the racy block ten times on two machines; confirm the identical corrupted value. Then insert a second `sleep(0)` before the write and predict the new (still deterministic) final balance before running.

**2. Audit for the one race.** In an async codebase, find every read-before-await-write-after pattern (a regex over ast gets close). Classify each as benign (task-local), locked, or a live bug. Report the count of each; the third bucket is rarely empty.

**3. Size a queue.** Build a three-stage pipeline (parse, transform, write) with bounded queues; measure throughput and peak memory at `maxsize` 1, 16, 256, and unbounded, under a bursty producer. Find the knee and defend a choice.

**4. Break an object from a thread.** Call `put_nowait` on an asyncio queue from a worker thread under load until you observe a failure; document the symptom. Fix with `call_soon_threadsafe` and show it holds. Keep both versions as the training exhibit.

**5. The lock-across-IO tax.** Guard a fake 10 ms network call with one `asyncio.Lock` shared by 50 tasks; measure p50/p99 completion. Restructure to copy-await-reconcile and re-measure. State the invariant that restructuring assumed.

**6. The design question.** `asyncio`'s primitives mirror `threading`'s API names, though their semantics differ (no thread safety, FIFO wakeups, loop affinity). Argue the choice: what the familiar names bought adoption, what they cost in migration traps (§105.4's first two edges are both name-induced), and whether a from-scratch design (Trio's, with no bare Lock and cancellation-aware primitives only) is the better teaching API. Then propose the single rename that would have prevented the most bugs, and check it against this chapter's edge list.

---

## 105.7 Summary and cross-references

- **Between awaits, the loop is the lock**: 400,000 unlocked increments, exact on every build, by semantics rather than accident. Most Deep E discipline is dead weight inside one loop.
- **The one remaining race is an invariant open across an `await`**, and it is *deterministic*: the listing prints the same lost update (`balance = 1`) every run, on every interpreter, making async races reproducible bugs rather than distributions. The audit: read before await, write after.
- **The tools**: `asyncio.Lock` for exactly those invariants; `Queue(maxsize)` for backpressure that propagates upstream by suspension; `Semaphore(n)` as the concurrency budget; all FIFO, all loop-affine, **none thread-safe**.
- **Priced**: uncontended async lock 211 ns, semaphore 345 ns (pure-Python bookkeeping; the C thread lock is 63 ns), while `asyncio.Queue` at 196 ns beats `queue.Queue`'s 581 ns because the loop replaces its locking. All noise next to a 27 us suspension; all real in a non-suspending inner loop.
- **The traps**: threads touching loop objects (silent corruption), awaits introduced under existing read-modify-writes, locks held across slow I/O, and unbounded queues as deferred outages.

**Cross-references.** Determinism and fairness → Chapter 101. Futures and suspension cost → Chapter 102. Task wakeups → Chapter 103. Groups and budgets composed → Chapters 104, 108. Streams' backpressure → Chapter 106. The thread bridge → Chapter 107. Thread cousins and their prices → Deep E (Chapters 46, 49), Chapter 99.
