# Chapter 48: Multiprocessing and IPC

Chapter 8 established that threads cannot run Python bytecode in parallel (the GIL), and that processes can,
a CPU-bound workload ran ~2.2x faster across processes than threads. So the reflex is "parallelize it with a
process `Pool`." That reflex is right when the work is compute-heavy and wrong when it is not, and the
difference is *data*. A process has no shared memory with its parent by default, so every argument you send
a worker is **pickled** (Chapter 42), piped across, and unpickled, and every result makes the return trip.
When compute dominates, that IPC cost is negligible and the pool wins. When data dominates, the pool spends
all its time shipping bytes: measured, a workload with trivial compute and 4 MB payloads per task runs in
**~0 ms serially** but **~60 ms on a 4-process pool**, the pool is *pure overhead*, slower than not
parallelizing at all.

That caveat, multiprocessing buys parallel CPU but charges serialization for every argument and result, is
this chapter's subject. It closes **Deep R** by completing Chapter 8's story: not just "processes give real
parallelism," but "and here is what you pay for it, and when the payment exceeds the gain." The escape hatch,
shared memory that avoids the copy, ties back to Chapter 44's `mmap`.

## Section index

- **48.1** A process `Pool`, and the pickle boundary
- **48.2** Why IPC can erase the parallelism win
- **48.3** Measurement: compute-bound vs data-bound
- **48.4** Edges and failure modes
- **48.5** Connections
- **48.6** Exercises
- **48.7** Summary and cross-references

Listings live under `code/ch048/` and are re-executed by `make verify` on both interpreters.

---

## 48.1 A process `Pool`, and the pickle boundary

```python
# code/ch048/l01_multiprocessing.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- Pool.map: distribute work across worker processes ---
  pool.map(square, 1..6) : [1, 4, 9, 16, 25, 36]
--- arguments and results cross the boundary by pickling ---
  is a lambda picklable? : False (so it cannot be sent to a worker)
--- each worker is a separate interpreter (its own PID, not the parent's) ---
  worker PID != parent   : True (work ran in another process)
  parent is MainProcess  : True
```

`multiprocessing.Pool` runs a function across several worker processes. `pool.map(square, [1..6])`
distributes the six inputs, runs `square` in the workers (in parallel, on separate cores, each a separate
interpreter with its own GIL), and collects the results in order. Because each worker is a real process,
this achieves the true CPU parallelism threads cannot (Chapter 8).

The middle block exposes the boundary. A worker is a *separate interpreter*, so the function and its
arguments must travel there, and they travel by **pickling**. A `lambda` is not picklable, so it cannot be
sent to a worker (`is a lambda picklable? False`); worker functions must be module-level, defined so they can
be imported by name (which is why the listing's helpers are top-level). The bottom block confirms the
separateness: the worker's PID differs from the parent's, the work genuinely ran in another process, and the
parent is not itself a worker. That separateness is the source of both the parallelism and the pickle cost.

Note the `if __name__ == "__main__":` guard: multiprocessing's `spawn` start method re-imports the module in
each worker, and without the guard that re-import would recursively spawn more processes. The guard is not
optional.

---

## 48.2 Why IPC can erase the parallelism win

A process pool changes the cost model of a task from "run the function" to "pickle the arguments, pipe them
to a worker, unpickle them, run the function, pickle the result, pipe it back, unpickle it." The added terms
are the **IPC cost**, and their size is proportional to how much *data* crosses the boundary, independent of
how much *compute* the function does.

So the pool's value is a race between two quantities: the compute it parallelizes (a win, roughly divided by
the worker count) and the data it must serialize (a loss, roughly the payload size times the pickle/pipe
rate, both ways). When compute per task is large relative to its data (the number-crunching case), the win
dominates and the pool is much faster. When data per task is large relative to its compute (the "ship a big
array, do a little to it" case), the serialization dominates and the pool is *slower than serial*, because
the serial version does the little compute with *zero* IPC while the pool pays to move megabytes it barely
touches. §48.3 shows both ends of this race.

The design consequence: **multiprocessing is for compute-bound work whose inputs and outputs are small
relative to the computation.** When the data is large, either keep the work in one process, or avoid the copy
with *shared memory*, a `multiprocessing.shared_memory.SharedMemory` block or an `mmap` (Chapter 44) that all
processes map, so the bytes exist once and are not pickled across. Shared memory is how you get process
parallelism over large data without paying to ship it.

---

## 48.3 Measurement: compute-bound vs data-bound

**Methodology.** `code/ch048/bench_ipc.py`. Two workloads on a 4-process `Pool` versus serial: **A**, heavy
compute (8 x 3,000,000-iteration loops) with tiny data; **B**, trivial compute (`len`) with big data (8 x
4 MB payloads). `min` over runs; the benchmark manages its own `Pool`. Process/IPC-bound and noisy. CPython
3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| workload | serial | pool(4) | outcome |
|---|---|---|---|
| **A** heavy compute, tiny data | **~717 ms** | **~256 ms** | **2.80x faster** (parallelism wins) |
| **B** trivial compute, big data | **~0 ms** | **~61 ms** | pool is **pure overhead** (slower) |

Workload **A** is the case multiprocessing is for: the CPU work dominates, so four workers finish in well
under a third of the serial time (2.80x, the GIL sidestepped exactly as Chapter 8 showed). Workload **B** is
the trap: the compute is essentially nothing (`len` of a bytes object), so the serial version finishes in ~0
ms, while the pool spends ~61 ms pickling and piping eight 4 MB payloads to workers that barely touch them.
The pool did not speed anything up; it *added* the entire cost of shipping the data. The `2.80x` and the
`slower-than-serial` are the same principle read at its two extremes.

The rule: **reach for a process `Pool` when the work is compute-bound and the per-task data is small; do not
when the data is large relative to the compute.** Before parallelizing, ask what crosses the boundary: if it
is megabytes per task and the function does little, the pool will lose. For process parallelism over large
data, use shared memory (above) so the data is not copied. This completes Chapter 8's guidance: processes
give real parallelism, *and* the parallelism is only a win when it is not eaten by the IPC.

---

## 48.4 Edges and failure modes

**Parallelizing data-bound work.** §48.3. If the per-task payload is large and the compute small, the pool is
slower than serial. Measure what crosses the boundary before parallelizing.

**Non-picklable arguments.** §48.1. Lambdas, local functions, open files, locks, and many objects cannot be
pickled and so cannot be sent to workers. Worker functions and their arguments must be picklable (module-
level functions, plain data).

**Missing `if __name__ == "__main__"`.** §48.1. Under the `spawn` start method (the default on macOS and
Windows), the module is re-imported per worker; without the guard, that re-import spawns more processes,
recursively. Always guard the entry point.

**Queue-plus-join deadlock.** A `Process` that `put`s a large object on a `Queue` while the parent `join`s it
can deadlock: the child blocks writing to a full pipe, the parent blocks in `join` without reading. Drain the
queue *before* joining, or use `Pool`/`concurrent.futures`, which manage this correctly.

**Start-method differences.** `fork` (default on Linux) shares memory copy-on-write and is fast but unsafe
with threads and some libraries; `spawn` (default on macOS/Windows) is clean but re-imports and is slower to
start. Set the start method explicitly for portable behavior, and do not assume `fork` semantics.

**Pool startup and teardown cost.** Creating a pool spawns processes (and, under `spawn`, imports your
module in each), which is not free. For many small batches, create the pool once and reuse it; do not create
a pool per call.

---

## 48.5 Connections

**Backward.** The GIL and the threads-vs-processes measurement this chapter completes are Chapter 8. The
pickling that every argument and result undergoes, and its security and cost, is Chapter 42, here it is the
IPC mechanism, safe because both ends are your own trusted processes. The shared-memory escape hatch is
Chapter 44's `mmap`. The compute the workers do is ordinary Python (Chapters 2-17).

**Forward.** `concurrent.futures.ProcessPoolExecutor` is the higher-level façade over this machinery, and
`asyncio` (Chapters 10-11) handles the I/O-bound case processes are wrong for. The per-interpreter-GIL
subinterpreters of Chapter 23 (PEP 734) are the emerging in-process alternative that shares an address space
without full processes. Distributed execution across machines (Dask, Ray, Spark) generalizes this to a
cluster in **Deep U**.

**Across books.** The compute-vs-data question is how Book II decides where **Book III** work runs. A
**Book III** pipeline parallelizes CPU-bound stages (tokenization, feature extraction) across a process pool
only when the per-item data is small enough that shipping it does not dominate; for large tensors it uses
shared memory or keeps the work in one process with a vectorized library (NumPy, **Deep T**), which
sidesteps the GIL in C without any IPC. The §48.3 measurement is the calculation behind that architectural
choice. **Deep U** owns the distributed-execution seam.

---

## 48.6 Exercises

**1. Reproduce both ends.** Run §48.3's benchmark and confirm the pool wins on compute-bound work and loses
on data-bound work. Explain, in terms of what crosses the process boundary, why the same tool helps one and
hurts the other.

**2. Find the crossover.** Fix the payload size and increase the compute per task until the pool goes from
slower-than-serial to faster. Explain what you are balancing and why a crossover exists.

**3. Hit the pickle wall.** Try to `pool.map` a lambda and a module-level function over the same data. Show
the lambda fails and the named function works. Explain why workers require picklable callables.

**4. Avoid the copy.** Put a large array in `multiprocessing.shared_memory.SharedMemory` (or an `mmap`,
Chapter 44), have workers read it by name instead of receiving it as an argument, and show the IPC cost
drops. Explain what shared memory changed.

**5. The design question.** Chapter 8 said processes give real parallelism; this chapter says that
parallelism can be erased by IPC. Reconcile them into a single rule for when to use a process pool. Your
answer must use the §48.3 numbers, address the compute-to-data ratio, and explain when shared memory or a
vectorized single-process library is the better answer than a pool.

---

## 48.7 Summary and cross-references

- **`multiprocessing.Pool`** runs a function across worker processes for true CPU parallelism (each worker a
  separate interpreter, GIL sidestepped, Chapter 8). Worker functions and arguments must be **picklable**
  (module-level, plain data); guard the entry with `if __name__ == "__main__"`.
- **There is no shared memory by default:** every argument and result is pickled across the process boundary.
  That IPC cost is proportional to the data, not the compute.
- **Measured:** heavy-compute/tiny-data is **2.80x faster** on a 4-process pool; trivial-compute/big-data
  makes the pool **pure overhead** (~61 ms of pickling vs ~0 ms serial). Multiprocessing is not free
  parallelism.
- **Use a pool for compute-bound work with small per-task data;** for large data, use **shared memory**
  (Chapter 44) to avoid the copy, or keep the work in one process with a vectorized library (Deep T).

**Cross-references.** GIL and threads-vs-processes → Chapter 8. Pickling as IPC → Chapter 42. Shared memory
and `mmap` → Chapter 44. Subinterpreters → Chapter 23. `asyncio` for I/O-bound → Chapters 10-11. Distributed
execution → Deep U. Vectorized single-process compute → Deep T.
