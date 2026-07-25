# Chapter 53: Deadlocks and Lock Ordering

Deep E has taught the tools of concurrency, threads and processes, the GIL, pools, queues, shared memory, thread-local storage.
This closing chapter is about the failure mode that lurks behind all of them once you use more than one lock: the **deadlock**, where two threads each hold a lock the other needs and both wait forever, and the program hangs with no error, no traceback, no CPU use, just silence.
A deadlock is worse than a crash: a crash tells you where it broke, a deadlock tells you nothing.

The good news is that deadlocks have a small number of causes and one dominant fix.
The classic cause is **inconsistent lock ordering**: thread 1 acquires lock A then B, thread 2 acquires B then A, and if each grabs its first lock and then waits for the second, neither can proceed.
The fix is a **global lock order**: every thread acquires locks in the *same* order, which makes the waiting cycle impossible.
This chapter demonstrates the fix (the ordered version completes; a real deadlock would just hang, so we never run one), covers re-entrant locks (`RLock`) and their modest cost, and distills Deep E's correctness discipline into a set of rules.

**This closes Deep E.**
It synthesizes the locking of Chapters 46, 49, and 51 into deadlock avoidance, and sets up the free-threaded build (Deep L), where more code runs truly in parallel and lock discipline matters even more. The overarching lesson, prefer designs that need few locks, is the through-line of the whole volume.

## Section index

- **53.1** Deadlock, and the global-order fix; `RLock`
- **53.2** The rules for deadlock-free concurrency
- **53.3** Measurement: `Lock` versus `RLock`
- **53.4** Edges and failure modes
- **53.5** Connections
- **53.6** Exercises
- **53.7** Summary and cross-references

Listings live under `code/ch134/` and are re-executed by `make verify` on both verification interpreters.

---

## 53.1 Deadlock, and the global-order fix; `RLock`

```python
# code/ch134/l01_deadlock_avoidance.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- consistent lock ordering PREVENTS deadlock (this completes) ---
  4 threads x 1000 (a-then-b order) : 4000 operations, no hang
  equals 4000 exactly               : True
--- the deadlock this avoids (described, NOT run) ---
  if thread1 took a-then-b and thread2 took b-then-a, each could hold one
  and wait for the other forever; one global order makes a cycle impossible
--- RLock: the SAME thread can re-acquire it (a plain Lock would self-deadlock) ---
  RLock acquired re-entrantly to depth : 2   (a Lock would hang here)
--- the rules ---
  acquire multiple locks in ONE consistent global order (no cycles);
  use RLock only for genuine re-entrancy; keep critical sections small
```

**The deadlock.**
When code needs *two* locks (say a lock on account A and a lock on account B, to transfer between them), the order threads acquire them in matters.
If thread 1 does `with lock_a: with lock_b:` and thread 2 does `with lock_b: with lock_a:`, an interleaving exists where thread 1 holds A and waits for B while thread 2 holds B and waits for A, a **cycle of waiting**, and both hang forever.
The listing does *not* run this (a deadlock hangs the process, which the verification harness cannot tolerate); it runs the **fixed** version.

**The global-order fix.**
Every thread in the listing acquires `lock_a` **before** `lock_b`, always, one consistent global order.
With a single order, a cycle is *impossible*: no thread can hold B and wait for A, because to hold B it must already have acquired A first (and would not be waiting for it).
So four threads doing a thousand double-locked operations each complete deterministically (`4000`, no hang).
This is the single most important deadlock-avoidance rule: **acquire multiple locks in one consistent global order** (e.g. sort by object `id`, or by a fixed hierarchy), and cyclic waiting cannot occur.

**`RLock` for re-entrancy.**
A plain `Lock` acquired twice by the *same* thread **self-deadlocks** (the second acquire waits for the first to release, which never happens, the thread is waiting on itself).
`threading.RLock` (re-entrant lock) allows the owning thread to acquire it again (tracking a recursion count), so the listing acquires it to depth 2 without hanging.
This is needed when a lock-holding method calls another method that acquires the *same* lock, common in a class whose public methods each lock and call one another.
`RLock` solves that self-deadlock, at a small cost (§53.3), but its need is often a hint that the locking is too coarse (§53.2).

---

## 53.2 The rules for deadlock-free concurrency

Deep E's correctness lessons distill into a small set of rules, ordered from most to least impactful.

**1. Prefer designs that need no locks (or few).**
The best deadlock fix is not having the locks. Isolation over sharing: `queue.Queue` hand-offs (Chapter 49), `threading.local` per-thread state (Chapter 51), immutable data, and return-and-combine (Chapter 48) eliminate shared mutable state, and un-shared state cannot deadlock. Most well-designed concurrent Python uses *one* queue or pool, not a web of locks.

**2. Acquire multiple locks in one consistent global order.** §53.1.
When you *do* need multiple locks, impose a total order (sort by `id`, or a fixed hierarchy) and always acquire in that order. This makes cyclic waiting impossible, the primary deadlock-avoidance technique.

**3. Keep critical sections small.**
Hold a lock for the shortest possible time, just the compound operation that needs it (Chapter 51), not surrounding IO or computation. A lock held during a slow operation (a network call, a subprocess) serializes everything and multiplies contention and deadlock risk. Compute outside the lock, mutate inside it.

**4. Never hold a lock across a blocking call.**
Holding a lock while waiting on IO, a subprocess, another lock's slow acquisition, or user input, is how a brief lock becomes a long stall and a deadlock. Release before blocking, or restructure so the blocking happens outside the critical section.

**5. Use timeouts to detect (not fix) deadlocks.**
`lock.acquire(timeout=...)` fails rather than waiting forever, turning a silent hang into a detectable, loggable error you can recover from or diagnose. It does not *fix* the deadlock (that is the ordering rule), but it makes one visible.

**6. Use the highest-level tool.**
`queue.Queue`, `concurrent.futures`, and the coordination primitives (Chapter 49) encapsulate correct locking, so you write less lock code and have fewer chances to deadlock. Raw locks are the last resort (Chapter 51).

**7. Prefer `Lock` over `RLock`.** §53.3.
Use a plain `Lock` by default; reach for `RLock` only for genuine re-entrancy, and treat needing it as a signal to consider a smaller critical section or a lock-free design.

The meta-rule, and Deep E's thesis: **concurrency correctness comes from design, not from adding locks.** A design that minimizes shared mutable state, imposes lock order where sharing is unavoidable, and uses high-level tools is deadlock-free by construction; a design that sprinkles locks reactively accumulates exactly the cycles and stalls this chapter is about.

---

## 53.3 Measurement: `Lock` versus `RLock`

**Methodology.** `code/ch134/bench_lock_types.py`.
An uncontended acquire/release of `threading.Lock` versus `threading.RLock`, `min` of 5 runs, 5,000,000 operations.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| uncontended acquire/release | ns | vs `Lock` |
|---|---|---|
| `threading.Lock` | 72.2 | 1.0x |
| `threading.RLock` | 84.3 | **1.2x** |

`RLock` is **1.2x** a plain `Lock` (1.1x on 3.14.6), a modest but real overhead.
The difference is bookkeeping: `RLock` tracks *which thread* owns it and a *recursion count* (so the owner can re-acquire), where `Lock` is a bare mutex with no owner tracking.
That extra state is what enables re-entrancy, and what costs the 1.2x.

The finding supports rule 7 (§53.2): **use `Lock` by default, `RLock` only for genuine re-entrancy.**
The 1.2x is small enough that it is rarely the deciding factor, the real reason to prefer `Lock` is *simplicity and design*: needing `RLock` (a method holding a lock calls another method that re-acquires it) is usually a sign that the critical section is too coarse or the class's locking is tangled.
Often the better fix is to factor the shared logic into a private method that assumes the lock is *already held* (so it does not re-acquire), leaving the public methods to acquire once, which removes the re-entrancy need *and* the `RLock` cost *and* clarifies the locking.
So the measurement is less about the nanoseconds and more about what reaching for `RLock` *signals*: prefer the plain `Lock` and the smaller critical section it forces you toward.

This closes Deep E on its central theme.
Across the volume, the right concurrency is chosen by understanding the workload (IO vs CPU, Chapters 46-47), using the highest-level tool that fits (Chapters 48-49), locking only what needs it (Chapter 51), and designing to minimize shared state so that deadlocks (this chapter) are avoided by construction rather than debugged after the hang.
Concurrency in Python rewards *design discipline* over *reactive locking*, and the free-threaded future (Deep L), where more runs truly in parallel, only raises the stakes on getting that design right.

---

## 53.4 Edges and failure modes

**Inconsistent lock order deadlocks.** §53.1.
The primary cause. Impose one global acquisition order (by `id`, or a hierarchy) for all multi-lock code.

**A plain `Lock` re-acquired by the same thread self-deadlocks.** §53.1.
Use `RLock` for genuine re-entrancy, or (better) refactor so the lock is acquired once.

**Deadlocks are silent.** §53.2.
No error, no traceback, just a hang. Use `acquire(timeout=...)` to make them detectable, and `faulthandler`/thread dumps to diagnose a hang (which threads hold which locks).

**Holding a lock across a blocking call stalls everything.** §53.2.
Never hold a lock during IO, a subprocess, or a slow computation. Keep critical sections to the compound mutation only.

**`with` releases locks on exception; manual acquire/release may not.**
`with lock:` guarantees release even if the body raises. A manual `lock.acquire()` without a `try/finally` leaks the lock on an exception, a permanent deadlock. Always use `with`.

**More locks, more deadlock surface.**
Every additional lock multiplies the ordering constraints. Fewer locks (via isolation and high-level tools) is safer, not just faster.

**Livelock and starvation are cousins.**
Beyond deadlock: livelock (threads actively retry but make no progress) and starvation (a thread never gets a contended lock) are related concurrency failures. The same discipline, minimize sharing, use fair high-level tools, helps.

**Cross-process deadlocks too.**
The same cyclic-wait deadlock happens with `multiprocessing` locks and with the `Process`/`Queue` pipe-buffer deadlock (Chapters 47, 52). The ordering and high-level-tool rules apply across processes as well as threads.

---

## 53.5 Connections

**Backward.**
This synthesizes the locking of Chapters 46 (the race, the lock), 49 (high-level coordination), and 51 (lock only what needs it). The `with`-releases-on-exception guarantee is the context-manager protocol. The "prefer isolation" rule is `queue.Queue` (Chapter 49), `threading.local` (Chapter 51), and return-and-combine (Chapter 48). The cross-process form is Chapters 47 and 52.

**Forward.**
The free-threaded build (Deep L) makes more code run truly in parallel, raising the stakes on lock discipline and introducing the memory-model concerns (visibility, ordering) that the GIL used to hide. Lock-free data structures and atomics are Deep L. `asyncio`'s single-threaded model (Deep F) avoids most locking by never running two coroutines' code at once, a different answer to the same problem.

**Across books.**
Deadlock-free design is a hard requirement for **Book I**: a trading system that hangs is a system that stops trading, silently, mid-session, the worst possible failure. The order-book system minimizes locks by design (queue hand-offs between stages, per-connection thread-local state, immutable messages), imposes a strict global lock order on the few places that need multiple locks (always by instrument `id`), keeps critical sections to the bare compound mutation (never holding a lock across IO or matching), and uses `acquire(timeout=...)` so a would-be deadlock surfaces as a logged, recoverable error rather than a silent hang, the §53.2 rules applied as an operational safety requirement, closing Deep E where **Book I**'s reliability begins.

---

## 53.6 Exercises

**1. Avoid the deadlock.** Reproduce §53.1's ordered version and confirm it completes. Then (carefully, with a `timeout` so it does not hang your machine) write the *inconsistent*-order version and observe the deadlock via the timeout firing. Explain the cycle and how ordering breaks it.

**2. Re-entrancy.** Show a plain `Lock` self-deadlocking when the same thread acquires it twice (again, with a timeout), and fix it with `RLock`. Then refactor to remove the re-entrancy need entirely (a private lock-assumed method). Explain why the refactor is often better than `RLock`.

**3. Small critical sections.** Take code that holds a lock across a slow operation (a `sleep` standing in for IO) and show the contention. Move the slow operation outside the lock and show the improvement. Explain rule 4.

**4. Measure the lock types.** Reproduce §53.3. Confirm `RLock` is ~1.2x `Lock`. Argue why the *design* reason to prefer `Lock` matters more than the 1.2x.

**5. The design question.** Deep E's thesis is "concurrency correctness comes from design, not from adding locks." Defend it using the whole volume: workload classification (Chapters 46-47), high-level tools (48-49), lock-only-what-needs-it (51), and deadlock avoidance (this chapter). What single design choice most reduces deadlock risk, and why?

---

## 53.7 Summary and cross-references

- A **deadlock** is a cycle of threads each holding a lock the other needs, hanging forever with no error. The classic cause is **inconsistent lock ordering**; the fix is a **global lock order** (all threads acquire in the same order), which makes a cycle impossible.
- A plain **`Lock` re-acquired by the same thread self-deadlocks**; **`RLock`** allows re-entrancy (tracking owner + recursion count), at a small cost.
- **The rules:** (1) prefer designs with few/no locks (isolation, queues, thread-local); (2) one consistent global lock order; (3) small critical sections; (4) never hold a lock across a blocking call; (5) `acquire(timeout=...)` to detect deadlocks; (6) use high-level tools; (7) prefer `Lock` over `RLock`.
- **Measured:** `RLock` is **1.2x** `Lock` (owner + recursion bookkeeping). Use `Lock` by default; needing `RLock` signals a too-coarse critical section, refactor to a lock-assumed private method.
- **Deep E's thesis:** concurrency correctness comes from **design** (minimize shared state, order locks, use high-level tools), not from reactively adding locks. The free-threaded future (Deep L) raises the stakes.
- **Edges:** deadlocks are silent (use timeouts + thread dumps); always `with lock:` (releases on exception); cross-process deadlocks apply too (Chapters 47, 52).

**Cross-references.** The race and the lock → Chapter 46. High-level coordination → Chapter 49. Lock only what needs it → Chapter 51. Isolation (queues, thread-local, return-and-combine) → Chapters 48, 49, 51. Free-threading and the memory model → Deep L. `asyncio` (avoids locking) → Deep F. Cross-process deadlocks → Chapters 47, 52. This closes Deep E (Concurrency I).
