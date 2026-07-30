# Chapter 96: Per-Object Locks and Container Atomicity

Chapter 93 promised that `list.append` from four threads stays exact on the free-threaded build, and Chapter 94's header showed where the machinery lives: a mutex in every object. This chapter is about what that mutex does, what it preserves, and what it costs, and it ends at the sharpest measurement in the volume so far.

The preserved part is the contract: every single-operation count in this chapter's listing is exact, on every build, with no user locks. The cost part has a shape nobody should guess at: **private mutation scales** (3.5x on four threads, the lock never contended), **shared mutation is worse than not threading at all** (one shared list took 107 ms of four threads' time where one thread does all the work in under 70), and **shared reads scale**, 2.8x, because lookups take no lock whatsoever.

And then the exhibit: the same shared-dict read loop, twice, differing only in whether the dict is hoisted into a local before the loop. Hoisted: 47 ms. Read through the shared name each pass: **355 ms, a 7.5x collapse**, with no lock taken in either version. On the GIL build the same pair differs by 1.06x. The mechanism is Chapter 94's, the fix is Chapter 75's, and the lesson is this volume's thesis in one line: on the free-threaded build, **how often you touch a shared object's reference count is a first-class cost**.

**This is a Deep L chapter.**
Deep Q owns what the containers are made of; Chapter 88 owns choosing between them; Deep E owns user-level locking discipline. This chapter owns the containers' own locks: the atomicity they preserve and the contention they price.

## Section index

- **96.1** The contract, counted
- **96.2** The machinery: one mutex per object, critical sections, lock-free reads
- **96.3** Measurement: sharing shapes, and the hoist that decides scaling
- **96.4** Edges and failure modes
- **96.5** Connections
- **96.6** Exercises
- **96.7** Summary and cross-references

Listings live under `code/ch177/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 96.1 The contract, counted

```python
# code/ch177/l01_container_atomicity.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- single operations, four threads, no user locks ---
  list.append x 400,000          -> len 400,000
  dict[key] = v, disjoint keys -> len 400,000
  set.add, disjoint values     -> len 400,000
  deque.append x 400,000         -> len 400,000
  every count exact, on every build: one operation, one container,
  atomic - by the GIL there, by the container's own lock here
--- compound operations: the promise that never existed ---
  d[k] += 1 under a Lock       -> 400,000
  read-modify-write spans two operations; the container's lock covers
  each, never the pair. the loss rate without the Lock is a
  probability, not a fact, and Chapter 99 measures it
--- the iteration contract is unchanged ---
  mutate while iterating -> RuntimeError: dictionary changed size during iteration
```

**The first block is the compatibility PEP 703 paid for, verified across the matrix.**
Four containers, four threads, four hundred thousand operations each, every count exact, and the output byte-identical on all three interpreters. This is not a small promise: it means the enormous corpus of existing threaded Python that leans, knowingly or not, on "one operation is atomic" ports to the free-threaded build without corrupting its data structures.

**The second block is the boundary of the promise, drawn exactly where Deep E drew it.**
`d[k] += 1` is a read, an add, and a write; the container's lock covers each operation, never the sequence. The listing shows the *locked* version's exact count and refuses to print an unlocked one, because an unlocked loss rate is a probability, not a reproducible fact; Chapter 99 measures it as the distribution it is.

**And the third block is the language contract surviving the mechanism swap.**
Mutating a dict mid-iteration raises the same `RuntimeError` with the same message on every build. The per-object lock changed who enforces the rule, not the rule, which is this chapter's pattern in miniature: semantics preserved, enforcement rebuilt, price relocated.

---

## 96.2 The machinery: one mutex per object, critical sections, lock-free reads

**Every mutable object carries a `PyMutex`,** the one-byte lock in Chapter 94's header. A mutating operation, `append`, `__setitem__`, `add`, acquires the container's own lock for the duration of the operation. Uncontended, that is an atomic compare-and-swap on a byte already in cache, which is why §96.3's private-mutation row scales at 3.5x: four uncontended locks in four caches never meet.

**Critical sections, not bare mutexes, so the world can still stop.**
Chapter 95's collector must halt every thread. A thread parked hard on a container mutex cannot answer, so the C-API wraps these acquisitions in *critical sections* (`Py_BEGIN_CRITICAL_SECTION`) that can be **suspended at safe points**, the thread releases the object lock, lets the collector run, and reacquires before resuming. Operations on two containers at once (`list.extend(other_list)`, comparison, copy) acquire both locks through the same machinery in a canonical order, which is textbook deadlock avoidance (Chapter 53) implemented where the user cannot forget it.

**Reads take no lock at all.**
`d[k]` and `lst[i]` use **optimistic lock-free reads**: read the container's internal state, fetch the item, take a reference safely (a conditional incref that can fail if the item is being freed), then re-check that the container did not change underneath; retry on conflict. Freed backing arrays are reclaimed only after every thread passes a quiescent state (QSBR, Chapter 95), so a reader can never chase a dangling pointer. This is why the read row scales while every mutation row serialises: readers of a stable dict touch **no shared mutable word at all**, in the ideal case.

**The ideal case has one condition, and §96.3b measures what it is worth.**
"No shared mutable word" must include the reference counts the loop touches (Chapter 94). A loop that re-loads the container through a shared name on every pass increfs the *container* per iteration, from every thread, and that atomic traffic on one cache line is the whole difference between scaling and collapse. The container's lock is innocent; the loop's name resolution is guilty.

---

## 96.3 Measurement: sharing shapes, and the hoist that decides scaling

**Methodology.** `code/ch177/bench_container_contention.py`.
Four threads, one million operations per thread; self-timed with `perf_counter`, fresh mutable state per run, `min` of 5; not `timeit` (Chapter 95's lesson, which bit an early draft of this exact benchmark). Within-build ratios only.
CPython 3.14.6, both builds; Apple M3 Pro, macOS 27.0, arm64.

**The free-threaded build, by sharing shape.**

| shape | time | reading |
|---|---|---|
| 1 thread, private list, append | 17.9 ms | the unit |
| 4 threads, private lists | 20.7 ms | **scaling 3.5x**: uncontended locks are nearly free |
| 4 threads, ONE shared list | 107.0 ms | **worse than any serial option** |
| 1 thread, shared dict, read | 32.9 ms | the unit |
| 4 threads, shared dict, read | 46.8 ms | **scaling 2.8x**: lock-free lookups |
| 4 threads, shared dict, write | 375.3 ms | 8x the read row: one lock, four queues |

**The GIL build, same program**: private 4-thread appends take 67.2 ms against 16.5 serial (scaling 1.0x), the shared list takes 48.5 ms, reads 114.6 ms, writes 101.6 ms. Flat, as always; one lock, one price, no parallelism to lose.

**The shared-mutation row deserves its sentence in bold.**
Four threads on one list took 107 ms; one thread doing all four million appends takes about 70 (the GIL table's arithmetic). **Contending on a shared container is worse than not threading at all**: the queueing plus the container's cache line bouncing between four cores costs more than serialisation ever did. The GIL at least made the whole program pay one flat price; a hot shared container makes you pay the old price plus coherence traffic.

**And the hoist pair.**

| the same read loop, 4 threads | 3.14t | GIL build |
|---|---|---|
| dict hoisted to a local before the loop | 47.2 ms | 114.7 ms |
| dict read through the shared name each pass | 355.2 ms | 121.3 ms |
| ratio | **7.5x** | 1.06x |

No lock is taken in either row. The per-pass version executes a global load each iteration, which takes and drops a reference to the dict, from four threads, on one cache line: Chapter 94's contended-atomic row, applied to the container itself. The hoisted version takes one reference and rides it for a million iterations. Chapter 75 taught this hoist as a ~10% name-lookup trick, and the GIL column shows exactly that; the free-threaded column shows it deciding whether the code scales *at all*. This is the volume's clearest instance of an old micro-optimisation being promoted to an architectural rule by the new build.

**Book I**'s reading of this table is immediate: it is the C++ rule "shared mutable state is the enemy; shared immutable state is free; and false sharing on hot lines will find you", now true of Python with the same numbers-shape. The shared system's Python side shares its reference data (read-only dicts, hoisted at loop entry) and partitions its mutable state per worker, merging at boundaries, exactly the design Deep E recommended under the GIL, now with a 3.5x reason instead of a stylistic one.

---

## 96.4 Edges and failure modes

**Sharing a container for mutation is the new global lock.** §96.3.
Worse: the GIL serialised at ~zero marginal cost, while a contended container serialises *and* burns cores on coherence. The design fix is partition-then-merge (per-thread containers, combine at the end), the same shape as Chapter 94's "allocate where you use".

**The hoist rule generalises beyond globals.**
`self.cache[k]` in a loop touches `self`'s refcount and the cache's per pass; an attribute chain touches every link. On the GIL build this was Chapter 75's constant factor; on the free-threaded build, if the objects in the chain are shared, it is contention. Hoist shared objects into locals at loop entry; the bytecode you save is now measured in scaling, not percent.

**`queue.Queue` is the shared structure that is *designed* for this.**
It wraps its deque in a real lock plus condition variables (Chapter 49), and its price under contention is the price of that design, not an accident. When threads must share a mutable channel, share a `Queue`; when they must share a table, consider sharding it per thread. The builtin containers' per-op atomicity is a *compatibility* guarantee, not an invitation to use a `dict` as a concurrent database.

**Compound operations still need your lock, and now the stakes are measured.**
Everything Deep E said about check-then-act stands; Chapter 99 puts loss-rate numbers on it. The container's lock composing with yours is safe (its critical section suspends cleanly inside your `with lock:`), so the old discipline ports unchanged.

**Iteration over a concurrently-mutated container is a race even when each op is atomic.**
The single-threaded `RuntimeError` in the listing is best-effort detection, not a guarantee, under concurrent mutation: iterate a snapshot (`list(d.items())`) or hold a lock. The contract "iteration pins the shape" was always advisory across threads, on every build.

**Contention does not show up in profiles as a function.**
A thread spinning on a container's lock or bouncing a cache line is "executing" the same bytecode as a scaling thread; `cProfile` shows the same functions, only slower (Chapter 86's blind spot). The diagnostic is the shape of this chapter's benchmark, same work, varied sharing, run on your own hot structures.

**And the numbers are build-tier specific.**
Per-object locking, the lock-free read paths, and deferred references are under active development; 3.13t disabled specialization entirely and priced everything differently, and 3.15 will move these ratios again. The *shapes*, private scales, shared mutation collapses, reads scale if the refcounts stay off the hot path, are the durable content; re-derive the constants (Chapter 85) before betting a design on them.

---

## 96.5 Connections

**Backward.**
The mutex's home in the header, and the refcount price list the hoist pair instantiates, are Chapter 94. The safe-point suspension that lets critical sections coexist with stop-the-world collection is Chapter 95. Name lookup and the hoist as a constant-factor trick are Chapter 75; lock-ordering and deadlock are Chapter 53; `queue.Queue`'s design is Chapter 49; check-then-act discipline is Chapter 46. Container choice by access pattern is Chapter 88, which this chapter extends with a new column: sharing shape.

**Forward.**
What the locks and read paths cost the single-threaded interpreter is Chapter 97's accounting. Subinterpreters, which make every container private by construction and move the cost to the boundary, are Chapter 98. The correctness rules for code that shares anyway, with the loss rates measured, are Chapter 99, and Chapter 100 turns partition-then-merge into the default architecture.

**Across books.**
This chapter is the one where Python inherits C++'s concurrency folklore wholesale: fine-grained locking, lock coupling, optimistic reads with epoch-based reclamation (QSBR is RCU's cousin), false sharing, and the iron rule that contended cache lines beat algorithms as the real enemy. **Book I** measured `std::mutex` contention shapes in its own chapter; the tables agree in shape to a degree that would be suspicious if it were not the same silicon underneath.

---

## 96.6 Exercises

**1. Reproduce the shapes.** Run the benchmark on both builds. Then add a `queue.Queue` row (4 producers) and place its cost between the private and shared rows; explain its position from its design.

**2. Find your hoists.** Take a real hot loop of yours that reads shared state (module config, `self` attributes). Measure it 4-threaded on the t-build before and after hoisting every shared object into locals. Report the ratio and the diff, which should be a few lines.

**3. Shard a dict.** Implement a 16-shard dict (shard by `hash(k) & 15`, one lock each) and measure 4-thread mixed read/write against one shared dict and against `queue`-mediated single-writer. Find the write fraction at which sharding stops paying.

**4. Snapshot iteration.** Build the race: one thread iterating a dict, three mutating it. Show the failure modes you observe on the t-build, then fix with (a) `list(d.items())` and (b) a lock, and measure what each costs the mutators.

**5. False sharing hunt.** Four threads increment four *different* counters that are adjacent attributes of one object. Measure on the t-build, then pad or separate the counters and measure again. Relate to Chapter 94's cache-line edge.

**6. The design question.** PEP 703 gives every object a lock but gives `dict` lock-free reads, an asymmetry: writes pay for readers' freedom. Argue the choice against the alternative (reader-writer locks on containers): what RW locks cost uncontended readers (an atomic each way, exactly what the measurement shows killing scaling), why read-mostly is the common case worth privileging, and what workload the chosen design is worst at (write-heavy shared tables, §96.3's 375 ms). Then connect to Chapter 88's method: "choose the container for the access pattern" now has a concurrency column, and write down that column's decision table.

---

## 96.7 Summary and cross-references

- **Per-operation atomicity is preserved on every build**, verified byte-identical across the matrix: single ops on list, dict, set, and deque stay exact from four threads with no user locks. Compound operations were never covered, and the iteration contract is unchanged.
- **The machinery**: a `PyMutex` in every object; critical sections that suspend at safe points (so the collector can stop the world); lock coupling for two-container ops; **lock-free optimistic reads** for lookups, made safe by QSBR reclamation.
- **Measured on 3.14t**: private mutation scales **3.5x**; one shared list under four threads costs **107 ms where one thread does everything in ~70**, worse than not threading; shared dict reads scale **2.8x**; shared dict writes cost 8x the reads.
- **The hoist pair is the volume's sharpest result**: the same lock-free read loop runs at 47 ms with the dict hoisted to a local and 355 ms reading the shared name each pass, **7.5x**, from refcount traffic on the container itself. The GIL build's difference: 1.06x. Chapter 75's trick is now an architectural rule.
- **Design rules**: partition mutable state per thread and merge; share immutable data and hoist it at loop entry; use `queue.Queue` for channels; shard tables that must be written concurrently; and remember contention is invisible to `cProfile`.
- **The constants are a moving target across 3.13t/3.14t/3.15**; the shapes are the durable content. Re-derive before deciding.

**Cross-references.** The header's mutex and the refcount price list → Chapter 94. Safe points, QSBR, the collector → Chapter 95. Name lookup and the hoist → Chapter 75. Locks, queues, deadlock → Chapters 46, 49, 53. Container choice → Chapter 88. Single-threaded cost → Chapter 97. Subinterpreters → Chapter 98. Loss rates and correctness → Chapter 99. Architecture → Chapter 100.
