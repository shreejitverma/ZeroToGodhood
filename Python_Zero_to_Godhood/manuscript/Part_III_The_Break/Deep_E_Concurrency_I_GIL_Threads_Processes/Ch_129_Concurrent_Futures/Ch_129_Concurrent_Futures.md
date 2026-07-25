# Chapter 48: `concurrent.futures`

Chapters 46 and 47 taught the two low-level concurrency primitives, raw `threading.Thread` and `multiprocessing.Pool`, and both chapters kept warning you off the hand-rolled versions: raw `Thread` with manual locks and `join`, raw `Process` with `Queue` and the deadlocks they invite.
This chapter is the tool they pointed to.
`concurrent.futures` is the **high-level, unified** concurrency API, one interface over both thread pools (`ThreadPoolExecutor`, for the IO-bound work of Chapter 46) and process pools (`ProcessPoolExecutor`, for the CPU-bound work of Chapter 47), so you write your concurrent logic once and choose threads-or-processes by changing a single word.

Its central abstraction is the **`Future`**: a handle to a result that is not ready yet.
You `submit` work and get a `Future` back immediately; you call `.result()` when you need the value, and it blocks until ready and re-raises any exception the worker hit.
This turns concurrency into something composable, submit many tasks, collect their futures, process results as they complete, without touching a lock or a queue.

But the executor is not free, and the measurement is the chapter's cautionary note: a pool over 100,000 *trivial* tasks is **~197x slower** than a plain loop, because each task pays scheduling overhead the trivial work cannot amortize.
The unified API removes the concurrency *boilerplate*, not the concurrency *cost*, so the amortization rule of the whole volume (Chapters 43-47) applies once more: pools are for **substantial** tasks, and a plain loop wins whenever the per-task overhead exceeds the per-task work.

**This is Deep E's high-level concurrency chapter.**
It unifies the threading (Chapter 46) and multiprocessing (Chapter 47) primitives under one API, uses the `Future` abstraction that `asyncio` (Deep F) generalizes, and is the recommended default for concurrent work.

## Section index

- **48.1** Futures, `submit`, `map`, and `as_completed`
- **48.2** The unified API, and choosing threads or processes
- **48.3** Measurement: the executor is not free
- **48.4** Edges and failure modes
- **48.5** Connections
- **48.6** Exercises
- **48.7** Summary and cross-references

Listings live under `code/ch129/` and are re-executed by `make verify` on both verification interpreters.

---

## 48.1 Futures, `submit`, `map`, and `as_completed`

```python
# code/ch129/l01_futures.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- submit returns a Future; result() gives the value ---
  ex.submit(work, 7).result() : 49
  future.done() after result  : True
--- map runs over inputs and returns results IN ORDER ---
  list(ex.map(work, [1,2,3,4])) : [1, 4, 9, 16]
--- as_completed yields futures as they finish (order not guaranteed) ---
  all results via as_completed (sorted) : [0, 1, 4, 9, 16]
--- an exception in a worker RE-RAISES at result() ---
  worker exception surfaced at result() : worker failed
--- the rule ---
  submit -> Future -> result(); map for ordered results; as_completed
  for results-as-ready; same API for ThreadPool (IO) and ProcessPool (CPU)
```

The `Future` is the whole model.
`ex.submit(work, 7)` schedules the call and returns a `Future` **immediately**, without waiting; the work runs in a pool worker.
`.result()` is where you collect: it blocks until the value is ready (`49`), and afterward `.done()` is `True`.
Crucially, `.result()` **re-raises** any exception the worker raised (the `boom` worker's `ValueError` surfaces at `f.result()`, not silently swallowed), so error handling is ordinary `try`/`except` at the collection point, no special worker-error plumbing.

Three ways to drive it, for three needs:

- **`submit`** for individual tasks you want fine control over (each returns a `Future` you can query, cancel, or attach a callback to).
- **`map`** for "run this over these inputs, results **in order**", the parallel `map`, returning results in input order (`[1,4,9,16]`) regardless of completion order.
- **`as_completed`** for "process results **as soon as each is ready**", it yields each `Future` the moment it finishes, in *completion* order (which is why the listing sorts them for determinism). This matters when tasks have varying durations and you want to act on the fast ones without waiting for the slow ones.

This is a far cleaner model than raw threads: no shared-state locks (each task returns its own result), no manual `join` (the `with` block waits for all workers at exit), no `Queue` plumbing (futures carry the results). The `Future` carries the value *and* the error *and* the completion status, so the concurrency reduces to "submit, then collect."

---

## 48.2 The unified API, and choosing threads or processes

The design payoff of `concurrent.futures` is that **the same code runs on threads or processes**, so you decide the concurrency model by the executor class alone.

`ThreadPoolExecutor` and `ProcessPoolExecutor` have the **identical interface**, `submit`, `map`, the `with` protocol, `Future`s, so the listing's logic works with either by changing only the import and constructor.
This lets you separate *what* runs concurrently (your task functions) from *how* it is parallelized (threads or processes), and switch based on the workload classification of Chapters 46-47:

- **`ThreadPoolExecutor`** for **IO-bound** work (network requests, file reads, database queries, waiting): the GIL is released during the waits (Chapter 46), so threads overlap and you get concurrency, cheaply (threads share memory, no pickling).
- **`ProcessPoolExecutor`** for **CPU-bound** work (computation): separate processes with separate GILs give real parallelism (Chapter 47), at the cost of pickling and startup.

So the decision procedure is: classify the workload (IO-bound to `ThreadPoolExecutor`, CPU-bound to `ProcessPoolExecutor`), write the task functions once, and pick the executor.
Because the process executor still requires picklable, module-level functions and pays the copying tax (Chapter 47), the switch is not *completely* free, but the *code* is the same, which is the ergonomic win.

`concurrent.futures` is therefore the **recommended default** for concurrent work in modern Python: it is safer than raw threads/processes (no manual locks, joins, or queues, so fewer deadlocks, the failure modes Chapters 46-47 warned about), it is uniform across the two models, and its `Future` abstraction composes.
Reach for raw `threading`/`multiprocessing` only when you need something the executor does not expose (a long-lived thread with custom lifecycle, a specific IPC pattern, shared-memory arrays); for the common "run these tasks concurrently and collect the results", `concurrent.futures` is the tool.

---

## 48.3 Measurement: the executor is not free

**Methodology.** `code/ch129/bench_executor_overhead.py`.
100,000 *trivial* tasks (`x + 1`) done as a plain list comprehension versus via `ThreadPoolExecutor.map`.
Wall-clock, `perf_counter`.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| 100,000 trivial tasks | time | vs loop |
|---|---|---|
| plain loop | 2.5 ms | 1.0x |
| `ThreadPoolExecutor` | 484.8 ms | **197x slower** |

The pool is **~197x slower** than a plain loop (187x on 3.14.6), a dramatic *pessimization*.
Each of the 100,000 tasks pays real overhead, creating a `Future`, queueing the task, dispatching it to a worker, marshalling the result back, and the trivial `x + 1` does far too little to amortize that.
Worse, the tasks are CPU work, so the threads serialize on the GIL (Chapter 46) *and* pay the scheduling overhead, the worst of both.

The lesson unifies the whole volume.
`concurrent.futures` removes the concurrency *boilerplate* but not the concurrency *cost*, and that cost is per-task, so:

- **Pools are for substantial tasks.** Submit a *few, big* tasks (each a network call, a heavy computation, a chunk of work), not *many, tiny* ones. The per-task overhead must be small relative to the per-task work.
- **To parallelize fine-grained work, batch it.** Instead of submitting one task per item (100,000 tasks), submit one task per *chunk* (a handful of tasks, each looping over thousands of items). One task then does a lot, amortizing the overhead. `Pool.map`'s `chunksize` and `executor.map`'s `chunksize` (for the process executor) do exactly this batching.
- **A plain loop wins when the work is trivial.** If per-task overhead exceeds per-task work, do not parallelize, the loop is faster and simpler.

This is the same **amortize the boundary** rule seen at the C FFI (Chapters 43-44) and the process boundary (Chapter 47), now at the task-scheduling boundary: crossing into a pool worker has a cost, so cross rarely with a lot of work each time.
The high-level API makes concurrency *easy to write*, which makes it easy to write *badly*, spraying trivial tasks at a pool, so the measurement is the guardrail: use pools for coarse-grained work, and reach for one only when the tasks are big enough to earn it.

---

## 48.4 Edges and failure modes

**A pool over trivial tasks is slower than a loop.** §48.3.
Per-task overhead (Future, queue, dispatch) dominates trivial work. Batch fine-grained work into fewer, larger tasks, or do not parallelize.

**Exceptions surface at `.result()`, not at `submit`.** §48.1.
A worker's exception is stored in its `Future` and re-raised when you call `.result()` (or iterate `map`'s results). Always collect results (or check futures) so errors are not silently lost.

**`ProcessPoolExecutor` needs picklable, module-level tasks.** §48.2, Chapter 47.
Same constraints as `multiprocessing`: no lambdas or local functions, picklable arguments, and the `if __name__ == "__main__"` guard under `spawn`. `ThreadPoolExecutor` has none of these (shared memory).

**`map` blocks on order; `as_completed` yields on completion.** §48.1.
`map` returns results in input order, so a slow early task delays later (already-done) results. Use `as_completed` when you want to process results as they finish, or `map` when order matters.

**The `with` block waits for all tasks.**
Exiting the executor's `with` calls `shutdown(wait=True)`, blocking until all submitted tasks finish. A task that hangs hangs the exit. Set timeouts on `.result(timeout=...)` where a task might not return.

**Pool size matters and defaults vary.**
`ThreadPoolExecutor`'s default worker count is `min(32, cpu+4)`; `ProcessPoolExecutor`'s is the CPU count. Too many threads for IO can overwhelm a service; too few underutilize. Size to the workload (many for high-latency IO, ~cpu for CPU).

**Do not share mutable state between pool tasks without synchronization.**
Even with the high-level API, if thread-pool tasks touch shared mutable state, the Chapter 46 races apply, use locks or return-and-combine. Process-pool tasks have separate memory (no shared state to race on, but no sharing either).

**Cancellation is limited.**
`Future.cancel()` works only if the task has not started. A running task cannot be interrupted (Python has no safe thread kill). Design tasks to finish or check a stop flag.

---

## 48.5 Connections

**Backward.**
`ThreadPoolExecutor` is the high-level form of Chapter 46 (threads, IO-bound); `ProcessPoolExecutor` of Chapter 47 (processes, CPU-bound), inheriting their constraints (pickling, the `__main__` guard). The `Future`'s stored-exception model is exceptions-as-values. The amortization lesson is Chapters 43-44 (FFI) and 47 (processes), at the task boundary.

**Forward.**
`asyncio` (Deep F) generalizes the `Future` into `await`able coroutines for single-threaded high-concurrency IO, often better than a thread pool for thousands of connections. `multiprocessing.shared_memory` (Chapter 47 / Deep E) addresses the process-pool copying cost. The free-threaded build (Deep L) changes what `ThreadPoolExecutor` can do for CPU work (real parallelism without processes).

**Across books.**
`concurrent.futures` is **Book I**'s default concurrency tool: a `ThreadPoolExecutor` fans out the many IO calls (market-data subscriptions, REST requests, database reads) that dominate a trading system's waiting, and a `ProcessPoolExecutor` farms out the coarse CPU jobs (backtests, batch pricing). The order-book system uses one executor per workload class, keeps tasks coarse (a whole backtest per task, not a tick, the §48.3 rule), collects results via `as_completed` to act on the fastest jobs first, and relies on the `Future`'s exception propagation so a failed job surfaces at collection rather than vanishing, the clean, composable concurrency this chapter's API provides, applied at the granularity the measurement demands.

---

## 48.6 Exercises

**1. Drive a pool three ways.** Reproduce §48.1: use `submit`/`result`, `map`, and `as_completed` on a `ThreadPoolExecutor`. Confirm `map` preserves order and `as_completed` does not. Trigger a worker exception and catch it at `.result()`. Explain the `Future` model.

**2. Swap the executor.** Take an IO-bound task and a CPU-bound task and run each on both `ThreadPoolExecutor` and `ProcessPoolExecutor`. Show which executor wins for which workload (Chapters 46-47), changing only the import. Explain the unified-API benefit.

**3. Find the overhead.** Reproduce §48.3. Confirm the pool is far slower for trivial tasks. Then batch the work (one task per chunk of 10,000 items) and show the pool becomes competitive or faster. Explain the amortization.

**4. Results as they finish.** Submit tasks with deliberately varying durations (`time.sleep` of different lengths) and use `as_completed` to print results in completion order. Compare to `map`. Explain when each is right.

**5. The design question.** `concurrent.futures` unifies threads and processes under one `Future`-based API. Argue what that abstraction buys (composability, safety, uniformity) over raw `threading`/`multiprocessing`, and what it hides that can bite (the §48.3 overhead, the process-pool pickling constraints). When would you still drop to the raw primitives?

---

## 48.7 Summary and cross-references

- **`concurrent.futures`** is the high-level, unified concurrency API: **`ThreadPoolExecutor`** (IO-bound, Chapter 46) and **`ProcessPoolExecutor`** (CPU-bound, Chapter 47) share one interface, so you choose the model by the executor class alone.
- The **`Future`** is a handle to a not-yet-ready result: **`submit`** returns one immediately, **`.result()`** blocks and **re-raises** worker exceptions, **`map`** returns results in order, **`as_completed`** yields them as they finish. No manual locks, joins, or queues.
- **Measured:** a pool over 100,000 *trivial* tasks is **~197x slower** than a plain loop, because per-task overhead (Future, queue, dispatch) dominates trivial work. **Pools are for substantial tasks; batch fine-grained work; a loop wins when the work is trivial** (amortize the boundary, again).
- **Recommended default** for concurrent work: safer and more uniform than raw threads/processes. Drop to the primitives only for custom lifecycles or IPC.
- **Edges:** exceptions surface at `.result()`; process pools need picklable module-level tasks + the `__main__` guard; `map` blocks on order; the `with` block waits for all tasks; cancellation is limited to not-yet-started tasks.

**Cross-references.** Threads / IO-bound → Chapter 46. Processes / CPU-bound → Chapter 47. Amortize the boundary → Chapters 43-44, 47. `asyncio` (the `Future` generalized) → Deep F. `shared_memory` → Deep E. Free-threading → Deep L.
