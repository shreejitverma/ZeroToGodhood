# Chapter 108: Async Patterns and the Decision

Deep J closes the way this book closes volumes: the pieces assembled into the shapes production code actually takes, the capstone measured, and the decision procedure handed over.

Three patterns cover most async services, and each is a composition of this volume's chapters proven by a deterministic order log. **Bounded fan-out**, `TaskGroup` owning lifetimes, `Semaphore` owning the budget, `timeout` owning the deadline, is the service skeleton; the listing runs ten jobs at budget three and prints `peak in flight 3`. The **hedged race**, `wait(FIRST_COMPLETED)` plus the loser-cancellation everyone forgets, prints its winner and the loser's honest cleanup. And **graceful shutdown**, stop intake, drain via sentinel, cancel stragglers behind a timeout, prints `served-0, served-1, served-2, worker-drained, group-closed`, the shutdown diagram as a log line.

The capstone benchmark then sizes the skeleton's one number, the budget, and watches both regimes appear in one table: in the waiting regime, throughput is **Little's law with nothing in the way** (budget 10 gives 834 requests/s; budget 1,000 gives 65,869/s, the whole thousand-request batch in one 10 ms wait); add 1 ms of CPU per request and every budget above 50 pins at **~980/s**, because a thousand milliseconds of bytecode is one full second on the loop's single thread, and past saturation, budget buys queueing, not throughput.

**This is a Deep J chapter, and it closes Deep J.**
Chapters 101 to 107 built the loop, the chain, the tasks, the structure, the coordination, the bytes, and the bridges; this chapter spends them, and hands the CPU column's problem to Deep L via Chapter 100's table, closing the composition loop between the two concurrency volumes.

## Section index

- **108.1** The three patterns, proven
- **108.2** The pattern language: budgets, races, drains
- **108.3** Measurement: sizing the budget
- **108.4** Edges and failure modes
- **108.5** Connections, and the volume closed
- **108.6** Exercises
- **108.7** Summary and cross-references

Listings live under `code/ch189/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 108.1 The three patterns, proven

```python
# code/ch189/l01_patterns_and_the_decision.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- pattern 1: bounded fan-out, the service skeleton ---
  10 jobs, budget 3 : 10 completed, peak in flight 3
  TaskGroup owns the lifetimes (Ch 104), the Semaphore owns the
  budget (Ch 105), the timeout owns the deadline (Ch 104), and
  every fan-out in production is this skeleton with I/O inside
--- pattern 2: the hedged race: first wins, losers cancelled ---
  winner : fast   order : fast-answered, slow-cancelled
  wait(FIRST_COMPLETED) is the race; cancelling the losers is the
  half everyone forgets, and Chapter 103's contract is why the
  slow backend's cleanup ran before we moved on
--- pattern 3: graceful shutdown: stop intake, drain, then cancel ---
  shutdown-requested, served-0, served-1, served-2, worker-drained, group-closed
  the sentinel drains in-flight work before the group closes; the
  cancel-everything hammer (Ch 103) is the fallback for stragglers,
  behind a timeout - drain first, cancel second, always
```

**The skeleton is three ownerships, no more.**
Lifetimes to the group, concurrency to the semaphore, time to the deadline, three orthogonal bounds, each from its own chapter, composing without knowing about each other. Every production fan-out, crawler, batch API client, notification fan, is this skeleton with real I/O where the `sleep(0)` sits, and most async incidents are one of the three bounds missing: unowned tasks (no group), unbounded concurrency (no semaphore), or unbounded time (no deadline).

**The hedged race's order log shows the half that matters.**
`fast-answered, slow-cancelled`: the loser's cleanup *ran*, before the function returned, because cancellation was requested and then **awaited**, Chapter 103's contract driven to completion rather than fired and forgotten. A race that abandons its losers leaks connections at the rate of its hedging, which is to say: at the rate of its success.

**And the shutdown log is the diagram every service needs, in one line.**
Intake stops (the sentinel is enqueued after the last real item), in-flight work drains (`served-*` complete), the worker exits by *seeing* the sentinel rather than by being shot, and only then does the group close. Cancellation, the hammer, stays holstered behind a timeout for stragglers. Drain first, cancel second; services that invert the order lose exactly the requests they were shutting down politely to protect.

---

## 108.2 The pattern language: budgets, races, drains

**Budgets are admission control, and they belong at the edge.**
One semaphore at the boundary where load enters beats scattered limits inside: internal stages inherit the bound through Chapter 105's backpressure chain, and overload becomes a queue *outside* the semaphore, visible, sheddable, and measurable, instead of ten thousand half-started tasks. The budget's number is §108.3's subject; its *placement* is this paragraph.

**Races generalise past hedging.**
The same `FIRST_COMPLETED`-then-cancel shape implements timeouts-with-fallback (race the work against a sleep), speculative retries, and multi-region reads. The invariants are constant: every loser is cancelled *and awaited*; the winner's result is read before the losers are reaped (a loser's exception must not mask the win); and shields (Chapter 103) mark any leg whose side effects must not be abandoned mid-flight.

**Drains are the shutdown primitive; cancellation is the enforcement.**
The sentinel-drain works because a bounded queue plus a stop on intake gives a finite amount of remaining work; the timeout-then-cancel backstop exists because "finite" is a claim about your code, not a guarantee about the network. The full sequence for a real service: stop accepting (close the listener, Chapter 106's ceremony), drain with a deadline, cancel survivors, await the group, and only then close pools and loops (Chapter 107's shutdown edge).

**The sync facade is the fourth pattern, mentioned to be bounded.**
Libraries exposing async cores to sync callers wrap entry points in `asyncio.run` (a loop per call, Chapter 101's price) or a dedicated loop thread plus `run_coroutine_threadsafe` (Chapter 107's door, amortised). The facade's rule is the two-color rule inverted: sync callers must never be handed awaitables, and the boundary is one module, not a style sprinkled through a codebase.

---

## 108.3 Measurement: sizing the budget

**Methodology.** `code/ch189/bench_budget_sizing.py`.
1,000 requests through the skeleton; each request waits 10 ms; the second column adds 1 ms of spinning CPU. `min` of 3 per cell; 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| budget | pure wait | wait + 1 ms CPU |
|---|---|---|
| 10 | 1,199 ms (834/s) | 2,081 ms (481/s) |
| 50 | 246 ms (4,068/s) | 1,024 ms (977/s) |
| 100 | 123 ms (8,126/s) | 1,125 ms (889/s) |
| 500 | 29 ms (34,507/s) | 1,018 ms (982/s) |
| 1,000 | **15 ms (65,869/s)** | 1,016 ms (**~984/s, pinned**) |

**The left column is Little's law with nothing in the way.**
`throughput = budget / latency`: each ten-fold budget increase buys almost exactly ten-fold throughput, up to the whole batch in flight at once, 1,000 concurrent waiters completing in a single 10 ms wait plus 5 ms of Chapter 103's task bookkeeping. Waiters are what Chapter 101 priced them: a frame and 1.4 KB. **In the waiting regime, concurrency is nearly free, so buy as much as the downstream can stand.**

**The right column is the wall this volume cannot move.**
1,000 requests times 1 ms of bytecode is one second of CPU, and the loop has one thread: every budget from 50 up lands on ~1,020 ms, and the extra concurrency past saturation bought only longer queues, worse tail latency at identical throughput (the budget-100 row's wobble is that queueing showing up as noise). The two columns are the two measurements a capacity plan needs: **the wait your budget divides, and the CPU floor your single thread imposes.** When the second binds, the answer is not in this volume: it is Chapter 107's bridges in batches, sized by Chapter 100's grain table, which is exactly where the two concurrency volumes' composition rule points.

**Book I**'s gateway capacity model is the same two-column table with the columns three orders apart, and its sizing memo ends with the same sentence this one does: find the wall you are actually against before buying concurrency you cannot execute.

---

## 108.4 Edges and failure modes

**A missing bound is an incident deferred.** §108.1.
No group: leaked tasks and unretrieved exceptions (Chapter 103). No semaphore: downstream overload at the first traffic spike, and memory as your only backpressure. No deadline: one dead upstream turns the service into a queue of forever. The skeleton is not style; it is the three incidents pre-empted.

**Budgets interact multiplicatively across stages.**
A budget-100 fan-out calling a budget-10 downstream stage queues 90 tasks at the inner semaphore, latency that looks like the downstream's fault. Budgets nest safely only when outer <= inner along every path, or when the outer bound is the only one and inner stages inherit it via backpressure; audit the chain, not the stage.

**Races must reap before they return.**
Returning the winner while losers are merely `cancel()`ed (not awaited) leaks their cleanup into the background: connections closed by GC (Chapter 95's timing on 3.14t), warnings at destruction, and shields silently violated. The listing's reap loop is four lines; it is the pattern's price of admission.

**`as_completed` and `wait` return futures, not results, in nondeterministic order.**
Real completion order depends on I/O arrival, so code consuming a race's stream must be order-independent, and *tests* of such code must fake the I/O to restore Chapter 101's determinism, which the listing does with beat-counted backends, the technique itself is the exhibit.

**Drain sentinels scale poorly past one worker per queue.**
N workers need N sentinels (or a `None`-broadcast wrapper), and mixed-priority queues need drains per class. Past that complexity, the group-cancel-with-timeout backstop *is* the drain, and the design question becomes idempotency of interrupted work, Chapter 103's shield decision at fleet scale.

**The saturation wobble is a symptom worth knowing by sight.** §108.3.
Throughput flat, tail latency growing, budget increases changing nothing: the loop is CPU-saturated. `asyncio` offers no CPU profiler of its own; Chapter 86's tools apply directly (profile the process; the loop is just Python), and the slow-callback log (Chapter 107) fingers the worst offenders.

**And the patterns assume the clause.**
Every log line in this chapter depends on nothing blocking the loop. One synchronous call inside the skeleton and the semaphore admits work the loop cannot progress, the deadline cannot fire, and the drain cannot drain. The volume's first rule is also its last.

---

## 108.5 Connections, and the volume closed

**Backward, through the volume this chapter closes.**
The loop and its determinism, Chapter 101, are why every order log in this chapter verifies. The suspension unit that budgets loop trips, Chapter 102. Tasks, cancellation's contract, and the reap discipline, Chapter 103. The group, the deadline, and error aggregation, Chapter 104. The semaphore, the queue, and backpressure, Chapter 105. The byte layer under the I/O these patterns bound, Chapter 106. The bridges the CPU column escapes through, Chapter 107. This chapter added no machinery, only composition, which is what a volume closing should need.

**Beyond the volume.**
The CPU floor hands off to Deep L through Chapter 100's decision table, completing the composition the two volumes were designed around: the loop absorbs the waiting, Deep L's primitives absorb the computing, and Chapters 100, 107, and 108 are the three views of one seam. Generators and `contextvars` beneath everything are Deep F; sockets beneath Chapter 106 are Deep R; the release history is Volumes 10 and 11.

**Across books, one last time for Deep J.**
The three patterns are the reactor trinity in every language: bounded intake, speculative execution with reaping, drain-then-kill shutdown. **Book I**'s gateway implements all three in C++ with the constants three orders smaller and the diagrams identical, and the shared system's operational runbook does not distinguish which language a service is written in when it describes them, which is the strongest closing argument this volume can make: the model, not the language, is the engineering.

---

## 108.6 Exercises

**1. Reproduce the capstone** on your machine; add budget rows 2,000 and 5,000 to the pure-wait column and find where task bookkeeping (Chapter 103's 1.7 us) becomes visible against the 10 ms wait.

**2. Break the skeleton three ways.** Remove the group, the semaphore, and the deadline one at a time under a fault-injecting fake backend (10% hang, 10% error). Document the failure signature of each missing bound; keep the trio as your incident-review checklist.

**3. Hedge against a real distribution.** Give backends latency `lognormal(10 ms, sigma)` and measure p50/p99 and duplicate-work rate for hedging delays of 0, p50, and p90. Find the delay where hedging pays at sigma = 1, and the sigma where it stops paying at all.

**4. Drain at scale.** Extend pattern 3 to five workers and two priority classes; implement broadcast sentinels and a 100 ms cancel backstop. Prove (order log) that no accepted high-priority item is ever lost, then inject a hung worker and prove the backstop fires.

**5. Build the facade.** Wrap the skeleton in a sync API twice: `asyncio.run` per call, and a dedicated loop thread with `run_coroutine_threadsafe`. Measure per-call overhead of each against Chapter 101's and 107's tables, and write the two-line guidance for which to ship.

**6. The design question.** This volume's patterns all bound *concurrency*; nothing in asyncio bounds *rate* (requests per second), and libraries bolt limiters on top with sleep-based token buckets, in tension with "publish with an edge, never with time" (Chapter 105). Design a rate limiter native to this volume's parts, timer handles as token refills, a queue as the bucket, backpressure as the interface, then argue whether it belongs in the stdlib, using the `Semaphore`/`Queue` precedent for what asyncio ships and the `uvloop` precedent for what it leaves out.

---

## 108.7 Summary and cross-references

- **Three patterns cover most services**, each a composition proven in order: bounded fan-out (group + semaphore + deadline, `peak in flight 3`), the hedged race (`FIRST_COMPLETED`, then cancel *and await* the losers), and graceful shutdown (stop intake, sentinel-drain, cancel behind a timeout, `drain first, cancel second`).
- **The capstone, measured**: pure waiting obeys Little's law from 834/s at budget 10 to **65,869/s at budget 1,000** (waiters are a frame and 1.4 KB); add 1 ms CPU per request and throughput pins at **~984/s** at every budget past 50, one second of bytecode is one second of the loop's single thread, and past saturation, budget buys queueing.
- **Therefore a capacity plan is two measurements**: the wait your budget divides, and the CPU floor your thread imposes; the second escapes through Chapter 107's bridges, sized by Chapter 100's table, the composition of this book's two concurrency volumes in one sentence.
- **The bounds are the incidents pre-empted**: no group leaks tasks, no semaphore melts downstreams, no deadline waits forever; budgets nest outer<=inner; races reap before returning; drains scale by design, not by hope.
- **Deep J, closed**: 101 the loop, 102 the chain, 103 the tasks, 104 the structure, 105 the coordination, 106 the bytes, 107 the bridges, 108 the compositions. The interleaving is code, not chance, and that determinism, every order log in this volume byte-verified on three interpreters, is what you traded threads for.

**Cross-references.** The loop and determinism → Chapter 101. Suspensions → Chapter 102. Tasks and reaping → Chapter 103. Groups and deadlines → Chapter 104. Semaphores, queues, backpressure → Chapter 105. The byte layer → Chapter 106. Bridges and facades → Chapter 107. The CPU escape → Chapters 100, 107, Deep L. Generators and context → Deep F. Sockets → Deep R.
