# Chapter 248: Concurrent Futures

## The constraint

Before Python 3.2, running work in parallel meant managing the machinery yourself.
To use threads, you created `Thread` objects, gave each one a target and a way to report back (usually a shared `Queue`), started them, joined them, and collected results by hand - and you had to arrange, separately, for an exception raised in a worker thread not to vanish silently into the background.
To use processes instead, you rewrote much of that against the `multiprocessing` API, with its own idioms.
The two were low-level, different from each other, and full of places to get the bookkeeping wrong.

The problem was one of *abstraction level*.
The thing a programmer usually wants to say is simple: "run these callables across a pool of workers and give me the results, and if one raises, tell me."
Nothing in that sentence mentions creating a thread, starting it, or joining it - those are implementation details of the pool, and having to spell them out every time was the source of the fragility.

The constraint Python 3.2 (2011, PEP 3148) answered: **provide one high-level, uniform API for pooled concurrent execution - submit work, get handles to pending results, collect them, and marshal errors - that works identically whether the workers are threads or processes.**

This is a two-track chapter, and the two tracks matter unusually much here.
The *mechanism* - the GIL and what it does to thread parallelism, when threads help (I/O-bound work) versus when only processes do (CPU-bound work), how processes marshal data across their boundary - is the entire subject of Deep Volume E, which follows immediately after this volume.
What this chapter owns is the release: the day concurrency got a clean, uniform *interface*, independent of the question of which pool to choose.

## What shipped

`concurrent.futures` provides an `Executor` - a worker pool - with two concrete forms: `ThreadPoolExecutor` and `ProcessPoolExecutor`.
You `submit` a callable and get back a `Future`, a handle to a result that may not exist yet; you call `map` to run a function over an iterable and get results back in input order; and a `Future` captures any exception and re-raises it when you ask for the result.
Listing 248.1 shows the API on today's interpreters, using threads and ordered `map` so the output is deterministic.

Verified output (CPython 3.13.5):

```text
--- an Executor is a pool you submit work to ---
  pool.submit(square, 9) returned a : Future
  future.result() blocks for the answer : 81
  submit() schedules the call and hands back a Future - a handle to
  a result that may not exist yet. result() waits for it. you never
  created, started, or joined a thread by hand
--- map() runs a function over an iterable, results IN INPUT ORDER ---
  pool.map(square, range(8)) : [0, 1, 4, 9, 16, 25, 36, 49]
  map() distributes the calls across the pool but returns results in
  the ORDER of the inputs, not the order they finished - so the
  output is deterministic even though the work ran concurrently
--- Futures carry exceptions across the boundary ---
  future.result() re-raised : ValueError(cannot process 42)
  an exception in a worker is captured by its Future and RE-RAISED
  when you call result(). errors cross the concurrency boundary
  cleanly instead of vanishing in a background thread
--- as_completed: react to results as they arrive (order sorted here) ---
  results via as_completed, then sorted : [0, 1, 4, 9, 16]
  as_completed() yields futures the moment each finishes - ideal for
  streaming results. completion order is nondeterministic, so we
  sort here purely to keep this listing's output stable
--- the uniformity: threads or processes, same code ---
  ThreadPoolExecutor and ProcessPoolExecutor share this API. swap
  the class and the SAME submit/map/Future code runs on processes
  instead of threads - the choice of pool is one line, not a rewrite
  (WHICH to pick, and why, is the GIL question Deep E answers)
--- the constraint answered ---
  hand-managing threads and processes - create, start, join, collect,
  marshal errors - was low-level and fragile. concurrent.futures
  (3.2) gave one high-level API: an Executor pool, submit() returning
  a Future, map() for ordered results, uniform across threads and
  processes. Deep E tells you which pool helps; this made USING one easy
```

## Why each part answers the constraint

**An Executor is a pool you submit to.**
The first block shows the core object: `pool.submit(square, 9)` returns immediately with a `Future`, and `future.result()` blocks until the answer (`81`) is ready.
Nowhere did the code create, start, or join a thread - the pool manages its workers, and you speak only in terms of work submitted and results awaited.
The `with` block ensures the pool is shut down cleanly when done.

**`map` gives ordered results despite concurrent execution.**
The second block shows `pool.map(square, range(8))` distributing eight calls across the pool and returning `[0, 1, 4, ..., 49]` - in *input* order, not completion order.
This is the property that makes concurrency safe to reason about: the work runs in parallel, but the results line up with the inputs, so the output is deterministic.
It is why the listing can use `map` and produce byte-identical output every run.

**Futures marshal exceptions.**
The third block addresses the failure that hand-rolled threading handled worst.
A worker that raises - `boom(42)` - does not crash silently in the background; its `Future` captures the exception and *re-raises* it in the caller when `result()` is called.
Errors cross the concurrency boundary cleanly and land where you can catch them, instead of disappearing into a dead thread.

**`as_completed` streams results.**
The fourth block shows the complementary pattern: `as_completed(futures)` yields each future the instant it finishes, ideal for reacting to results as they arrive rather than waiting for all of them.
The block is careful to note - and to sort around - the fact that completion order is *nondeterministic*: with concurrent work, whichever finishes first comes first, so the listing sorts purely to keep its own output stable.
This is an honest illustration of where concurrency's nondeterminism is real and where the API (via `map`) hides it.

**Uniformity across threads and processes.**
The fifth block names the payoff that ties the release together: `ThreadPoolExecutor` and `ProcessPoolExecutor` share this exact API.
Swap the class, and the same `submit`/`map`/`Future` code runs on processes instead of threads - a one-line change, not a rewrite against a different concurrency library.
The interface is uniform; only the choice of worker kind differs.

## The two-track note

The question this API deliberately leaves open is the one Deep Volume E exists to answer: *which* pool to choose, and why.
Threads share memory and are cheap but are serialized by the GIL for CPU-bound Python code, so they help mainly with I/O-bound work; processes sidestep the GIL and achieve true parallelism for CPU-bound work but pay to marshal data across their boundary.
That whole decision - the GIL, threads, processes, and when each actually speeds things up - is Deep Volume E's subject, which is precisely why the canonical table of contents places Deep E immediately after this volume.
What the timeline records is the interface-level advance: in 3.2, `concurrent.futures` gave concurrency one clean, uniform API, so that choosing and using a pool became a one-line decision rather than a bespoke engineering exercise.
The modern consequence, verified above, is that the Executor/Future model is the default high-level way to run parallel work in Python, and later async work (`asyncio`, Part IV) borrowed the very word "future" from it.

## Where this lands, and the close of Consolidation

`concurrent.futures` is the clearest single example of what "consolidation" meant for Python 3.1 and 3.2: taking capabilities that already existed in low-level form and giving them a clean, uniform, high-level interface.
Reach for `ThreadPoolExecutor` when your work waits on I/O, `ProcessPoolExecutor` when it burns CPU, `map` when you want ordered results, `submit` plus `as_completed` when you want to stream them - and let the pool handle the threads and processes you no longer create by hand.
Deep Volume E, next, is where you learn which of those pools will actually help and why; this chapter is the record of the release that made using either one easy.

This closes Volume 8, Consolidation.
The volume's two quiet releases, 3.1 and 3.2, added no schism-level changes; their through-line was making Python 3 *usable* - `lru_cache` for memoization, the format mini-language for text, `total_ordering` for comparable types, and `concurrent.futures` for parallel work, alongside the new GIL of Chapter 8.
Together they turned Python 3 from a language that had made a hard break into one that was pleasant to work in.
Part III now hands off to Deep Volume E, the concurrency mechanism that `concurrent.futures` presents an interface to, before Part IV follows generators to their conclusion in async.
