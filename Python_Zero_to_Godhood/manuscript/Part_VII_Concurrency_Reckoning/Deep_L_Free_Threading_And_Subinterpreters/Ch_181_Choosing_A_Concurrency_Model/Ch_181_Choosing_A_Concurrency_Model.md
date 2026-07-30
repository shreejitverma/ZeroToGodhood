# Chapter 100: Choosing a Concurrency Model

Deep L opened with two escapes from one lock; it closes with the decision between four primitives, made the way this book closes every volume: from measurements, with the procedure written down.

The capstone measurement is one table generated live: the same ~200 ms of CPU work, split into 4, then 40, then 4,000 tasks, through a thread pool, an interpreter pool, and a process pool, on both builds. At coarse grain, **every primitive that can scale on its build ties at ~61 to 69 ms**, and the choice barely matters. At fine grain the boundaries submit their invoices in the exact order Chapter 98 priced them: threads on the free-threaded build do not care (**60 ms at every grain**), subinterpreters on the GIL build charge ~7 us per task, processes ~47 us, and at 4,000 tasks the process pool is slower than not parallelising at all.

So the closing lesson of the volume has three clauses. **The build decides which primitives can scale; the boundary decides what each task costs; and the grain, which is yours to choose, decides whether the scaling survives the boundary.**

**This is a Deep L chapter, and it closes Deep L.**
Chapters 93 to 99 measured the machinery; this chapter is the machinery compressed into a choice. Deep E owns the primitives' APIs; Deep H owns `asyncio`, which interleaves waiting rather than computing and is therefore this chapter's complement, not its competitor.

## Section index

- **100.1** The decision, as a model
- **100.2** The four primitives, one property at a time
- **100.3** Measurement: grain against boundary
- **100.4** Edges and failure modes
- **100.5** Connections, and the volume closed
- **100.6** Exercises
- **100.7** Summary and cross-references

Listings live under `code/ch181/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 100.1 The decision, as a model

```python
# code/ch181/l01_choosing_the_model.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- the four primitives, as measured properties ---
  primitive            CPU scaling           boundary      race burden     fault isolation
  threads (GIL build)  none for CPU (Ch 93)  queue hop     full (Ch 99)    none
  threads (3.14t)      cores (3.7x, Ch 93)   queue hop     full (Ch 99)    none
  subinterpreters      cores (3.8x, Ch 98)   marshal/copy  none: isolated  none
  processes            cores (3.7x, Ch 98)   pickle + IPC  none: isolated  full
  asyncio is deliberately absent: it interleaves WAITING, not
  computing (Deep H), and composes with any row for the I/O half
--- amortisation: boundary price to minimum task size ---
  rule: for >= 95% efficiency, task work must exceed ~20x the
  per-task boundary price (measured per grain in bench 181.1)
```

**The properties table is the volume with the argument removed.**
Each cell is a chapter: the GIL-thread row's "none" is Chapter 93's 1.06x; the 3.14t row's "cores" is its 3.69x; the isolation rows' empty race-burden column is Chapter 98's copied boundary; the process row's "full" fault isolation is the one property nothing in-process can offer. Reading down a column is comparing primitives; reading across a row is pricing one; and no row dominates, which is why this is a decision and not a default.

**The amortisation block is the only new mathematics in the chapter.**
A boundary priced at `c` per task caps efficiency at `work / (work + c)`; demanding 95% gives `work >= 19c ~ 20c`. With Chapter 98's and this chapter's measured constants, that yields concrete minimums: any task fits a thread hand-off; tasks under ~0.14 ms should not cross an interpreter boundary singly; tasks under ~1 ms should not cross a process boundary singly. "Singly" is the operative word, because batching moves `work` up at fixed `c`, which is Chapter 84's rule promoted to architecture and §100.3's fine-grain column demonstrated in reverse.

**And the procedure block is the volume's deliverable**, five questions asked in order: waiting or computing; partitionable; must it share; must it survive crashes; and only then, what grain. The chapters back every branch, and the closing recap prints Deep L in eight lines because a volume that measured a price list should end by handing it over.

---

## 100.2 The four primitives, one property at a time

**Threads are the cheapest boundary and the heaviest discipline.**
A task hand-off is a queue hop (sub-microsecond); memory is shared, so nothing is copied, and everything in Chapters 94 to 97 is in force: refcount ownership, container locks, per-thread bytecode, and Chapter 99's full race burden. On the GIL build they parallelise only waiting; on 3.14t they parallelise everything and become the default *fast* answer wherever the discipline is affordable.

**Subinterpreters are the middle price on both axes.**
In-process, so creation is 7.5 ms and shareable crossings are hundreds of nanoseconds (Chapter 98); isolated, so the race burden is zero by construction; but every non-primitive crossing is a copy, every world re-imports its modules, and a crash still kills the process. They are the GIL build's only in-process route to the cores, which makes them the deployment bridge for the years the `t` ecosystem needs to finish arriving.

**Processes are the only fault domain.**
Everything the interpreter pool charges, plus pickling both ways and real IPC, ~47 us a task here, plus ~55 ms a worker to start. In exchange: separate address spaces, separate RSS, separate deaths, `kill -9` as a management tool, and immunity to every in-process failure mode this volume measured, including a segfaulting extension. Choose them when the requirement is survival, not speed.

**And `asyncio` is the row that is not a row.**
It multiplexes waiting on one thread; its "boundary" is an `await` and its scaling axis is concurrent I/O, not cores (Deep H). The composition rule is mechanical: an async front absorbs the waiting, and CPU work is shipped to one of the three real rows via an executor, sized by this chapter's table.

---

## 100.3 Measurement: grain against boundary

**Methodology.** `code/ch181/bench_granularity.py`.
A fixed budget of pure-Python CPU work (~200 ms, per-iteration cost held constant across grains by masking the operands) split into 4, 40, and 4,000 tasks; pools pre-warmed with 4 workers; `min` of 3. Within-build comparisons only; the two builds' tables are printed separately.
CPython 3.14.6, both builds; Apple M3 Pro, macOS 27.0, arm64.

**The GIL build.**

| executor | 4 tasks | 40 tasks | 4,000 tasks |
|---|---|---|---|
| sequential | 238 ms | 240 ms | 207 ms |
| thread pool | 243 ms | 242 ms | 222 ms |
| interpreter pool | **67 ms** | **68 ms** | 94 ms |
| process pool | 69 ms | 69 ms | **258 ms** |

**The free-threaded build.**

| executor | 4 tasks | 40 tasks | 4,000 tasks |
|---|---|---|---|
| sequential | 234 ms | 242 ms | 209 ms |
| thread pool | **61 ms** | **62 ms** | **60 ms** |
| interpreter pool | 64 ms | 68 ms | 596 ms |
| process pool | 65 ms | 63 ms | 161 ms |

**Read the coarse column first: at 50 ms a task, the choice barely matters.**
Every primitive that can scale on its build lands within noise of ~65 ms, and the sequential rows calibrate (the ~13% drift across their own columns is call-structure overhead, reported rather than hidden). Architecture arguments at coarse grain are arguments about the *other* columns of §100.1's table, isolation, fault domains, discipline, because the speed column has gone flat.

**Read the fine column second: the boundaries submit their invoices.**
Per-task overheads derived from the 4,000-task column against the 4-task column: interpreter pool on the GIL build, ~7 us a task, still 2.2x faster than sequential; process pool, ~47 us a task, now 25% *slower* than sequential; and the thread pool on 3.14t, no measurable change at all, 60 ms at every grain, the queue hop vanishing into the noise. Fine-grained work survives only the cheapest boundary, exactly as the amortisation arithmetic predicts.

**And one measured surprise, reported with its hypothesis flagged.**
The interpreter pool's fine-grain column is *much* worse on the free-threaded build (596 ms, ~133 us a task) than on the GIL build (94 ms), while the process pool improves (161 against 258). The plausible mechanism is Chapter 96's: the young executor's shared dispatch machinery, queues, futures, wakeups, contends across truly-parallel threads on 3.14t where the GIL build serialised it for free. The number is real either way, the API is new, and this row is the one most likely to move by 3.15; re-run before relying on it.

**Book I**'s capstone table is this one with the same shape and smaller constants: its thread hand-off is nanoseconds, its process boundary is the same ~50 us, and its architecture rule is word-for-word the conclusion above, coarse grain first, then pick by isolation needs, then batch until the boundary amortises. The shared system's final form uses every row: C++ threads in the engine, Python 3.14t threads in analytics, subinterpreters for plugin isolation, and processes where a crash must not take the book down.

---

## 100.4 Edges and failure modes

**The table was measured with pre-warmed pools, and yours might not be.**
Add Chapter 98's startup invoice for short-lived programs: 55 ms a process worker or 7.5 ms an interpreter dwarfs a 200 ms job's savings. Pools first, always; a CLI that forks a pool for one second of work has chosen the table's worst cell.

**Grain is a distribution, not a number.**
A mean task of 5 ms with a p99 of 500 ms stalls a 4-worker pool behind its own tail. The amortisation rule sizes the *smallest common* task; heavy tails want work stealing (smaller batches to idle workers) or a two-tier split, and the diagnosis is worker-utilisation timelines, not this chapter's totals.

**Mixed workloads decompose; they do not average.**
"Half I/O, half CPU" is not a fifth row: it is `asyncio` (or GIL threads) absorbing the waiting, feeding a CPU primitive sized by this table. Choosing one primitive for both halves yields either idle cores or a starved event loop, and the composition is three lines of executor code.

**The isolation rows still share a fate on one axis each.**
Subinterpreters share a process: one segfault, one OOM kill, everything gone (Chapter 98). Processes share a machine: memory pressure, CPU quotas, and the file system remain common-mode. The fault column of §100.1 is about *software* failure domains; capacity planning is a different chapter of a different book.

**Data gravity beats compute placement.**
A 10 GB read-only table pulls the design toward whatever can reach it without copying: 3.14t threads (shared memory, hoisted references, Chapter 96), or processes with OS-level shared memory / `mmap` (Deep E, Chapter 79). Shipping the table through any pickled boundary converts the fine-grain column's microseconds into seconds; this is Chapter 89's "choose the representation from the consumer" at cluster scale.

**And every constant here has a shelf life.**
This chapter is built on a 2026 snapshot: 3.14t's overhead percentages, a brand-new interpreters executor, no JIT on the t-build. The *procedure*, the properties table, and the amortisation arithmetic are the durable parts; the constants are `make bench CH=ch181` away from re-derivation, which is exactly how Deep K said to hold them.

---

## 100.5 Connections, and the volume closed

**Backward, through the volume this chapter closes.**
The two escapes and the headline scaling, Chapter 93. The ownership price list that made "allocate where you use" a rule, Chapter 94. The collector whose pauses multiply by threads stopped, Chapter 95. Container locks, the contention cliff, and the hoist, Chapter 96. Thread-local bytecode and the itemised single-thread bill, Chapter 97. Isolation and its invoice, Chapter 98. The race lab and the discipline, Chapter 99. This chapter spent all of it.

**Beyond the volume.**
The primitives' APIs and the I/O story are Deep E and Deep H. The boundary economics this chapter kept citing are Chapter 84 (Deep M); the representation arguments under "data gravity" are Chapters 79 and 89 (Deep K). The release history that made any of this possible, 3.12's per-interpreter GIL, 3.13's experiment, 3.14's support, is Chapters 23, 26, and 27, whose cited figures this volume has now measured (the verification queue's row on free-threaded overhead is closed).

**Across books, one last time.**
Book I never had a GIL to lose, and its concurrency chapters open where this one ends: with ownership, boundaries, and grain as the design inputs. That the two books now end their concurrency volumes with the same three-clause lesson, build decides scaling, boundary decides cost, grain decides survival, is the series' thesis demonstrated: the constants belong to the language; the engineering belongs to both.

---

## 100.6 Exercises

**1. Regenerate the capstone.** Run the granularity benchmark on your machine and matrix. Derive your own per-task boundary prices from the fine-grain column and update §100.1's amortisation minimums for your hardware.

**2. Find the knee.** For the interpreter pool on the GIL build, bisect between 40 and 4,000 tasks for the grain at which efficiency crosses 95%, and check it against the ~20x rule's prediction from your measured per-task price.

**3. Compose a mixed workload.** Build a workload of 100 downloads (50 ms latency each, faked with `sleep`) each followed by 50 ms of CPU parsing. Implement it three ways: threads only, `asyncio` only, `asyncio` front + the best CPU primitive for your build. Measure wall time and explain the ranking with §100.1's table.

**4. Chase the surprise.** Profile the free-threaded interpreter pool's fine-grain collapse (596 ms): instrument the executor's internal queue with timestamps, attribute the ~133 us, and test the Chapter 96 hypothesis by replacing the shared future-wakeup path with a per-worker queue. Report what you find; this row is young enough that your result may be a bug report.

**5. Write the deployment note.** For a real service you know, answer §100.1's five questions in order, name the primitive and grain the answers select, and state the one measurement that would change the decision. One page, numbers cited.

**6. The design question.** `concurrent.futures` presents threads, processes, and now interpreters behind one `Executor` interface, which this chapter's tables show differ by orders of magnitude in boundary price. Argue both sides of that uniformity: what the shared interface buys (this chapter's benchmark is 30 lines because of it; migration between rows is a one-line change) against what it hides (a `map` over 4,000 small tasks is free on one executor and catastrophic on another, with no type-level warning). Then propose the smallest API addition that would surface the boundary price to callers, and defend it against "just read Chapter 100".

---

## 100.7 Summary and cross-references

- **The three-clause lesson**: the build decides which primitives scale (GIL threads cannot; everything else can); the boundary decides the per-task price (queue hop, then marshalling, then pickle+IPC); the grain decides whether scaling survives the price.
- **Measured**: at 4x~50 ms tasks all scaling primitives tie (~61-69 ms); at 4,000x~50 us tasks, 3.14t threads are unmoved (**60 ms at every grain**), the GIL-build interpreter pool pays ~7 us/task (94 ms, still winning), and the process pool pays ~47 us/task (258 ms, **slower than sequential**). One flagged surprise: the interpreter executor's fine-grain cost is much higher on 3.14t (~133 us/task), plausibly Chapter 96 contention in young executor machinery.
- **The amortisation rule**: 95% efficiency needs task work >= ~20x the boundary price, ~0.14 ms for an interpreter crossing, ~1 ms for a process crossing, anything for a thread hop, and batching buys any primitive back.
- **The procedure**: waiting → `asyncio`/threads; partitionable CPU → cheapest scaling primitive (3.14t threads, else subinterpreters, else processes); genuine mutable sharing → 3.14t threads under Chapter 99's discipline; fault isolation → processes; then set the grain.
- **Deep L, closed**: one lock became a price list, refcount ownership, world-stopping pauses, container locks, thread-local bytecode, isolation invoices, measured race rates, and this chapter is the list handed back as a decision. The constants will age; re-derive them; the procedure is the part to keep.

**Cross-references.** The escapes and scaling → Chapter 93. Ownership → Chapter 94. The collector → Chapter 95. Container locks → Chapter 96. Thread-local bytecode → Chapter 97. Isolation → Chapter 98. Correctness → Chapter 99. Boundary economics → Chapter 84. Buffers and representation → Chapters 79, 89. `asyncio` → Deep H. The release story → Chapters 23, 26, 27.
