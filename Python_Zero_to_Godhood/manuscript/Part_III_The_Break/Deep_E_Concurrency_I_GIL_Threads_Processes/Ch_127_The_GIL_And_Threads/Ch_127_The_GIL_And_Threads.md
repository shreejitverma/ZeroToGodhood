# Chapter 46: The GIL and Threads

No single design decision draws more Python criticism than the **Global Interpreter Lock**, and none is more misunderstood.
The GIL is a mutex inside the interpreter that lets **only one thread execute Python bytecode at a time**.
Create ten threads doing pure-Python computation on a ten-core machine, and they will not run ten times faster, they will take turns on the one GIL and finish about as slowly as one thread, plus overhead.
That is the notorious limitation, and it is real: **CPython threads do not give CPU-bound parallelism.**

But the reflexive conclusion, "Python threads are useless", is wrong, and the measurement shows exactly why.
The GIL is **released** during blocking operations, network reads, disk IO, `time.sleep`, and anything that waits on the outside world, so while one thread waits, others run.
For **IO-bound** work, threads overlap their waits and give near-linear speedup (measured **1.97x** on two threads); for **CPU-bound** work, they do not (**1.06x**).
The GIL does not make threads useless; it makes them a tool for **concurrency** (overlapping waits), not **parallelism** (using many cores for computation).
Knowing which kind of work you have is the whole game, and this chapter opens **Deep E** by establishing it.

**This is the canonical home for the GIL and threading.**
It builds on Chapter 31 (reference counting is what the GIL primarily protects, an unsynchronized `Py_INCREF`/`Py_DECREF` from two threads would corrupt the count), Chapter 19 (shared objects), and Chapter 8 (the 3.2 GIL rewrite, the timeline moment this deep volume follows). The free-threaded build that *removes* the GIL, and biased reference counting, are **Deep L**; multiprocessing (parallelism via separate processes) is later in Deep E.

## Section index

- **46.1** Threads share memory; the GIL serializes; a lock synchronizes
- **46.2** Why the GIL exists, and what it protects
- **46.3** Measurement: threads help IO-bound work, not CPU-bound
- **46.4** Edges and failure modes
- **46.5** Connections
- **46.6** Exercises
- **46.7** Summary and cross-references

Listings live under `code/ch127/` and are re-executed by `make verify` on both verification interpreters.

---

## 46.1 Threads share memory; the GIL serializes; a lock synchronizes

```python
# code/ch127/l01_gil_threads.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- the GIL rotates between threads on a fixed interval ---
  sys.getswitchinterval() : 0.005 s   (GIL check interval)
--- threads SHARE memory: the counter is one object in all threads ---
  4 threads x 100,000 increments (locked) : 400000
  equals 4 * 100,000 exactly              : True
--- threads append to ONE shared list (lock-protected) ---
  5 threads each appended once : list length 5
  all five values present      : True
--- join() synchronizes: after join, all workers have finished ---
  active threads after all joins : 1   (just main)
--- the rule ---
  threads share memory (cooperate on state) but need a Lock for
  read-modify-write; the GIL serializes bytecode, one thread at a time
```

Three facts define CPython threading.

**Threads share memory.**
Unlike processes (which copy), threads run in one address space, so the `counter` and the `shared` list are the *same objects* in every thread. This is threading's advantage, threads cooperate on shared state with no copying or serialization, and its hazard, they can step on each other.

**The GIL serializes bytecode.**
Only one thread runs Python bytecode at a time, and the interpreter rotates between threads on a timer (`sys.getswitchinterval()`, default **5 ms**): every interval, the running thread is asked to release the GIL so another can run. So threads *interleave* in fine slices, but never truly *parallelize* Python execution.

**A lock is still needed for read-modify-write.**
The GIL protects individual bytecodes, but `counter += 1` is *several* bytecodes (load, add, store), and the GIL can switch between them. Two threads doing `counter += 1` concurrently can both load the same value, both add one, and both store, losing an increment, the classic **race condition**. A `threading.Lock` (the `with lock:` block) makes the update atomic, and the result is exactly `400000` (4 threads x 100,000), deterministically. Without the lock, the total would be *unpredictable and usually too low*.
This is the crucial subtlety: **the GIL does not make your code thread-safe.** It serializes bytecode, but your logical operations span multiple bytecodes, so you still need locks (or atomic data structures) around shared mutable state. The GIL prevents interpreter *corruption*, not application *races*.

`join()` provides synchronization: the main thread waits until each worker finishes, so after all joins, `active_count()` is 1 (just main), a deterministic barrier.

---

## 46.2 Why the GIL exists, and what it protects

The GIL is not an accident or an oversight; it is a deliberate trade that made CPython simple and fast for the common case, at a cost that only became painful with many-core machines.

**What it protects: reference counts (and interpreter state).**
Every object has a refcount (Chapter 31) touched on nearly every operation, and `Py_INCREF`/`Py_DECREF` are *not atomic*, they are plain memory read-modify-writes. If two threads incref the same object simultaneously without synchronization, the increments can collide (exactly the §46.1 race, at the C level), corrupting the count, leading to premature frees (use-after-free) or leaks. The GIL prevents this by ensuring only one thread mutates interpreter state at a time. It also protects the internal invariants of built-in containers (`list`, `dict`), making many single operations effectively atomic.

**What it buys:**

- **Fast single-threaded execution.** With the GIL, refcounting needs no atomic operations (which are several times slower than plain writes, Chapter 31), so single-threaded code, the overwhelmingly common case, runs at full speed. A naive lock-free-refcount alternative would tax every operation.
- **Simple C extensions.** An extension author can touch Python objects without worrying about concurrent access, because the GIL is held. This made the C-extension ecosystem (NumPy, etc.) far easier to build, a major reason for Python's scientific-computing dominance.
- **Simple interpreter internals.** No fine-grained locking on every container and object.

**What it costs:**

- **No CPU parallelism within a process.** The §46.3 headline: CPU-bound Python cannot use multiple cores in one process. You must use multiprocessing (separate processes, separate GILs) or the free-threaded build.

The trade, then: the GIL sacrifices in-process CPU parallelism to gain single-threaded speed, C-extension simplicity, and internal simplicity.
For decades that was a good trade (most workloads are IO-bound or offload CPU work to C), and it is only the many-core era that made it costly enough to motivate the free-threaded build (PEP 703, **Deep L**), which removes the GIL and pays for it with **biased reference counting** to keep the single-threaded case fast, the same trade, renegotiated.

---

## 46.3 Measurement: threads help IO-bound work, not CPU-bound

**Methodology.** `code/ch127/bench_gil.py`.
Two units of work, done serially versus on two threads, for a CPU-bound task (a Python arithmetic loop) and an IO-bound task (`time.sleep(0.2)`).
Wall-clock, `perf_counter`.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| 2 units of work | serial | 2 threads | speedup |
|---|---|---|---|
| CPU-bound (Python loop) | 415 ms | 390 ms | **1.06x** |
| IO-bound (`sleep`) | 406 ms | 206 ms | **1.97x** |

The two rows are the entire practical lesson.
**CPU-bound: no speedup** (1.06x; on 3.14.6, 0.95x, actually slightly *slower* from thread overhead). The two threads compute pure Python, so they contend for the one GIL and take turns, finishing no faster than serial. Adding threads to CPU-bound Python does not help and can hurt.
**IO-bound: near-2x speedup** (1.97x, 1.99x on 3.14.6). `time.sleep` (like a network or disk read) **releases the GIL** while waiting, so the two threads' waits *overlap*, two 0.2 s sleeps finish in ~0.2 s wall-clock instead of 0.4 s.

This gives the rule for CPython threading:

- **Use `threading` for IO-bound concurrency:** waiting on network, disk, database, subprocess, or user input. The GIL is released during the wait, so threads overlap and you get real concurrency (and `asyncio` is often even better for high-concurrency IO, a Deep F/async topic).
- **Do not use `threading` for CPU-bound parallelism:** it does not help. Use **`multiprocessing`** (separate processes, each with its own GIL, real multi-core parallelism, at the cost of copying data between them, later in Deep E), or the **free-threaded build** (Deep L), or offload the computation to a C extension / NumPy that releases the GIL during its own work.

The deeper point is a diagnostic habit: **classify your workload before choosing a concurrency tool.** "My program is slow, I'll add threads" is the wrong reflex, threads help only if the slowness is *waiting*, not *computing*. Measure whether the bottleneck is IO (threads/async help) or CPU (processes/native code help), and the right tool follows. The GIL makes this classification unusually consequential in Python, which is why it is the first thing Deep E teaches.

---

## 46.4 Edges and failure modes

**The GIL does not make code thread-safe.** §46.1.
It serializes bytecode, but your operations span multiple bytecodes. Shared mutable state still needs a `Lock` (or thread-safe structures like `queue.Queue`). "The GIL protects me" is a common and dangerous misconception.

**Threads do not speed up CPU-bound Python.** §46.3.
Adding threads to a compute loop gives ~1x (or worse). Use processes or native code for CPU parallelism.

**Race conditions are nondeterministic and load-dependent.**
An unsynchronized shared-state bug may pass every test on a quiet machine and fail under load (when the GIL switches at the wrong moment). Reason about correctness with locks, not by testing; a race that "never happens" in testing will happen in production.

**Deadlocks from lock ordering.**
Two threads each holding one lock and waiting for the other's deadlock forever. Acquire locks in a consistent global order, use `with` (so locks release on exception), and keep critical sections small. (This is why the earlier draft's `Process`+`Queue`+`join` patterns hung, a coordination deadlock; prefer high-level tools.)

**Prefer high-level concurrency tools.**
`concurrent.futures.ThreadPoolExecutor`, `queue.Queue` (thread-safe by design), and `threading.Event`/`Condition` are safer than hand-rolled locks and raw threads. Reach for the lowest-level primitive last.

**Daemon threads and shutdown.**
A daemon thread is killed abruptly at interpreter exit (no cleanup); a non-daemon thread keeps the process alive until it finishes. Choose deliberately, and `join()` threads you need to complete.

**The switch interval is a tuning knob, rarely touched.**
`sys.setswitchinterval()` changes how often the GIL rotates. Lowering it improves responsiveness but adds overhead; the default 5 ms is well-chosen. Do not tune it without a measured reason.

**`time.sleep(0)` and GIL fairness.**
Releasing the GIL cooperatively (via IO or `sleep`) is how threads yield; a tight pure-Python loop holds the GIL for its full 5 ms slice, so a compute-heavy thread can starve others' responsiveness. Break long computations or offload them.

---

## 46.5 Connections

**Backward.**
The GIL primarily protects **reference counting** (Chapter 31): non-atomic `Py_INCREF`/`Py_DECREF` would race without it. Shared objects across threads are Chapter 19's single-address-space model. The 3.2 GIL rewrite (the new GIL with a time-based switch instead of a bytecode-count one) is Chapter 8, the timeline moment Deep E follows. Locks and `with` are the context-manager protocol.

**Forward.**
**`multiprocessing`** (separate processes for CPU parallelism, and the `fork`/`spawn`/data-copying trade) is the next Deep E topic. **`concurrent.futures`** (the high-level pool API) and **`queue.Queue`** (thread-safe communication) are Deep E. **`asyncio`** (single-threaded IO concurrency, often better than threads for high-fan-out IO) is Deep F. The **free-threaded build** (PEP 703, removing the GIL) and **biased reference counting** are **Deep L**; **subinterpreters** (per-interpreter GILs, PEP 684) are Chapter 23 / Deep L.

**Across books.**
The IO-bound-versus-CPU-bound classification is a **Book I** architecture decision: a trading or data system's network and disk waits are handled with threads or async (the GIL released, concurrency free), while its CPU-heavy work, matching, pricing, model inference, is pushed to native code (NumPy, a C/Rust extension) that releases the GIL, or to separate processes. The order-book system uses threads for its many concurrent network connections (IO-bound, the §46.3 win) and offloads its compute to GIL-releasing native kernels, so the GIL is never the bottleneck, the workload-classification discipline of §46.3 turned into the system's concurrency architecture.

---

## 46.6 Exercises

**1. Prove the sharing and the race.** Reproduce §46.1's locked counter (get exactly 400,000). Then remove the lock and run it many times; observe totals *below* 400,000, and that they vary. Explain why, in terms of `counter += 1` being multiple bytecodes and the GIL switching.

**2. Measure the two workloads.** Reproduce §46.3. Confirm CPU-bound threading gives ~1x and IO-bound ~2x. Then scale to 4 threads and show IO-bound approaches 4x while CPU-bound stays ~1x. Explain both.

**3. Classify a program.** Take a program that (a) downloads several URLs and (b) computes checksums of large files. Decide which part is IO-bound and which CPU-bound, and which concurrency tool fits each. Justify with §46.3.

**4. Deadlock and fix.** Write two threads that acquire two locks in opposite orders and deadlock. Fix it by ordering the acquisitions. Explain the lock-ordering rule.

**5. The design question.** The GIL trades in-process CPU parallelism for single-threaded speed, C-extension simplicity, and internal simplicity (§46.2). Argue whether that was the right trade for Python's first three decades, and why the many-core era changed the calculus enough to motivate the free-threaded build (Deep L). What does free-threading have to pay (biased refcounting) to remove the GIL, and does that reframe or settle the trade?

---

## 46.7 Summary and cross-references

- The **GIL** lets **only one thread run Python bytecode at a time**, rotating between threads every ~5 ms (`sys.getswitchinterval()`). Threads are real OS threads that **share memory** (one address space).
- **The GIL does not make code thread-safe:** a read-modify-write like `counter += 1` is multiple bytecodes and races between threads; use a **`Lock`** (or `queue.Queue`) for shared mutable state. The GIL prevents interpreter corruption, not application races.
- **It exists to protect non-atomic reference counting** (Chapter 31) and interpreter state, buying **fast single-threaded execution** and **simple C extensions**, at the cost of **no in-process CPU parallelism**.
- **Measured:** two threads give **~1x** on CPU-bound work (the GIL serializes) and **~2x** on IO-bound work (`sleep`/IO releases the GIL). **Use `threading` for IO-bound concurrency; use `multiprocessing`/native code/free-threading for CPU parallelism.** Classify the workload first.
- **Edges:** races are nondeterministic (reason with locks, not tests); deadlocks from lock ordering; prefer `ThreadPoolExecutor`/`queue.Queue`; daemon threads die at exit.

**Cross-references.** Reference counting (what the GIL protects) → Chapter 31. Shared objects / single address space → Chapter 19. The 3.2 GIL rewrite → Chapter 8. `multiprocessing`, `concurrent.futures`, `queue` → the rest of Deep E. `asyncio` → Deep F. Free-threading (removing the GIL), biased refcounting, subinterpreters → Deep L / Chapter 23.
