# Chapter 73: Async Generators

The iterator protocol of Chapter 69 has an asynchronous twin. An **async generator** is `async def` plus
`yield`: it can `await` between items, waiting on network, disk, or a queue, and is consumed with `async for`.
Its purpose is the asyncio one (Chapters 10-11): while one stream awaits I/O, others make progress, so many
async sources are consumed *concurrently* on a single thread. But that power has a price, and the price is the
chapter's caution. For a source with *no* real awaiting, iterating an async generator costs **3.1x** a sync
generator per item (83 ns versus 27 ns), because each item is driven through `__anext__` and the coroutine/
event-loop machinery instead of a direct frame resume. Async generators are for *genuinely async* sources,
where the per-item overhead is dwarfed by the I/O wait; using one to iterate in-memory data is paying 3x for
nothing.

This chapter continues **Deep F** with async generators: the `async def`/`yield`/`async for` mechanism, the
concurrent interleaving that justifies them, and the measured overhead that bounds where they belong. It
extends the iterator protocol (Chapter 69) and the coroutine ideas (Chapter 70) into the async world of
Chapters 10-11.

## Section index

- **73.1** `async def` + `yield`, consumed by `async for`
- **73.2** Interleaving vs overhead
- **73.3** Measurement: the per-item cost
- **73.4** Edges and failure modes
- **73.5** Connections
- **73.6** Exercises
- **73.7** Summary and cross-references

Listings live under `code/ch073/` and are re-executed by `make verify` on both interpreters.

---

## 73.1 `async def` + `yield`, consumed by `async for`

```python
# code/ch073/l01_async_gen.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- async comprehension collects an async generator ---
  [x async for x in stream(...)] : ['page0', 'page1', 'page2']
--- async for streams items one at a time ---
  streamed : row0
  streamed : row1
--- two async streams interleave (concurrent on one thread) ---
  interleaved order : ['A0', 'B0', 'A1', 'B1', 'A2', 'B2']
  (A and B alternate: each yields control at every await)
```

An **async generator** is a function that is both `async def` and contains `yield`. It can `await` between
yields (the `stream` coroutine awaits `asyncio.sleep(0)`, standing in for awaiting real I/O), which a plain
generator cannot. You consume it with **`async for`** (which drives its `__anext__`, an *awaitable*) or an
**async comprehension** (`[x async for x in ...]`), both usable only inside an `async def`.

The third block is the reason async generators exist. Two `stream` async generators, drained concurrently with
`asyncio.gather`, **interleave**: the order is `A0, B0, A1, B1, A2, B2`, the two streams alternate, because each
yields control at its `await`, letting the other advance. On one thread, without the GIL contention of threads
(Chapter 8) or the copying of processes (Chapter 48), many async streams make progress together, exactly the
asyncio concurrency model, now producing values via `async for`. This interleaving is what a sync generator
cannot do: a sync `for` over one generator runs it to completion before the next.

---

## 73.2 Interleaving vs overhead

The interleaving is the benefit; the machinery to enable it is the cost. Every step of an `async for` is not a
direct frame resume (as in a sync generator, Chapter 69) but an *awaitable*: `__anext__` returns a coroutine
that the event loop schedules and steps. That indirection, through the coroutine object and the loop, is what
lets other tasks run at each `await`, and it is also pure overhead when there is nothing to await.

So the two properties trade against each other by *workload*. When items arrive from a *real async source*, each
`await` actually suspends for I/O (milliseconds of network or disk), and during that suspension other streams
run; the per-item machinery overhead (tens of nanoseconds) is invisible against the I/O wait, and the
interleaving delivers real concurrency, the win Chapter 10 measured at hundreds of x for I/O-bound work. When
items come from an *in-memory* source (a list, a range, a computation), there is nothing to await, so the
`await` overhead is *all* you pay, 3x per item (§73.3), for interleaving that buys nothing because no item ever
blocks.

The rule: **use an async generator only when the source is genuinely async, awaiting I/O between items; use a
plain generator for in-memory data.** An `async for` over a list is a code smell (a sync `for` is 3x cheaper and
simpler). Async generators shine for streaming from a socket, reading a large file in awaited chunks, consuming
an async queue, or merging several such streams, precisely where the interleaving of §73.1 turns waiting into
concurrency. Match the tool to whether the iteration actually *waits*.

---

## 73.3 Measurement: the per-item cost

**Methodology.** `code/ch073/bench_async_overhead.py`. Consuming a 100,000-item sequence from an async generator
(`async for`, run in an event loop) versus a sync generator (`for`), with *no* real awaiting in either. `min`
per run. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| iterate 100,000 items (no I/O) | per item | ratio |
|---|---|---|
| sync generator | **27 ns** | 1.00x |
| async generator | **83 ns** | **3.1x** |

With no awaiting, the async generator costs **3.1x** per item, 83 ns versus 27 ns. The extra is the coroutine/
event-loop machinery: each item's `__anext__` produces an awaitable that the loop steps, where the sync
generator just resumes its frame. This is the *floor* cost of the async protocol, paid on every item regardless
of whether it awaits anything.

The rule the measurement enforces: **the async overhead is only worth paying when items genuinely await.** For a
real async source, each item's I/O wait is milliseconds; 56 ns of extra machinery per item is nothing, and the
interleaving is everything. For an in-memory source, there is no wait to overlap, so the 3.1x is pure loss, use
a sync generator. The decision is not "async is modern, prefer it" but "does this iteration *wait*?", if yes,
async generator (and reap the concurrency); if no, sync generator (and skip the overhead). This is the same
"async is for I/O-bound, not CPU-bound" lesson as Chapter 8 and Chapter 10, at the iteration level.

---

## 73.4 Edges and failure modes

**`async for` over in-memory data.** §73.3. 3x the cost for interleaving that buys nothing (no item blocks). Use
a plain generator for in-memory sequences.

**Async generators need `async` cleanup.** An async generator holding a resource must be closed with `aclose()`
(awaited), and its `finally` runs asynchronously. `async for` does not auto-close it; use `contextlib.aclosing`
(3.10+) to guarantee `aclose`, or the generator may leak until GC, which for async generators involves the loop
finalizing them (a source of "async generator ignored GeneratorExit" warnings).

**Mixing `await` and `yield` incorrectly.** An async generator can `await` and `yield` but cannot `return` a
value (unlike a coroutine); `return` in an async generator just ends it. And you cannot use `yield` in a plain
`async def` coroutine that you `await`, `yield` makes it an async *generator*, consumed with `async for`, not
`await`.

**Blocking calls inside an async generator.** A synchronous blocking call (a non-awaited network read, a heavy
CPU loop) inside an async generator blocks the whole event loop, stalling every other stream. Keep async
generators non-blocking; offload blocking work (Chapter 10's `run_in_executor`).

**Consuming an async generator outside a loop.** `async for` and `aclose` only work inside a running event loop
(`async def`). You cannot iterate an async generator with a plain `for`; it has `__anext__`, not `__next__`.

**Backpressure and unbounded buffering.** An async generator that produces faster than the consumer awaits can,
if buffered, grow memory. Async generators are pull-based (the consumer drives `__anext__`), which gives natural
backpressure, but a queue between producer and consumer can defeat it. Design the flow so the consumer's pace
bounds the producer.

---

## 73.5 Connections

**Backward.** The sync iterator protocol (`__iter__`/`__next__`) this parallels is Chapter 69; the coroutine
`await` it builds on is Chapters 10-11. The generator producer/coroutine mechanics are Chapters 69-70. The GIL/
threads/processes concurrency alternatives are Chapters 8 and 48.

**Forward.** The event loop that schedules the `__anext__` awaitables, and structured concurrency over async
streams, are Chapters 10-11 and **Deep H** (asyncio in depth). `contextlib.aclosing` and async context managers
are the async cleanup story. Async streaming pipelines are a **Deep U** pattern.

**Across books.** Async generators are how Book II streams from async sources into **Book III** concurrently. A
**Book III** retrieval or serving path that reads from several async backends (a vector store, an embedding
service, a token stream from a model) consumes each as an async generator and interleaves them with `gather`, so
the slow awaits overlap and total latency is the max, not the sum, exactly Chapter 10's asyncio win, now
composed as streams. The §73.3 overhead is why the *in-memory* stages of that pipeline stay sync generators
(Chapter 72) while only the *I/O* stages go async. **Deep U** owns the async-streaming seam; **Deep H** owns the
loop.

---

## 73.6 Exercises

**1. Stream and interleave.** Write an async generator that awaits between items, consume it with `async for`,
and run two of them concurrently with `gather` to observe interleaving. Explain why they alternate and a sync
generator cannot.

**2. Measure the overhead.** Run §73.3's benchmark and confirm the async generator is several times slower per
item with no awaiting. Explain the `__anext__`/event-loop machinery cost and why it is invisible for a real
async source.

**3. Close it properly.** Write an async generator that holds a resource in `try/finally`, and use
`contextlib.aclosing` to guarantee `aclose`. Show the cleanup runs. Explain why `async for` alone does not close
it.

**4. Choose sync or async.** For several sources (a list, a socket read loop, a computation, an async queue),
decide async generator or plain generator and justify each by whether the iteration awaits. Explain the rule.

**5. The design question.** Async generators add per-item overhead to enable interleaving. Argue when that trade
is worth it. Your answer must use the §73.3 measurement, explain the "does it await?" test, and connect it to the
async-is-for-I/O-bound lesson of Chapters 8 and 10.

---

## 73.7 Summary and cross-references

- An **async generator** (`async def` + `yield`) can **`await` between items** and is consumed with **`async
  for`** or an **async comprehension**. Multiple async generators **interleave** (concurrent on one thread), the
  asyncio benefit.
- **Measured:** with no real awaiting, an async generator costs **3.1x** a sync generator per item (83 ns vs 27
  ns), the coroutine/event-loop machinery. This overhead is the floor of the async protocol.
- **Use an async generator only when the source genuinely awaits I/O** (socket, disk, queue), where the overhead
  is dwarfed by the wait and the interleaving is the point; **use a plain generator for in-memory data.**
- **Edges:** close with `aclose`/`aclosing`; never block the loop inside one; consume only inside a running loop;
  design for backpressure.

**Cross-references.** Sync iterator protocol → Chapter 69; coroutines → Chapters 69-70. `await`/event loop →
Chapters 10-11; asyncio in depth → Deep H. Sync generators for in-memory data → Chapter 72. Concurrency
alternatives → Chapters 8, 48. The async-streaming seam → Deep U.
