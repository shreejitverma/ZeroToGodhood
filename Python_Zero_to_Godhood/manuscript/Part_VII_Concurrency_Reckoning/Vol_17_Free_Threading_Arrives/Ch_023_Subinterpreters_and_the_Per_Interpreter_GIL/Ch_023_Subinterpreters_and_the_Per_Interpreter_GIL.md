# Chapter 23: Subinterpreters and the Per-Interpreter GIL (Python 3.12-3.14)

Chapter 8 established the hard fact of CPython concurrency: four threads doing CPU-bound work finish no
faster than one, because a single interpreter has a single GIL. The escape was processes, at the cost
of a serialization tax, separate memory, and `pickle` across a pipe. There is now a third option, and
it lives between the two:

| four CPU-bound tasks | speedup |
|---|---|
| four threads (one interpreter) | 1.01x |
| four **subinterpreters** (one process) | **3.48x** |

Four subinterpreters, in a *single process*, achieve real multi-core parallelism where four threads
achieve none, because each subinterpreter has its *own* GIL. This is the payoff of two changes: **PEP
684** (Python 3.12) gave each subinterpreter an independent GIL, and **PEP 734** (Python 3.14) exposed
a clean standard-library API, `concurrent.interpreters`, to use them from Python. This chapter is the
concurrency model Chapter 8 left as a forward reference: parallelism without the free-threaded build
(Deep L) and without the process-boundary tax.

> **Version note.** The `concurrent.interpreters` API is 3.14+ (PEP 734). Per-interpreter GILs exist
> from 3.12 via the C-API, and a private `_interpreters` module on 3.13, but the public, ergonomic API
> is 3.14. This chapter's listings are gated `# requires: 3.14+` and run on the 3.14 verification
> interpreter; on 3.13 the harness reports them skipped.

## Section index

- **23.1** The problem: one GIL per interpreter, and there was one interpreter
- **23.2** Subinterpreters: isolated Pythons in one process
- **23.3** Measurement: real CPU parallelism without processes
- **23.4** Subinterpreters versus threads versus processes versus free-threading
- **23.5** Edges and failure modes
- **23.6** Connections
- **23.7** Exercises
- **23.8** Summary and cross-references

Listings live under `code/ch023/` and are re-executed by `make verify` on the 3.14 interpreter.

---

## 23.1 The problem: one GIL per interpreter, and there was one interpreter

The GIL of Chapter 8 is not, strictly, a *process*-wide lock; it is an *interpreter*-wide lock. For
Python's entire history that distinction was academic, because a process had exactly one interpreter.
CPython had long supported *subinterpreters* internally (the C-API `Py_NewInterpreter`), but they all
*shared one GIL*, so they gave isolation without parallelism: you could run separate Python
environments in one process, but only one of them could execute bytecode at a time, exactly like
threads.

PEP 684 broke that sharing. It moved the GIL, and the great mass of interpreter state it protects (the
small-int cache, interned strings, the allocator's free lists, module state), from being process-global
to being *per-interpreter*. Once each interpreter has its own GIL and its own state, two subinterpreters
have no lock in common, so they run in genuine parallel on separate cores. The academic distinction
became the basis of a new concurrency model.

---

## 23.2 Subinterpreters: isolated Pythons in one process

A subinterpreter is a full, isolated Python inside the same process: its own GIL, its own imported
modules, its own module-level state, its own memory. Subinterpreters do *not* share objects; they pass
data through queues:

```python
# code/ch023/l01_subinterpreters.py   # requires: 3.14+
from concurrent import interpreters
interp = interpreters.create()
interp.exec("x = 40 + 2")
result = interp.call(lambda: 40 + 2)
```

Verified output (CPython 3.14.6):

```text
--- an isolated interpreter in the same process ---
  created: Interpreter(1)
  interp.call(lambda: 40 + 2): 42
  'x' in this interpreter's globals: False
  queue.get(): message from a subinterpreter
```

Three facts define the model. The subinterpreter runs code (`exec` a string, or `call` a callable) and
returns results. Its state is *isolated*: the `x` it bound does not exist in the main interpreter's
globals. And because objects are not shared, data crosses between interpreters through a `Queue` that
copies or shares only interpreter-safe values (immutable and buffer-like data). This isolation is the
whole safety story: with no shared mutable objects, there are no data races between subinterpreters, the
class of bug that makes shared-memory threading hard. You get parallelism with the *isolation* of
processes but the *cheapness* of staying in one process.

---

## 23.3 Measurement: real CPU parallelism without processes

The chapter opened with the result; here is the methodology.

**Methodology.** `code/ch023/bench_subinterpreters.py`. Four CPU-bound tasks (a five-million-iteration
integer loop each) run serially, across four threads, and across four subinterpreters each driven by a
thread. Subinterpreter creation is warmed once outside the timed region. `min` of three runs. CPython
3.14.6, Apple M3 Pro (12 cores), macOS 27.0, arm64.

| approach | speedup |
|---|---|
| serial | 1.00x |
| 4 threads (one interpreter) | **1.01x** |
| 4 subinterpreters (one process) | **3.48x** |

Four threads give nothing, confirming Chapter 8 on the same machine: one interpreter, one GIL, no
CPU parallelism. Four subinterpreters give **3.48x**, real multi-core parallelism, because each has its
own GIL and the four threads driving them run genuinely concurrent bytecode. And this happens in a
single process: no `fork`, no `spawn`, no `pickle` of arguments across a pipe. The 3.48x is comparable
to, and here better than, the process pool's 2.2x from Chapter 8, because subinterpreters skip the
process-creation and serialization overhead that ate into the process pool's parallelism.

The cost is different, not absent. Creating a subinterpreter is more expensive than a thread (it
initializes a fresh interpreter state), and passing data requires a queue rather than a shared variable.
So subinterpreters win for *coarse-grained* CPU work partitioned into independent chunks, and lose for
fine-grained sharing. They are the right tool when you have CPU-bound work you can split into isolated
pieces and you want to avoid both the GIL and the process boundary.

---

## 23.4 Subinterpreters versus threads versus processes versus free-threading

Python now has four models for running work concurrently, and the choice is a matter of what you share
and what you parallelize:

- **Threads** (Chapter 8): share everything (one interpreter, one memory, one GIL). Parallelize I/O,
  not CPU. Cheapest to create, cheapest to share, no CPU parallelism.
- **Subinterpreters** (this chapter): share a process but not objects (own GIL, own state per
  interpreter). Parallelize CPU, in one process, with isolation. Data crosses through queues.
- **Processes** (Chapter 8): share nothing (separate memory, separate everything). Parallelize CPU with
  full isolation, at the cost of spawn and `pickle` across a pipe.
- **Free-threaded build** (Deep L): one interpreter, *no* GIL, shared memory, CPU parallelism *with*
  shared objects, at the cost of per-object synchronization and an ecosystem that must be free-threading
  safe.

Subinterpreters and free-threading are the two answers to "CPU parallelism in Python," and they make
opposite trades. Free-threading keeps shared memory and pays with per-object locking and a rebuilt
ecosystem; subinterpreters keep the GIL (one per interpreter) and pay with isolation and message-passing.
For workloads that partition cleanly, subinterpreters are the safer path, no data races by construction.
For workloads with large shared state, free-threading is the only option that avoids copying it.

---

## 23.5 Edges and failure modes

**Expecting shared objects.** §23.2. Subinterpreters do not share Python objects; you cannot pass a
list from one to another and mutate it in both. Pass data through a `Queue`, and only interpreter-safe
(immutable or buffer-protocol) values cross cheaply.

**Fine-grained work.** §23.3. Subinterpreter creation and cross-interpreter messaging have real cost.
For small or tightly-coupled tasks, the overhead dominates; subinterpreters are for coarse, independent
CPU chunks.

**Using the API on 3.13 or earlier.** The public `concurrent.interpreters` is 3.14+. On 3.13 only the
private `_interpreters` exists, and its API is unstable; do not build on it.

**Extension-module compatibility.** A C extension must declare multi-phase-init support to run under
subinterpreters. Some extensions do not, and importing them in a subinterpreter fails or is unsafe.
Check before relying on a native dependency inside one.

**Assuming it replaces free-threading.** §23.4. They are different trades, not competitors. Choose by
whether your work can be partitioned into isolated pieces (subinterpreters) or needs shared mutable
state (free-threading).

---

## 23.6 Connections

**Backward.** The GIL that subinterpreters give one-per-interpreter is Chapter 8, whose threads-vs-
processes measurement this chapter extends with a third row. The interpreter state (small-int cache,
interned strings, allocator) that PEP 684 made per-interpreter is Chapters 19 and the allocator of
**Deep B**.

**Forward.** The free-threaded build, the other answer to CPU parallelism, is **Deep L**, and the JIT
that runs inside each interpreter is Chapter 21. Structured concurrency across subinterpreters, and the
queue and channel APIs in depth, are **Deep H**.

**Across books.** Subinterpreters are how a Book II service parallelizes CPU-bound Python across cores
without the process tax. An embedding or reranking stage in a **Book III** pipeline that does real
Python computation per document can fan the batch across subinterpreters in one process, each isolated,
sharing the loaded model data through a read-only buffer rather than re-pickling it per worker. When a
stage instead calls a **Book I** C++ kernel, the kernel releases its own GIL (Chapter 8), so
subinterpreters and native parallelism compose. **Deep H** and **Deep U** own those seams.

---

## 23.7 Exercises

**1. Reproduce the third row.** Run §23.3's benchmark and confirm four threads give ~1x and four
subinterpreters give real parallelism. Then vary the worker count from 1 to your core count and plot the
subinterpreter speedup; explain where it stops scaling and why.

**2. Measure the creation cost.** Time how long it takes to create and close a subinterpreter versus
starting and joining a thread versus spawning a process. Explain the ordering, and compute the task
size at which a subinterpreter's creation cost is amortized.

**3. Pass real data.** Send a list of numbers into a subinterpreter through a `Queue`, have it compute a
sum, and send the result back. Then try to pass a mutable object and mutate it in both interpreters, and
explain what happens (or does not) in terms of §23.2's isolation.

**4. Break isolation, safely.** Share a large read-only buffer (a `bytes` or a `memoryview` over one)
between two subinterpreters and confirm both can read it without copying. Explain why a buffer can cross
the boundary cheaply when a list cannot.

**5. The design question.** Python is pursuing *both* subinterpreters and the free-threaded build as
answers to the GIL. Argue whether that is redundant or complementary. Your answer must address the
shared-memory-versus-isolation trade from §23.4, which workloads each suits, and why the core team might
reasonably ship both rather than betting on one.

---

## 23.8 Summary and cross-references

- The GIL is **per-interpreter**, not per-process; **PEP 684 (3.12)** gave each subinterpreter its own
  GIL and its own state, so subinterpreters run in genuine parallel. **PEP 734 (3.14)** added the public
  `concurrent.interpreters` API.
- A **subinterpreter** is an isolated Python in one process: own GIL, own modules, own memory. Objects
  are *not* shared; data crosses through a `Queue` of interpreter-safe values, so there are no data
  races by construction.
- **Measured:** four subinterpreters achieve **3.48x** on CPU-bound work where four threads achieve
  **1.01x**, in a single process with no spawn or `pickle` tax.
- Subinterpreters and the **free-threaded build** (Deep L) are opposite trades: isolation with
  message-passing versus shared memory with per-object locking. Choose by whether the work partitions.

**Cross-references.** The GIL, threads, and processes → Chapter 8. Per-interpreter state and the
allocator → Chapter 19 and Deep B. The free-threaded build → Deep L. The JIT inside each interpreter →
Chapter 21. Structured concurrency and queues → Deep H. The CPU-parallelism seams to Books I and III →
Deep H and Deep U.
