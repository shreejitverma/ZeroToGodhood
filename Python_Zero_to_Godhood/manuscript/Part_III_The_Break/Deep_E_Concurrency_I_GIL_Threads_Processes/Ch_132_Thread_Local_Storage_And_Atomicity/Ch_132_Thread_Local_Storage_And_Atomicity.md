# Chapter 51: Thread-Local Storage and Atomicity

Chapter 46 taught the lock, and Chapter 49 taught the higher-level tools that encapsulate it.
This chapter teaches the two ways to write correct concurrent code that need *no* lock at all, and the discipline of locking only what actually requires it.
The reflex "threads are involved, so lock everything" is wrong in both directions: it locks operations that are already safe (pure overhead, measured **5x** for a needless lock), and it can lull you into thinking a lock makes a *compound* operation atomic when it does not.
Correct, fast concurrent code comes from knowing precisely which operations need synchronization and which do not.

Two tools remove the need for a lock.
**`threading.local()`** gives each thread its *own* copy of an attribute, so there is no shared state to race on, per-thread state (a connection, a buffer, a request context) is isolated by construction, not by locking.
And **atomicity under the GIL**: some operations, `list.append`, a single `dict` or attribute assignment, `list.pop`, complete in *one uninterruptible bytecode*, so concurrent uses are already safe without a lock, while read-modify-write (`counter += 1`, Chapter 46) is *several* bytecodes and is not.
Knowing the difference is the whole skill: lock the compound operations, leave the atomic ones alone, and use thread-local storage where threads do not need to share.

**This is Deep E's thread-correctness chapter.**
It refines Chapter 46 (the race, the lock) with the cases where no lock is needed, complements Chapter 49 (the coordination tools), and sets up the free-threaded build (Deep L), where atomicity guarantees change because there is no GIL.

## Section index

- **51.1** Thread-local storage, and what is atomic under the GIL
- **51.2** Locking only what needs it
- **51.3** Measurement: the cost of a needless lock
- **51.4** Edges and failure modes
- **51.5** Connections
- **51.6** Exercises
- **51.7** Summary and cross-references

Listings live under `code/ch132/` and are re-executed by `make verify` on both verification interpreters.

---

## 51.1 Thread-local storage, and what is atomic under the GIL

```python
# code/ch132/l01_thread_local.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- threading.local: each thread has its OWN value (no sharing) ---
  each thread's own _tls.value : {0: 0, 1: 100, 2: 200, 3: 300}
  the main thread never set it : False   (separate per thread)
--- list.append is ATOMIC under the GIL: correct WITHOUT a lock ---
  4 threads x 10,000 lock-free appends : 40000
  equals 40,000 exactly (no lost items): True
--- but read-modify-write is NOT atomic (Chapter 46): that needs a lock ---
  atomic (no lock)  : append, pop, single dict/attr assignment
  NOT atomic (lock) : counter += 1, check-then-act, multi-step updates
--- the rule ---
  use threading.local for per-thread state; lock only compound
  read-modify-write, single append/assignment is already atomic
```

**`threading.local()`** is one object whose attributes are *per thread*.
Each of the four threads sets `_tls.value` and reads back *its own* value (`0, 100, 200, 300`), and the main thread, which never set it, does not have the attribute at all (`hasattr` is `False`).
There is no sharing, so there is nothing to race on and no lock needed.
This is the right tool for **per-thread state**: a database connection or HTTP session per worker thread, a per-thread scratch buffer, a per-thread request context (web frameworks use thread-local storage for "the current request"). Instead of a shared dict keyed by thread ID plus a lock, `threading.local` gives each thread private storage for free.

**Atomicity under the GIL** is the second lock-free tool, and the subtler one.
`list.append` completes in a *single* bytecode (`LIST_APPEND` / a `CALL` that the interpreter runs atomically under the GIL), so it cannot be interrupted partway: four threads doing 10,000 lock-free appends each produce *exactly* 40,000 items, no lost updates, no lock.
The atomic operations include `list.append`/`pop`, `dict[key] = value` and `dict.get`, a single attribute assignment, and similar single-bytecode operations on built-in containers.

But the contrast with Chapter 46 is the crucial line: **read-modify-write is *not* atomic.**
`counter += 1` is *load, add, store*, three bytecodes, and the GIL can switch between them, so concurrent `+=` loses updates (Chapter 46's race) and *needs* a lock. Likewise "check-then-act" (`if x in d: d[x] += 1`) and any multi-step update span multiple bytecodes and race.
So the atomic/non-atomic line is: **single-bytecode operations on built-ins are atomic (no lock); anything that reads a value, computes, and writes it back is not (lock).**

---

## 51.2 Locking only what needs it

The practical discipline follows directly, and it cuts both ways against the "lock everything" reflex.

**Do not lock atomic operations.** §51.1, §51.3.
A single `append`, `pop`, or `dict`/attribute assignment is already thread-safe; wrapping it in a lock adds cost (5x, §51.3) and, worse, invites the lock-ordering deadlocks of Chapter 46 for no benefit. If a shared structure is only ever mutated by atomic single operations (a work list that threads only `append` to, a cache that threads only assign single keys to), it needs no lock.

**Do lock compound operations.**
Anything that spans multiple bytecodes, and could therefore be interleaved by a GIL switch, needs a lock (or a lock-free structure like `queue.Queue`, Chapter 49):

- **Read-modify-write:** `counter += 1`, `total += x`, `d[k] += 1`.
- **Check-then-act:** `if k not in d: d[k] = compute()` (two threads can both pass the check), `if q: q.pop()` (the item can vanish between check and pop).
- **Multi-step invariants:** updating two related fields that must change together (a balance and a log), moving an item between two structures.

**Prefer isolation over synchronization.**
`threading.local` (per-thread state) and the "return-and-combine" pattern (each thread computes into its *own* result, the main thread merges at the end, as `concurrent.futures` encourages, Chapter 48) avoid shared mutable state entirely, and un-shared state needs no lock. The best lock is the one you do not need because nothing is shared.

The rule: **lock compound operations on shared mutable state; leave atomic operations and per-thread state unlocked.**
This is both a correctness rule (compound operations *will* race without a lock) and a performance rule (locking atomic operations is waste, §51.3).
It requires knowing which operations are atomic, which is CPython-specific and, importantly, **changes under free-threading** (Deep L): without the GIL, even single operations may need internal locking, so relying on GIL atomicity is a portability caveat, the safe, portable habit is to lock compound operations explicitly and not depend on implicit atomicity for correctness across implementations.

---

## 51.3 Measurement: the cost of a needless lock

**Methodology.** `code/ch132/bench_atomic_lock.py`.
A bare `list.append` (already atomic) versus a lock-protected one, `min` of 5 runs, 5,000,000 operations.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| `list.append` | ns | vs bare |
|---|---|---|
| bare (already atomic) | 15.9 | 1.0x |
| lock-protected (needless) | 79.3 | **5.0x** |

Wrapping an already-atomic append in a lock makes it **5.0x** slower (4.2x on 3.14.6), for **no benefit**, the append was already safe.
The 5x is the lock's `acquire`/`release` cost (even an uncontended lock is a real operation) added to an operation that did not need it.

The lesson is the over-locking discipline of §51.2 in numbers.
"Threads are involved, so I'll lock everything" is a common and costly reflex: it slows every guarded operation several-fold, and it multiplies the surface for deadlocks (Chapter 46), all to protect operations that were already atomic.
The correct habit is the opposite: **lock the minimum**, the compound read-modify-write and check-then-act operations that genuinely race, and leave single atomic operations and per-thread state unlocked.
This is not a licence to under-lock, a compound operation without a lock is a real race (Chapter 46's lost updates), and *that* bug is far worse than the 5x. The point is *precision*: lock exactly what needs it, neither more (waste and deadlock risk) nor less (races).

The deeper current, running through all of Deep E, is that correct concurrency comes from *understanding what is shared and what is atomic*, not from reflexively locking or reflexively trusting.
`threading.local` removes sharing; GIL atomicity removes the need to lock single operations; and explicit locks (or `queue.Queue`) protect the compound operations that remain.
And the coming free-threaded world (Deep L) sharpens the point: when the GIL no longer provides implicit atomicity, the code that already locked its compound operations explicitly, and relied on isolation rather than implicit atomicity, is the code that ports cleanly, another reason the precise discipline of this chapter is the right one even while the GIL still makes some over-trust survivable.

---

## 51.4 Edges and failure modes

**GIL atomicity is CPython-specific and changes under free-threading.** §51.2.
Relying on `append`/`dict`-assignment atomicity for *correctness* is not portable (other implementations, and the free-threaded build, may differ). Prefer explicit locks (or `queue.Queue`) for correctness-critical shared mutations; treat atomicity as a performance nicety, not a guarantee to build on.

**Read-modify-write and check-then-act always need a lock.** §51.1.
`+= `, `if k in d: ...`, and multi-step updates span bytecodes and race. This is not optional; the §51.3 warning against over-locking does not license under-locking these.

**`threading.local` state does not transfer to child threads or tasks.**
A thread-local value set in one thread is absent in threads that thread spawns, and in `asyncio` tasks (which need `contextvars`, Deep F, not `threading.local`). It is per *thread*, strictly.

**`threading.local` in a thread pool persists across tasks.**
A `ThreadPoolExecutor` reuses threads, so thread-local state set by one task lingers for the next task on the same thread. This is a feature (per-thread connection reuse) and a hazard (stale state leaking between unrelated tasks); reset it if tasks must not share.

**Over-locking causes deadlocks, not just slowness.** §51.3.
More locks mean more lock-ordering opportunities (Chapter 46). A needless lock is not merely 5x slower; it is a deadlock waiting for a second needless lock. Fewer locks is safer.

**Atomicity is per operation, not per statement.**
`d[k] = d.get(k, 0) + 1` looks like one line but is a read (`get`) then a write (`[]=`), two operations, a race. One *bytecode* is atomic; one *line* is not.

**`contextvars` is the async-aware successor.**
For "current context" state that must follow `asyncio` tasks (not OS threads), use `contextvars.ContextVar` (Deep F), which is thread-*and*-task-local. `threading.local` is for threads only.

---

## 51.5 Connections

**Backward.**
The race that motivates all this, and the lock that fixes compound operations, is Chapter 46. The higher-level lock-free coordination (`queue.Queue`) is Chapter 49. Return-and-combine (isolation over sharing) is the `concurrent.futures` model of Chapter 48. GIL atomicity is a consequence of the GIL itself (Chapter 46).

**Forward.**
`contextvars` (the async/task-aware version of thread-local) is Deep F. The free-threaded build (Deep L) removes the GIL and thus the implicit atomicity this chapter relies on, changing what needs locking, and lock-free data structures and the memory model become first-class there. `queue.Queue` (Chapter 49) is the lock-free structure that sidesteps most of this.

**Across books.**
Thread-local storage and atomicity discipline shape **Book I**'s concurrent code: a per-thread market-data buffer or database connection uses `threading.local` (no sharing, no locks), a shared work list threads only `append` to needs no lock, and the genuinely shared, compound-updated state (a running aggregate, an order book touched by multiple threads) is locked precisely. The order-book system locks its compound updates (the book's price-level modifications, which are read-modify-write) and leaves its atomic single-operation structures (append-only event logs) unlocked, uses `threading.local` for per-connection state, and prefers `queue.Queue` hand-offs over shared mutable state where it can, the §51.2 precision applied so that the matching path holds locks only where a race would actually occur, minimizing both contention and deadlock risk.

---

## 51.6 Exercises

**1. Per-thread state.** Reproduce §51.1's `threading.local`: each thread sets and reads its own value; the main thread's is separate. Then use it for a realistic per-thread resource (a fake "connection"). Explain why this needs no lock.

**2. Atomic versus not.** Show that 4 threads appending to a shared list without a lock give the exact total (atomic), but 4 threads doing `counter += 1` without a lock lose updates (not atomic). Explain the bytecode difference.

**3. Measure over-locking.** Reproduce §51.3. Confirm locking an atomic append is ~5x slower. Then find a compound operation in your code that *does* need the lock and show it races without one. State the precise rule.

**4. The check-then-act trap.** Write `if k not in d: d[k] = expensive()` run by multiple threads and show two threads both compute `expensive()` (the check-then-act race). Fix it with a lock or `dict.setdefault`. Explain why one line was two operations.

**5. The design question.** GIL atomicity lets some operations skip locks, but it is CPython-specific and changes under free-threading (Deep L). Argue whether relying on it is wise, and how the free-threaded future changes the advice. What discipline (explicit locks on compound ops, isolation via thread-local/return-and-combine) ports cleanly, and why?

---

## 51.7 Summary and cross-references

- **`threading.local()`** gives each thread its **own** copy of an attribute, per-thread state with **no sharing and no lock**. Use it for per-thread connections, buffers, and context.
- **Some operations are atomic under the GIL** (single-bytecode: `list.append`/`pop`, a single `dict`/attribute assignment), so concurrent uses need **no lock**. But **read-modify-write** (`counter += 1`), **check-then-act**, and multi-step updates span bytecodes and **must be locked** (Chapter 46).
- **Measured:** locking an already-atomic append is **5.0x** slower for no benefit. The discipline: **lock only compound operations on shared mutable state**; leave atomic operations and per-thread state unlocked, neither over-lock (waste, deadlock risk) nor under-lock (races).
- **Prefer isolation over synchronization:** `threading.local` and return-and-combine avoid shared state entirely, and un-shared state needs no lock.
- **Edges:** GIL atomicity is CPython-specific and **changes under free-threading** (rely on explicit locks for correctness, not implicit atomicity); one bytecode is atomic but one *line* may not be; thread-local is per-thread only (use `contextvars` for async); pool threads persist thread-local state across tasks.

**Cross-references.** The race and the lock → Chapter 46. Lock-free coordination (`queue.Queue`) → Chapter 49. Return-and-combine → Chapter 48. `contextvars` (async-aware) → Deep F. Free-threading (changes atomicity) → Deep L.
