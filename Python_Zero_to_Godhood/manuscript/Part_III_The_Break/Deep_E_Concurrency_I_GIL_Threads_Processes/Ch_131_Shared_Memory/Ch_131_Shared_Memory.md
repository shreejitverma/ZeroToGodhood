# Chapter 50: Shared Memory

Chapter 47 gave multiprocessing its power (real CPU parallelism via separate processes) and named its cost (data is pickled and copied to each worker).
For small arguments that cost is trivial, but for *large* data, a big array shared among several workers, it dominates: sending an 80 MB array to four workers copies 320 MB, and the pickling and copying can cost more than the computation.
This chapter is the escape.
`multiprocessing.shared_memory` creates a **named block of memory that multiple processes map into their own address spaces**, so they share the *same physical bytes* with **zero copy**.
One process creates and fills it; the others attach by name and read (or write) the identical memory.
Measured, sharing an 80 MB array with four workers this way is **2.1x** faster than pickling it to each, and the gap widens with more workers or larger data.

This is the cross-process form of a pattern the book has now shown three times.
Chapter 44 shared a buffer with **C** in one call (zero copy across the language boundary); Chapter 19 escaped the per-object header with contiguous typed memory; here, `shared_memory` shares a buffer across the **process** boundary (zero copy across the address-space boundary).
The unifying idea, running through Deep M and Deep E alike, is that large data should cross a boundary as a *reference to shared memory*, not as a copy, and this is that idea applied to processes.

**This is Deep E's shared-memory chapter.**
It is the zero-copy answer to Chapter 47's pickling tax, connects to Chapter 44 (buffer sharing) and Deep Q's buffer protocol (Chapter 37, the `memoryview`/`ndarray` views used here), and completes the multiprocessing data story.

## Section index

- **50.1** A named block, mapped into many processes
- **50.2** When to share, and the costs of sharing
- **50.3** Measurement: sharing versus copying large data
- **50.4** Edges and failure modes
- **50.5** Connections
- **50.6** Exercises
- **50.7** Summary and cross-references

Listings live under `code/ch131/` and are re-executed by `make verify` on both verification interpreters.

---

## 50.1 A named block, mapped into many processes

```python
# code/ch131/l01_shared_memory.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- create a shared block and fill it via a NumPy view ---
  shared block created; size >= requested : True
--- a SECOND handle to the same name sees the SAME memory (no copy) ---
  handle 2 sees handle 1's data : [10, 20, 30, 40, 50]
  write via handle 2, read via handle 1 : 999   (same physical memory)
--- real worker PROCESSES attach by name and read it (no pickling) ---
  two worker processes summed the shared block : [150, 150]   (10+20+30+40+50)
--- the rule ---
  shared_memory maps one physical block into many processes: share large
  data by NAME with zero copy, instead of pickling it to each worker
```

`shared_memory.SharedMemory(create=True, size=...)` allocates a block of memory the operating system can map into multiple processes, and gives it a **name**.
You lay a typed view over its `.buf` (here a NumPy `ndarray`, the buffer protocol of Deep Q Chapter 37) and fill it. (The block's actual `size` is rounded up to a page boundary by the OS, which is why the listing checks `>= requested` rather than an exact number, the exact size is platform-specific.)

The defining property is **shared physical memory**.
A *second* handle opened by the same **name** maps the *same bytes*: it sees the data (`[10,20,30,40,50]`), and a write through the second handle (`arr2[0] = 999`) is immediately visible through the first, because there is only *one* physical block, viewed twice.
No copy, no serialization, the two handles are windows onto identical memory.

And this works **across processes**, which is the point.
The worker processes in the `Pool` attach to the block by name (`SharedMemory(name=...)`) and read it, summing `[10,20,30,40,50]` to `150` in *each* worker, without the array ever being pickled or copied.
The parent created the data once; the workers read it in place.
This is exactly what pickling avoids paying for: instead of sending each worker its own 80 MB copy, you send each worker a short *name*, and they map the one shared block.
The mental model: `shared_memory` is a named region of RAM that lives outside any one process, and processes attach to it like opening a shared file, one copy of the data, many readers (and writers).

---

## 50.2 When to share, and the costs of sharing

Shared memory is a sharp tool with real costs, and it is right only for a specific shape of problem.

**Use it for large, read-mostly data shared by multiple processes.** §50.3.
The win scales with data size and worker count (each avoided copy is bytes not moved), so it pays for big arrays, lookup tables, model weights, datasets, that many workers read. For small arguments, pickling is trivial and shared memory's complexity is not worth it.

**The costs are lifecycle and synchronization.**

- **Manual lifecycle.** You must `create`, `attach`, `close` (each handle), and `unlink` (once, by the creator) the block. Forget to `unlink` and the block **leaks** (it outlives the process, a named region the OS keeps until explicitly freed or reboot, unlike normal memory that refcounting reclaims). This is memory management by hand, outside Chapter 31's automatic reclamation, because the block is shared and no single process owns it.
- **Manual synchronization.** Shared memory is *shared mutable state across processes*, so if workers **write** to it concurrently, you have the race conditions of Chapter 46 (now across processes), and you need `multiprocessing.Lock`/`Semaphore` to coordinate. Read-only sharing (all workers read, none write) needs no synchronization and is the safe, common case.
- **Raw bytes, no structure.** Like `ctypes` (Chapter 43) and unlike pickling, a shared block is untyped bytes; you must agree on the dtype, shape, and layout between processes (the listing hardcodes `(5,), int64`). A mismatch reinterprets memory as garbage.

So shared memory trades multiprocessing's *safety* (separate memory, no shared-state races, Chapter 47) for *performance* (no copying), reintroducing the shared-state hazards of threads (Chapter 46) at the process level.
The rule: **share large read-mostly data via `shared_memory`; keep small data and anything workers mutate as pickled arguments** (or synchronize the writes explicitly).
Higher-level wrappers, `multiprocessing.Array`/`Value` (typed shared objects with optional locking) and `SharedMemoryManager` (which handles cleanup), reduce the lifecycle burden, and `ProcessPoolExecutor` with shared memory is a common production combination.

---

## 50.3 Measurement: sharing versus copying large data

**Methodology.** `code/ch131/bench_shared_memory.py`.
An 80 MB array (10,000,000 `int64`) summed by four worker processes, passed two ways: as a pickled `Pool.map` argument (copied to each worker) versus via a shared block (attached by name, no copy).
Wall-clock, `perf_counter`.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| pass 80 MB to 4 workers | time | vs pickled |
|---|---|---|
| pickled (copy to each worker) | 644 ms | 1.0x |
| `shared_memory` (no copy) | 313 ms | **2.1x faster** |

Sharing is **2.1x** faster than pickling (2.0x on 3.14.6).
The pickled version serializes and copies the 80 MB array to *every* worker, four copies, 320 MB moved, plus the pickle/unpickle CPU cost; the shared version moves the data *zero* times, the workers map the one physical block by name.
And this understates the advantage: the gap **widens with more workers** (pickling copies per worker, sharing does not) and **with larger data** (the copy cost scales, the name does not). At eight workers and a gigabyte, pickling would copy 8 GB while sharing still copies nothing.

The finding completes Chapter 47's cost analysis.
Multiprocessing's pickling tax (Chapter 47) is not fundamental, it is the cost of *copying*, and shared memory removes it for the case that matters most: large data read by many workers.
This is the same zero-copy principle as Chapter 44 (share a buffer with C in one call) and the buffer protocol (Chapter 37, share a buffer between Python objects), now at the process boundary: **large data crosses as a shared reference, not a copy.**
The decision rule for CPU-parallel work over large data is therefore two-step: use `multiprocessing`/`ProcessPoolExecutor` for the parallelism (Chapters 47-48), and `shared_memory` for the data (this chapter), so you get multi-core computation *without* the copying that would otherwise erase the gain.
The alternative on the horizon, the free-threaded build (Deep L), sidesteps both pickling *and* shared-memory lifecycle by keeping everything in one process's shared heap, the same zero-copy goal reached by removing the process boundary entirely rather than tunneling through it.

---

## 50.4 Edges and failure modes

**You must `unlink` the block, or it leaks.** §50.2.
A shared block outlives the process until explicitly `unlink`ed (it is OS-managed, not refcounted). Forgetting leaks a named region until reboot. Use `try/finally`, `SharedMemoryManager`, or `multiprocessing.Array` (which cleans up) to avoid this.

**Concurrent writes race.** §50.2.
Shared memory is shared mutable state; if workers write, use `multiprocessing.Lock`/`Semaphore`. Read-only sharing is safe without synchronization and is the common case.

**Layout must be agreed, no structure is stored.** §50.2.
A block is raw bytes; producer and consumer must agree on dtype/shape/offset. A mismatch yields garbage (like `ctypes`, Chapter 43). Store or fix the layout explicitly.

**Size is rounded up.** §50.1.
The OS rounds the block to a page multiple, so `.size` exceeds your request. Do not assume an exact size; use `>=` or track your logical size separately.

**Resource-tracker warnings.**
Python's resource tracker warns about (and may clean up) leaked shared blocks at exit, but relying on it is fragile. `unlink` explicitly.

**It is same-machine only.**
`shared_memory` shares RAM on one host; it does not work across machines. For distributed sharing you need a different mechanism (a message broker, a distributed store, RDMA), a Deep U topic.

**`close` versus `unlink`.**
Each handle `close`s its own mapping (per process); exactly one `unlink` frees the underlying block (once, by the owner). Confusing them either leaks (no unlink) or crashes other users (unlink while attached).

**Not for small data.** §50.3.
The lifecycle and synchronization complexity is only worth it for large data. For small arguments, pickling is simpler and fast enough.

---

## 50.5 Connections

**Backward.**
Shared memory is the zero-copy fix for Chapter 47's pickling cost, and the cross-process form of Chapter 44's buffer sharing with C and Chapter 37's buffer protocol (the `ndarray`/`memoryview` views used here). Concurrent writes reintroduce Chapter 46's races at the process level. Manual `unlink` is memory management outside Chapter 31's automatic reclamation.

**Forward.**
`multiprocessing.Array`/`Value` and `SharedMemoryManager` (higher-level, auto-cleanup) and `ProcessPoolExecutor` + shared memory (the production combination) are Deep E. The free-threaded build (Deep L) removes the need for shared memory (one shared heap). Distributed data sharing across machines is Deep U.

**Across books.**
Shared memory is how **Book I** parallelizes computation over large in-memory datasets without copying them per worker: a historical price matrix, a feature table, a set of model weights loaded once and shared across worker processes that each compute over it. The order-book system loads its large reference data (an instrument universe, a precomputed table) into a shared block once at startup, and its `ProcessPoolExecutor` workers attach and read it in place, so a multi-gigabyte dataset is resident *once*, not once per worker, exactly the §50.3 win, and it keeps the data read-only in the workers to avoid the §50.2 synchronization, reserving writes for the parent. Where the data changes, it uses message passing instead; where it is large and static, shared memory.

---

## 50.6 Exercises

**1. Share a block.** Reproduce §50.1: create a shared block, attach a second handle, confirm they see the same memory (a write through one is visible in the other), then have worker processes attach by name and read it. Explain "same physical memory."

**2. Measure the win.** Reproduce §50.3. Confirm sharing beats pickling for an 80 MB array. Then vary the worker count and data size and show the gap widening. Explain why (copies scale, the name does not).

**3. The leak.** Create a shared block and exit *without* `unlink`ing it. Observe the resource-tracker warning (and, on your OS, the lingering block). Fix it with `try/finally`. Explain why shared memory is not automatically reclaimed.

**4. Coordinate a write.** Have multiple workers *write* to a shared block concurrently without synchronization and observe corruption; fix it with a `multiprocessing.Lock`. Explain how shared memory reintroduces Chapter 46's races across processes.

**5. The design question.** Shared memory removes multiprocessing's copying cost but reintroduces shared-state hazards and manual lifecycle. Argue when the trade is worth it (§50.3's large read-mostly data) and when pickling's safety is better. Then argue how the free-threaded build (Deep L) changes the calculus, does it make shared memory obsolete, and at what cost?

---

## 50.7 Summary and cross-references

- **`multiprocessing.shared_memory`** creates a **named block of RAM mapped into multiple processes**, so they share the **same physical bytes with zero copy**. One process creates and fills it; others attach by **name** and read/write the identical memory (across processes, no pickling).
- **Measured:** sharing an 80 MB array with four workers is **2.1x** faster than pickling it to each (313 vs 644 ms), and the gap **widens with more workers and larger data** (copies scale, the name does not).
- This is the **zero-copy** principle at the process boundary, the same idea as Chapter 44 (buffer to C) and Chapter 37 (buffer protocol): large data crosses as a **shared reference, not a copy**. Pair it with `ProcessPoolExecutor` for CPU-parallel work over large data.
- **Costs:** manual **lifecycle** (`create`/`attach`/`close`/`unlink`, or it leaks, no automatic reclamation) and manual **synchronization** if workers write (Chapter 46's races, across processes). Raw bytes, agreed layout required. Use it for **large, read-mostly** data only.
- **Edges:** `unlink` exactly once or leak; size rounds up; same-machine only; `close` (per handle) vs `unlink` (once); not for small data.

**Cross-references.** Multiprocessing's pickling cost (this fixes) → Chapter 47. Zero-copy buffer sharing with C → Chapter 44. Buffer protocol / `memoryview` → Deep Q Chapter 37. Shared-state races (now cross-process) → Chapter 46. `Array`/`Value`/`SharedMemoryManager`, `ProcessPoolExecutor` → the rest of Deep E. Free-threading (one shared heap) → Deep L. Distributed sharing → Deep U.
