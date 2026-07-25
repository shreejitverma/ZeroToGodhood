# Chapter 47: Multiprocessing and Parallelism

Chapter 46 ended on a hard limit: the GIL means CPython threads cannot parallelize CPU-bound work.
It also named the escape, and this chapter takes it.
If one interpreter has one GIL, then *many interpreters* have *many GILs*, and running your computation in separate **processes**, each a full Python interpreter with its own GIL, gives real multi-core parallelism.
The `multiprocessing` module makes that nearly as easy as threading: a `Pool` of worker processes, a `map` over your inputs, and the work runs in parallel.
Measured, four CPU-bound tasks across four processes finish **2.87x** faster than serially, the speedup threads (Chapter 46) could not deliver.

But multiprocessing is the mirror image of threading, and its costs are exactly threading's benefits inverted.
Threads *share* memory (cheap communication, dangerous races); processes have *separate* memory (safe isolation, expensive communication).
A global changed in a worker does not affect the parent, and every input and result must be **pickled** and copied across the process boundary.
So multiprocessing pays a startup-and-copying tax that threads avoid, and it wins only when each task does enough CPU work to dwarf that tax, the same "amortize the boundary" rule that governed the C FFI (Chapters 43-44), now at the process boundary.

**This is Deep E's parallelism chapter.**
It is the CPU-bound counterpart to Chapter 46's IO-bound threading, building on the GIL (why processes are needed), Chapter 42 (`pickle`, how data crosses processes), and Chapter 31 (each process has its own refcounting). The free-threaded build, which gives CPU parallelism *without* separate processes, is **Deep L**.

## Section index

- **47.1** Separate processes, separate memory, `Pool.map`
- **47.2** The costs: startup, pickling, and when it pays
- **47.3** Measurement: real CPU parallelism
- **47.4** Edges and failure modes
- **47.5** Connections
- **47.6** Exercises
- **47.7** Summary and cross-references

Listings live under `code/ch128/` and are re-executed by `make verify` on both verification interpreters.

---

## 47.1 Separate processes, separate memory, `Pool.map`

```python
# code/ch128/l01_multiprocessing.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- separate memory: a worker's change does not reach the parent ---
  a worker incremented its own _counter : True
  the PARENT's _counter is untouched     : True   (separate address space)
--- Pool.map distributes work and returns ORDERED results ---
  Pool.map(square, [1..5]) : [1, 4, 9, 16, 25]
--- workers are separate PROCESSES (own PID, own interpreter, own GIL) ---
  every worker PID differs from the parent : True
  the parent is one process                : True
--- the rule ---
  multiprocessing = separate processes, own GIL each (real CPU
  parallelism), separate memory, data copied by pickling
```

The defining contrast with threads (Chapter 46) is **separate memory**.
A worker increments the module global `_counter`, but that change is to the *worker's own copy*, in the worker's own address space, so the **parent's `_counter` stays 0**.
There is no shared state to race on, which is multiprocessing's safety advantage: no locks needed for the workers' private data, no `counter += 1` race (Chapter 46). Each process is an island.
This is why the per-worker values in the listing are reported as stable *facts* (a worker did increment, the parent did not change) rather than exact numbers, the OS scheduler decides which worker runs which task, so the specific values are nondeterministic, but the isolation is absolute.

**`Pool.map`** is the workhorse.
`pool.map(square, [1,2,3,4,5])` distributes the five inputs across the pool's worker processes, runs `square` in parallel, and collects the results **in input order** (`[1,4,9,16,25]`), so you get parallelism with the simple semantics of a `map`.
Each worker is a genuinely separate process (a different PID from the parent, its own interpreter, its own GIL), which is precisely what breaks the GIL barrier: four workers on four cores run four GILs, four streams of Python bytecode, truly at once.

The mental model: `multiprocessing` turns "run this function over these inputs" into "farm these inputs out to a pool of separate Python processes and gather the answers." It is `map`, parallelized across processes, and the separate-process design is what makes the parallelism real.

---

## 47.2 The costs: startup, pickling, and when it pays

Separate processes are not free, and the costs determine when multiprocessing actually helps.

**Process startup.**
Each worker is a fresh Python interpreter. On macOS and Windows the default start method is **`spawn`**: the child launches a new Python, re-imports your module (which is why worker functions must be at module level and importable, and why top-level code must be guarded by `if __name__ == "__main__"`, without the guard, `spawn` re-runs your main code in every child, forking a fork-bomb of pools). On Linux the default has been **`fork`** (cheaper, copies the parent's memory lazily via copy-on-write), though `fork` interacts badly with threads and is being deprecated as a default. Either way, starting workers costs milliseconds, paid once per pool.

**Pickling and copying.**
Inputs are **pickled** (Chapter 42) in the parent, sent to the worker over a pipe, and unpickled there; results make the reverse trip. So:

- The data (and the worker function) must be **picklable**. A lambda, a local function, an open file, or a lock cannot be pickled, hence worker functions live at module level.
- Large inputs/outputs cost real time and memory to serialize and copy. Sending a 1 GB array to each of eight workers copies 8 GB.

**When it pays.**
Multiprocessing wins when **each task's CPU work dwarfs the startup-and-pickling tax**, big, coarse-grained, compute-heavy tasks with small inputs and outputs. It *loses* when tasks are fine-grained (the per-task overhead exceeds the work) or the data is large (pickling dominates). This is the FFI rule again (Chapters 43-44): **amortize the boundary**, cross the process boundary rarely with a lot of work each time, never often with a little.

The escape hatches for the data-copying cost are their own topics: **shared memory** (`multiprocessing.shared_memory`, `Array`/`Value`) lets processes share a buffer without copying (useful for large read-mostly data), and **`chunksize`** on `Pool.map` batches tasks to reduce per-task overhead. And the whole model has a coming alternative: the **free-threaded build** (Deep L) gives multi-core parallelism *within one process*, no separate interpreters, no pickling, at the cost of the concurrency-safety concerns the GIL used to hide.

---

## 47.3 Measurement: real CPU parallelism

**Methodology.** `code/ch128/bench_multiprocessing.py`.
Four CPU-bound tasks (each an 8,000,000-iteration Python arithmetic loop) done serially versus on a `Pool` of four processes.
Wall-clock, `perf_counter`.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| 4 CPU-bound tasks | time | speedup |
|---|---|---|
| serial (one process) | 803 ms | 1.0x |
| `Pool` of 4 processes | 280 ms | **2.87x** |

Four processes finish **2.87x** faster than serial (2.61x on 3.14.6), and the results are identical.
This is the parallelism Chapter 46 showed threads *cannot* give (they got ~1x on the same CPU work): each process has its own GIL and runs on its own core, so four streams of Python bytecode execute genuinely at once.

Two honest notes on the number.
First, the speedup is **~2.87x, not 4x**, even with four tasks and four processes, because of the process-startup and pickling overhead (§47.2), plus the machine's core contention and the `spawn` cost. The overhead is a fixed tax that keeps the speedup below the ideal; larger per-task work would push it closer to 4x (the tax amortizes), smaller work would push it below (the tax dominates).
Second, this is *CPU* work with *tiny* data (an integer in, an integer out), the best case for multiprocessing; a version passing large arrays would spend much of its time pickling and could show *no* speedup at all.

So the rule for CPU parallelism in CPython: **use `multiprocessing` for coarse-grained, compute-heavy, small-data tasks**, and expect a speedup *approaching* the core count but discounted by the process/pickling overhead.
Measure the actual speedup, do not assume linear scaling, the overhead is real and workload-dependent.
For fine-grained or large-data parallelism, multiprocessing's copying tax can erase the gain, and the alternatives (shared memory, or the free-threaded build) become necessary.
This completes Chapter 46's dichotomy: **threads for IO-bound concurrency** (GIL released during waits), **processes for CPU-bound parallelism** (separate GILs), each with its own boundary cost to amortize, and the workload classification decides which.

---

## 47.4 Edges and failure modes

**Guard the entry point with `if __name__ == "__main__"`.** §47.2.
Under `spawn` (macOS/Windows default), each worker re-imports the module; without the guard, top-level code that creates a `Pool` re-runs in every child, spawning processes recursively (a crash or hang). This is mandatory, not optional, for multiprocessing code.

**Worker functions and data must be picklable.** §47.2.
Lambdas, local/nested functions, open files, locks, and many objects cannot be pickled. Worker functions live at module level; pass plain data. A `PicklingError` at pool submission is this bug.

**Large data kills the speedup.** §47.2, §47.3.
Pickling and copying big inputs/outputs to each worker can dominate. Use `shared_memory`/`Array` for large read-mostly data, or reconsider whether the task is worth parallelizing.

**Speedup is sublinear and workload-dependent.** §47.3.
Do not assume N processes give Nx. Startup, pickling, and core contention discount it. Measure.

**`fork` interacts badly with threads and is being deprecated.**
Forking a multithreaded process can deadlock (a lock held by a thread that does not exist in the child). Prefer `spawn` (set via `mp.set_start_method("spawn")`) for robustness, especially in libraries. This is behind many "works on my Linux machine, hangs on macOS" bugs.

**Deadlocks and hangs from manual `Process`/`Queue`/`join`.**
Hand-rolled process coordination (a `Process` writing to a `Queue` the parent reads after `join`) can deadlock (a full pipe blocks the child, which never exits, so `join` waits forever). Prefer the high-level `Pool`/`concurrent.futures.ProcessPoolExecutor`, which manage this correctly.

**Exceptions in workers surface at result collection.**
An exception in a `Pool.map` task is re-raised in the parent when you read the results, not silently swallowed, but the worker's traceback is limited. Handle errors explicitly for robust pipelines.

**Process pools have startup latency.**
Creating a pool costs milliseconds (spawning interpreters). For repeated work, create the pool once and reuse it; do not spin up a pool per small batch.

---

## 47.5 Connections

**Backward.**
Multiprocessing exists *because* of the GIL (Chapter 46): separate processes have separate GILs. Data crossing processes is `pickle` (Chapter 42), which is why picklability is required. Each process has its own reference counting and memory (Chapters 31, 19). The `spawn` re-import connects to the import system (Deep G).

**Forward.**
`concurrent.futures.ProcessPoolExecutor` (the high-level, `Future`-based API unifying process and thread pools) and `multiprocessing.shared_memory`/`Array` (zero-copy sharing of large data, Chapter 44's buffer idea across processes) are Deep E. `asyncio` (IO concurrency) is Deep F. The **free-threaded build** (multi-core parallelism in one process, no pickling) is **Deep L**, the emerging alternative to multiprocessing for CPU parallelism.

**Across books.**
Process-based parallelism is how **Book I** uses all its cores for CPU-bound work the GIL would otherwise serialize: batch pricing of a portfolio, backtesting many parameter sets, feature computation over a dataset, each an embarrassingly-parallel, coarse-grained, small-data task, the §47.3 sweet spot. The order-book system farms independent CPU-heavy jobs (per-symbol analytics, scenario runs) to a `ProcessPoolExecutor`, keeps the per-task data small (parameters in, summary out) to stay on the right side of the pickling tax, and reserves shared-memory arrays for the few large read-mostly datasets, exactly the §47.2 cost management, and it uses threads/async (Chapter 46) for its IO. Workload classification (CPU to processes, IO to threads/async) is the concurrency architecture the two chapters together prescribe.

---

## 47.6 Exercises

**1. See the isolation.** Reproduce §47.1: a worker modifies a global and the parent's copy is unchanged; `Pool.map` returns ordered results; workers have different PIDs. Explain how separate memory both enables safe parallelism and forces pickling.

**2. Measure the speedup.** Reproduce §47.3. Confirm ~Nx-but-sublinear speedup for coarse CPU tasks. Then shrink each task's work drastically and show the speedup vanish (overhead dominates). Explain the amortization.

**3. The pickling tax.** Parallelize a task that takes a *large* array as input. Measure and show the pickling/copying can erase the speedup. Then use `shared_memory` (or make the data small) and show the improvement. Explain the boundary cost.

**4. The `__main__` guard.** Remove the `if __name__ == "__main__"` guard from a multiprocessing script and observe the failure under `spawn`. Restore it and explain why `spawn` requires it.

**5. The design question.** CPython offers *two* concurrency models with opposite trade-offs: threads (shared memory, one GIL, IO concurrency) and processes (separate memory, many GILs, CPU parallelism). Argue why both exist and how you choose, using Chapters 46-47's measurements. Then argue what the free-threaded build (Deep L) changes: does it make multiprocessing obsolete, or just add a third option?

---

## 47.7 Summary and cross-references

- **`multiprocessing`** sidesteps the GIL with **separate processes**, each a full interpreter with its **own GIL**, giving **real CPU parallelism** (which threads cannot, Chapter 46). `Pool.map` distributes a function over inputs across workers and returns ordered results.
- Processes have **separate memory** (a worker's change does not reach the parent, no shared-state races), but data crossing between them is **pickled and copied** (Chapter 42), and worker functions must be **picklable** (module-level).
- **Measured:** four CPU-bound tasks run **2.87x** faster on a 4-process pool than serially, the parallelism threads gave ~1x on. The speedup is **sublinear** (startup + pickling overhead) and vanishes for fine-grained or large-data tasks.
- **When it pays:** coarse-grained, compute-heavy, small-data tasks (amortize the process boundary, the FFI rule again). Use `shared_memory` for large data, `chunksize` for fine tasks.
- **Edges:** guard the entry point (`if __name__ == "__main__"`) for `spawn`; prefer `spawn` over `fork` (which deadlocks with threads); use `Pool`/`ProcessPoolExecutor` over hand-rolled `Process`/`Queue` (deadlock risk); speedup is sublinear, measure.

**Cross-references.** The GIL (why processes are needed) → Chapter 46. `pickle` (data across processes) → Chapter 42. Per-process memory/refcounting → Chapters 19, 31. `ProcessPoolExecutor`, `shared_memory` → the rest of Deep E. `asyncio` → Deep F. Free-threading (CPU parallelism without processes) → Deep L.
