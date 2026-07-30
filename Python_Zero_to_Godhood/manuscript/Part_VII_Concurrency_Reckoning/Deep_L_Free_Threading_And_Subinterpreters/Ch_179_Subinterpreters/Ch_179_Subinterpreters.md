# Chapter 98: Subinterpreters: Isolation as the Primitive

Chapters 94 through 97 catalogued what it costs to let threads share every object: rebuilt refcounts, a stopping world, a lock per container, bytecode copied per thread. This chapter is the escape that refuses the premise. A **subinterpreter** (PEP 684, surfaced as `concurrent.interpreters` by PEP 734 in Python 3.14) is a complete Python world inside your process, own globals, own `sys.modules`, own specializer, and **own GIL**, sharing nothing by default. Nothing shared, nothing to coordinate: none of this volume's machinery is needed, because none of its races can be expressed.

The headline is that this works *on the build everyone already runs*. Four CPU-bound calls on the GIL build of 3.14.6: a thread pool ties sequential at 207.8 ms, and an **interpreter pool finishes in 56.0 ms, 3.8x**, matching a process pool without leaving the process. On the free-threaded build, threads join the party and the three parallel rows tie within noise.

The invoice is isolation's, and it is itemised below: **7.5 ms** to create an interpreter (250x a thread, a seventh of a process), and a marshalling cost per value crossed, 336 ns for a shareable `int`, cheaper than `queue.Queue`, but **7.9x** it for a pickled list. Subinterpreters do not remove the boundary between workers; they move it inside the process and make it explicit, which is exactly Chapter 84's kind of boundary, with Chapter 84's rule attached.

**This is a Deep L chapter.**
Chapter 23 owns the release story, how the per-interpreter GIL landed in 3.12 and the stdlib module in 3.14. This chapter owns the working model: what is isolated, what crosses and at what price, and when this primitive beats the other three.

## Section index

- **98.1** Isolation, demonstrated
- **98.2** The model: worlds, shareables, and copies
- **98.3** Measurement: scaling, startup, crossing
- **98.4** Edges and failure modes
- **98.5** Connections
- **98.6** Exercises
- **98.7** Summary and cross-references

Listings live under `code/ch179/` and are re-executed by `make verify` on 3.14 and 3.14t; the listing declares `# requires: 3.14+` and is skipped, not failed, on 3.13.

---

## 98.1 Isolation, demonstrated

```python
# code/ch179/l01_isolated_interpreters.py
```

Verified output (CPython 3.14.6):

```text
--- isolation: a namespace, a module system, an interpreter each ---
  child set FLAG='child'; main's FLAG is still : 'main'
  'dis' imported in main; imported in child too : False
  code runs in the child and answers over a queue : 42
  same process, separate worlds: globals, sys.modules, and the GIL
  are all per-interpreter (PEP 684)
--- what crosses without a copy: the shareable types ---
  is_shareable(int     ) : True
  is_shareable(str     ) : True
  is_shareable(bytes   ) : True
  is_shareable(tuple   ) : True
  is_shareable(NoneType) : True
  is_shareable(bool    ) : True
  is_shareable(list    ) : False
  is_shareable(dict    ) : False
  is_shareable(object  ) : False
  shareable values cross by value-identity, safely, lock-free;
  everything else is COPIED (pickled) across the boundary
--- crossing is copying, demonstrated ---
  a list makes the round trip equal   : True
  ...but it is a different object     : True
  no aliasing can exist across interpreters, so no data race can;
  isolation buys Chapter 99's whole problem away, at a copy per value
--- each interpreter has its own lock ---
  the child's own GIL is enabled : True
```

On the free-threaded build the output is identical except the last line, which is its own small lesson. Verified output (CPython 3.14t):

```text
  the child's own GIL is enabled : False
```

**The first block is three isolations in four lines.**
The child's `FLAG` does not touch main's; the child's `sys.modules` has not heard of a module main imported; and code sent with `Interpreter.exec` runs in the child's world, answering over a queue that `prepare_main` bound into the child's `__main__`. This is not process isolation, same address space, one OS process, but it is *semantic* isolation as complete as Python can state it.

**The shareable table is the boundary's type system.**
`int`, `str`, `bytes`, `bool`, `None`, and tuples of shareables cross without pickling, by value; `interpreters.Queue` itself is shareable, which is how channels are handed to children. Everything else that crosses is **copied**, and the round-trip block proves the copy: equal list, different object. There is no aliasing across the boundary, therefore there is no data race across it, therefore Chapter 99's entire subject is bought away, at a copy per value, which §98.3 prices.

**And the last line is the volume folding onto itself.**
Each interpreter has its own lock on the GIL build, and on the free-threaded build each interpreter has its own *absence* of one: the two escapes compose. Isolation is orthogonal to free-threading, and Chapter 100 treats them as two independent dials rather than rivals.

---

## 98.2 The model: worlds, shareables, and copies

**A subinterpreter is everything Chapter 93's table listed, duplicated.**
Own small-int cache and interned strings, own `sys.modules` (every import re-executes per interpreter, §98.4), own allocator arenas, own GC with its *generational* collector (Chapter 95's stop-the-world applies per interpreter, stopping only that interpreter's threads), own specializer state (Chapter 97's tables are per-world). The per-interpreter GIL, PEP 684's 3.12 achievement that Chapter 23 narrates, is what makes the duplication buy parallelism: two interpreters' bytecode runs on two cores because the lock each one respects is its own.

**The API is three verbs and a channel.**
`interpreters.create()` makes a world; `Interpreter.exec(code)` runs source in it (in the caller's thread, blocking, which is why parallel use pairs interpreters with threads or uses `InterpreterPoolExecutor`); `Interpreter.call(fn, *args)` pickles a callable across and runs it; `interpreters.create_queue()` yields a `Queue` whose ends can live in different worlds. `prepare_main(**bindings)` seeds a child's `__main__` with shareables, the idiomatic way to hand over channels.

**Shareability is a safety property, not a convenience tier.**
The shareable types are precisely the immutable primitives whose cross-interpreter aliasing cannot be observed: no mutation, no identity contract worth preserving, no refcount visible to the other side (the mechanism uses per-interpreter proxies rather than shared `PyObject`s, so no Chapter 94 machinery leaks across). A `list` cannot be shareable without importing this volume's entire problem, so it is copied instead, and `NotShareableError` marks the things that will not even pickle.

**The design consequence is Chapter 84's rule, verbatim.**
The boundary is safe and it is priced per crossing, so the winning shape is few crossings, large payloads, workers that own their data: send a filename or a 1 MB `bytes`, not fifty thousand small lists. §98.3c measures the slope, and Chapter 100 shows the same rule deciding between all four concurrency primitives.

---

## 98.3 Measurement: scaling, startup, crossing

**Methodology.** `code/ch179/bench_interpreter_scaling.py`.
The Chapter 93 workload (~50 ms of pure-Python CPU work per call), four ways, executors pre-warmed so rows price steady state; `min` of 5. Startup and crossing hand-timed, `min` of 10 and of 3x10,000. Within-build ratios only.
CPython 3.14.6, both builds; Apple M3 Pro, macOS 27.0, arm64.

**Scaling, GIL build.**

| 4 CPU-bound calls | time | vs sequential |
|---|---|---|
| sequential | 214.1 ms | 1.00x |
| thread pool | 207.8 ms | 1.03x |
| **interpreter pool** | **56.0 ms** | **3.8x** |
| process pool | 58.1 ms | 3.7x |

**Scaling, free-threaded build.**

| 4 CPU-bound calls | time | vs sequential |
|---|---|---|
| sequential | 187.9 ms | 1.00x |
| thread pool | 48.9 ms | 3.8x |
| interpreter pool | 48.9 ms | 3.8x |
| process pool | 50.0 ms | 3.8x |

The GIL table is the chapter's reason to exist: **CPU parallelism, in-process, on the default build**, matching processes without process costs. The free-threaded table shows the escapes converging when the GIL is gone; threads win on simplicity and shared memory, but nothing here punishes the isolated designs.

**Startup: bring up one worker, retire it.**

| worker | GIL build | free-threaded |
|---|---|---|
| thread, start+join | 0.03 ms | 0.31 ms |
| subinterpreter, create+close | 7.54 ms | 8.32 ms |
| process pool of one, up+down | 55.7 ms | 44.9 ms |

An interpreter is ~250 threads of startup and a seventh of a process, most of it re-importing the world (§98.4). The design answer is the same as for threads-on-3.14t (Chapter 97): **pool them**; the benchmark's own pre-warming is the pattern.

**Crossing: one value, put+get.**

| payload, per round trip | `interpreters.Queue` | `queue.Queue` | ratio |
|---|---|---|---|
| `int` (shareable) | 336 ns | 592 ns | **0.6x, cheaper** |
| 1 KB `bytes` (shareable) | 389 ns | 595 ns | 0.7x |
| 100-element list (pickled) | 4,836 ns | 610 ns | **7.9x** |

The shareable rows are the surprise worth keeping: the isolation queue beats the threading queue for primitives, because the shareable fast path is leaner than `queue.Queue`'s lock-and-condition machinery. The pickled row is the invoice: ~4 us per small list, and it scales with payload complexity. Batch per Chapter 84 and the invoice amortises; cross per element and it is your program.

**Book I**'s cousin is exactly this: the shared system's C++ side talks to Python over a boundary that ships packed buffers per batch (Chapters 79, 84), and a subinterpreter architecture is that same design expressed entirely in Python, worlds that own their data, meeting at explicit, priced crossings.

---

## 98.4 Edges and failure modes

**Every interpreter imports its own copy of everything.**
`import numpy` in eight interpreters is eight imports, eight module objects, eight sets of module-level state, in one process's memory; the 7.5 ms creation cost grows with what the child must import to be useful. Interpreters are cheap worlds, not free ones; pool them and keep them warm.

**Extensions must opt in.**
A C extension is loaded per interpreter, and only modules implementing multi-phase init (PEP 489) with per-interpreter state (or explicitly supporting the per-interpreter GIL) can load in a subinterpreter at all; legacy single-phase modules raise `ImportError`. The ecosystem's coverage is the practical gate, exactly parallel to the `cp314t` wheel story (Chapter 93), and the two compatibility campaigns are converging on the same fix: modules without process-global mutable state.

**`exec` runs in the calling thread.**
`Interpreter.exec` blocks its caller; parallelism requires a thread per busy interpreter (`call_in_thread`, or the executor, which manages this). A subinterpreter is a *world*, not a *worker*; the worker is still a thread standing in that world.

**Exceptions cross as reports, not objects.**
An uncaught exception in the child surfaces as `ExecutionFailed` carrying a rendered traceback; the original exception object, like every other object, does not cross. Error-handling designs that match on exception types must marshal their own error values over the queue.

**Isolation is semantic, not physical.**
One process means one address space, one RSS limit, one `ulimit`, and one fatal crash: a segfaulting extension in any interpreter kills them all, where a process pool loses one worker. Choose interpreters over processes for cheap creation and fast shareable channels; choose processes when fault isolation or memory caps are the requirement (Chapter 100's table).

**The GIL build's old blind spot still applies inside each world.**
Within one interpreter, threads behave exactly as Deep E described on that build. Subinterpreters change the *between*, never the *within*; a program can and often should use both dials at once.

**And the API is young.**
`concurrent.interpreters` is new in 3.14; expect the shareable set, `call`'s pickling rules, and the executor's ergonomics to grow. The isolation model and the per-interpreter GIL beneath it (3.12) are the stable parts; re-run this chapter's benchmark before relying on a specific constant.

---

## 98.5 Connections

**Backward.**
The release history, PEP 684 in 3.12 and PEP 734 in 3.14, is Chapter 23. The machinery this chapter's isolation avoids is Chapters 94 to 97. The boundary-design rule it inherits, cross per batch with big payloads, is Chapter 84; the pickling that unshareable values ride is Deep O's serialization chapters. `queue.Queue`, the within-world baseline, is Chapter 49.

**Forward.**
Chapter 99 is the correctness chapter for the sharing designs this chapter lets you refuse; its opening move is "first ask whether Chapter 98 makes the problem vanish". Chapter 100 closes the volume with the four-way decision, threads, subinterpreters, processes, `asyncio`, using this chapter's three tables as the isolation column.

**Across books.**
Share-nothing workers meeting at explicit channels is the actor model, Erlang's bet, Go's "share memory by communicating", and **Book I**'s process-pinned shards. The C++ side of the shared system has always been a set of isolated worlds passing messages, because that is what survives at scale; subinterpreters are Python acquiring that architecture natively, one process wide, with the type system of the boundary (`is_shareable`) enforced by the runtime instead of by review.

---

## 98.6 Exercises

**1. Reproduce the tables.** Run the benchmark on both builds. Add an 8-way row on your machine and report where interpreter scaling bends relative to your core count.

**2. Price the world.** Measure interpreter creation with the child importing nothing, `json`, and `decimal`+`sqlite3`. Plot creation cost against import weight, and state the pool-size and reuse policy that makes it irrelevant for a server handling 1,000 tasks.

**3. Batch the boundary.** Send 100,000 dicts across an `interpreters.Queue` one at a time, then as 100 pickled batches of 1,000, then as one `bytes` blob the child parses. Reconcile the three timings with §98.3c and Chapter 84's model.

**4. Break an import.** Find or write a single-phase C extension and show the `ImportError` in a subinterpreter. Then show the same module importing cleanly in a process pool, and write the two-line deployment note explaining the choice it forces.

**5. Compose the dials.** On the free-threaded build, run 2 interpreters x 2 threads each against 4 threads and 4 interpreters, on a workload that is half shared-read (Chapter 96's hoisted dict) and half private compute. Report which composition wins and why.

**6. The design question.** The shareable set excludes `list`, `dict`, and user objects, though a frozen, deeply-immutable structure could in principle cross safely. Argue the restriction: what "deeply immutable" would require the runtime to *verify* (Chapter 94's header has no such bit), why a proxy-based `Queue` for mutables would reimport every race this chapter deletes, and what the eventual middle ground looks like (immutable buffers already cross: `bytes` and `memoryview`). Then design the API you would want for sharing a 10 GB read-only table across 8 interpreters without 8 copies, and check your design against `memoryview`'s existing semantics (Chapter 79).

---

## 98.7 Summary and cross-references

- **A subinterpreter is a full Python world in-process**, own globals, modules, allocator, collector, specializer, and own GIL (PEP 684); `concurrent.interpreters` (PEP 734, 3.14) is the API: `create`, `exec`, `call`, queues, `prepare_main`.
- **Measured on the GIL build: 3.8x CPU scaling in-process**, 56.0 ms against threads' 207.8 for the same four calls, matching a process pool. On 3.14t the thread, interpreter, and process rows tie at ~3.8x: the two escapes compose rather than compete.
- **Isolation's invoice**: 7.5 ms to create a world (pool them), and marshalling per crossing, 336 ns for a shareable `int` (cheaper than `queue.Queue`), **7.9x** for a pickled list. Shareables are the immutable primitives; everything else crosses as a copy, so no race can cross at all.
- **Edges**: every world re-imports everything; extensions need multi-phase init; `exec` blocks its calling thread; exceptions cross as reports; one crash kills all worlds (processes still own fault isolation); and the within-world rules are unchanged.
- **The design rule is Chapter 84's**: few crossings, big payloads, workers that own their data, now available without leaving the process.

**Cross-references.** Release story → Chapter 23. The machinery isolation avoids → Chapters 94-97. Boundary economics → Chapter 84. Buffers → Chapter 79. `queue.Queue` → Chapter 49. Serialization → Deep O. Correctness under sharing → Chapter 99. The four-way decision → Chapter 100.
