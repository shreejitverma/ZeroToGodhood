# Chapter 8: The New GIL and the Concurrency Foundation (Python 3.1-3.2)

An engineer has a function that takes 300 milliseconds of pure computation, and a machine with twelve
cores. They split the work across four threads, expecting it to finish in roughly a quarter of the
time. It finishes in 300 milliseconds. Four threads, twelve idle cores, and not one millisecond
saved. Then they change `ThreadPoolExecutor` to `ProcessPoolExecutor`, one word, and it finishes in
140. The threads never ran in parallel; the processes did.

That result is the single most consequential fact about concurrency in CPython, and it is the
Global Interpreter Lock. Python 3.0 broke the language to fix correctness (Chapter 7); Python 3.1 and
3.2 were the quieter releases that made Python 3 *usable*, and their most important work was on this
exact foundation. Antoine Pitrou rewrote the GIL in 3.2 to end a decade-old pathology, and PEP 3148
gave thread and process parallelism one clean API so that the one-word change above is genuinely one
word. This chapter is about that concurrency foundation: what the GIL is, why it makes the opening
result inevitable, what the 3.2 rewrite actually changed, and how to reach real parallelism through it.

The 3.1-3.2 releases also filled a handful of standard-library gaps, `OrderedDict`, `Counter`, and
`argparse`. Those are genuinely useful and genuinely unrelated to the GIL, so this chapter does not
pretend otherwise: §8.5 notes what landed and points to where each is taught in full, rather than
stapling three feature descriptions onto a concurrency chapter.

## Section index

- **8.1** The GIL and why it exists
- **8.2** The new GIL: from the convoy effect to interval switching (3.2)
- **8.3** `concurrent.futures`: one API, two backends (PEP 3148)
- **8.4** Measurement: the GIL made visible
- **8.5** Also in 3.1-3.2, and where it is taught
- **8.6** Edges and failure modes
- **8.7** Connections
- **8.8** Exercises
- **8.9** Summary and cross-references

Listings live under `code/ch008/` and are re-executed by `make verify` on both interpreters.

---

## 8.1 The GIL and why it exists

**Why this exists.** The **GIL** (Global Interpreter Lock) is a single mutex that lets only one thread
execute Python bytecode at a time. It is not an accident or an oversight; it is a deliberate trade.
Every Python object carries a reference count (Chapter 19), and every `INCREF`/`DECREF` mutates it. If
multiple threads ran bytecode simultaneously, every one of those refcount mutations would need to be
atomic or locked, which would make the common case, single-threaded code, pay a synchronization cost
on every object operation. The GIL buys single-threaded speed and implementation simplicity by
serializing bytecode execution: with one lock held during execution, refcounting needs no per-object
locking at all.

The price is the opening result. Two CPU-bound Python threads cannot run bytecode at the same time,
because only one can hold the GIL, so threading a pure-computation workload yields no speedup. This is
a property of CPython, not of the Python language: other implementations make other choices, and the
free-threaded CPython build (**Deep L**) is CPython itself finally paying the per-object-locking cost
to remove the GIL. But for the default build this chapter describes, the GIL is the ground truth of
concurrency.

---

## 8.2 The new GIL: from the convoy effect to interval switching (3.2)

**Why this exists.** Before 3.2, the GIL was handed off by a **bytecode ticker**: after a thread ran
roughly 100 bytecodes (`sys.checkinterval`), it released the GIL and immediately tried to reacquire
it. On a multi-core machine this produced the **convoy effect**. The just-released thread, still hot
on its core with the GIL's memory in cache, usually reacquired the lock before a thread sleeping on
another core could even wake, so the waiter starved and the machine burned cycles on failed handoffs.
Worse, the ticker counted *bytecodes*, not time, so a single long-running opcode could hold the GIL
arbitrarily long.

**The fix (Python 3.2): time-based switching.** Pitrou's GIL switches on a *time interval* instead of
a bytecode count. A waiting thread waits on a condition variable for the interval; if it times out
still holding no GIL, it sets a shared `gil_drop_request` flag. The running thread checks that flag at
safe points in the eval loop and, when set, drops the GIL and hands off, so a contending thread is
guaranteed a turn within roughly one interval. The interval replaced `checkinterval` and is
observable:

```python
# code/ch008/l01_new_gil.py
import sys
print("  sys.getswitchinterval():", sys.getswitchinterval(), "seconds")
```

Verified output (CPython 3.13.5):

```text
--- the switch interval replaced the old bytecode ticker ---
  sys.getswitchinterval(): 0.005 seconds
  that is the maximum a CPU-bound thread holds the GIL before yielding.
--- is the GIL enabled on this build? ---
  sys._is_gil_enabled(): True
  (a free-threaded 3.13+ build can report False; this is a default build)
```

That 5 ms is the maximum a CPU-bound thread holds the GIL before being asked to yield. The critical
point, and the one that trips up most people: **this changed fairness, not parallelism.** The convoy
effect was a starvation bug, and the new GIL fixed it, so contending threads now take turns
promptly. But taking turns is not running together. Two CPU-bound Python threads still cannot execute
bytecode simultaneously under the new GIL; the interval only bounds how long one waits for its turn.
The `sys._is_gil_enabled()` check hints at the escape: a free-threaded 3.13+ build can report `False`,
and that build is where the story changes (**Deep L**). On the default build, the opening result
stands, and §8.4 measures it.

---

## 8.3 `concurrent.futures`: one API, two backends (PEP 3148)

**Why this exists.** Before 3.2, running work concurrently meant hand-managing `threading.Thread` or
`multiprocessing.Process` objects and wiring up your own result plumbing. **PEP 3148** added
`concurrent.futures`: one `Executor` interface with two interchangeable backends, a
`ThreadPoolExecutor` and a `ProcessPoolExecutor`, and a `Future` object carrying each task's eventual
result or exception. Because the API is identical across backends, the one-word change in the chapter
opening is genuinely one word:

```python
# code/ch008/l02_concurrent_futures.py
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

def main():
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(io_task, i) for i in range(5)]
        results = sorted(f.result() for f in as_completed(futures))
    ...
    with ProcessPoolExecutor(max_workers=2) as ex:
        results = list(ex.map(cpu_task, [1000, 2000, 3000]))
```

Verified output (CPython 3.13.5):

```text
--- ThreadPoolExecutor: submit returns a Future; as_completed yields them ---
  thread pool results: [0, 1, 4, 9, 16]
--- ProcessPoolExecutor: same API, separate interpreters ---
  process pool results: [332833500, 2664667000, 8995500500]
```

`submit()` returns a `Future` immediately; `as_completed()` yields futures as they finish; `map()`
applies a function across an iterable. A `Future` carries a result *or* an exception, and `.result()`
re-raises the exception in the caller, so error handling crosses the pool boundary cleanly.

**The choice between backends is the whole point, and it is dictated by the GIL.** A
`ThreadPoolExecutor` shares one interpreter and one GIL; its threads overlap only while blocked in
C-level I/O (a socket, a file, `sleep`) that *releases* the GIL. A `ProcessPoolExecutor` runs separate
interpreters with separate memory and separate GILs, so it achieves real CPU parallelism, but
arguments and results must cross the process boundary via `pickle` through an OS pipe. That
serialization is a real tax: for tiny tasks the transfer dominates and a process pool is *slower* than
serial code. The rule is threads for I/O, processes for CPU, and pool coarse-grained work in both
cases.

There is one operational gotcha worth stating because it is a frequent first crash. On macOS and
Windows the default process start method is **spawn**, which launches a fresh interpreter that
*re-imports your module* to find the worker function. Any code at module top level runs again in every
worker, so pool code must sit under `if __name__ == "__main__":` and worker functions must be
importable top-level names, not lambdas or closures (which are unpicklable). Omitting the guard
re-runs your top-level code in each worker and can recursively spawn pools.

---

## 8.4 Measurement: the GIL made visible

The opening result was a claim. Here it is measured, which is also the clearest way to *see* what the
GIL does and does not do.

**Methodology.** `code/ch008/bench_gil.py`. Four tasks run serially, across four threads, and (for the
CPU case) across four processes. CPU task: a three-million-iteration integer sum. I/O task: a 50 ms
`sleep`. `min` of five runs; the process pool is warmed once so its spawn cost falls outside the timed
region. This benchmark does its own coarse-grained timing rather than the microbenchmark harness,
because a process pool cannot be spun up thousands of times, but it carries the same provenance header.
CPython 3.13.5, `-O2`, computed gotos on, `sys._is_gil_enabled()` True, Apple M3 Pro (12 cores), macOS
27.0, arm64. Ratios reproduced across runs.

| workload | backend | speedup |
|---|---|---|
| CPU-bound | 4 threads | **1.04x** |
| CPU-bound | 4 processes | **2.2x** |
| I/O-bound | 4 threads | **~3.9x** |

Three facts, and together they are the entire practical meaning of the GIL.

**CPU-bound threads: 1.04x, no speedup.** Four threads, twelve cores, and the work takes as long as
doing it serially, because the GIL lets only one thread execute bytecode at a time. The 4% is noise,
not parallelism. This is the opening result, confirmed.

**CPU-bound processes: 2.2x.** Changing one word to `ProcessPoolExecutor` gives real parallelism,
because each process has its own interpreter and its own GIL. It is 2.2x rather than 4x because the
serialization tax from §8.3 is real: pickling the arguments out and the results back, and the process
startup, eat into the theoretical maximum. Real parallelism is not free parallelism.

**I/O-bound threads: ~3.9x, near-linear.** The same threads that gave nothing for CPU work give almost
perfect scaling for I/O, because `time.sleep` (like a socket read or a file write) is a blocking C
call that *releases the GIL* while it waits. Four threads sleep concurrently; the GIL is only needed
to run bytecode, and sleeping is not running bytecode.

So the decision procedure is not a matter of taste: **threads for I/O-bound work, processes for
CPU-bound work.** The GIL makes threads useless for the first kind of parallelism and irrelevant to
the second. Everything else in Python's concurrency story, `asyncio` (Chapter 11) for high-count I/O,
subinterpreters and free-threading (**Deep L**) for GIL-free CPU parallelism, is a refinement of this
one measurement.

---

## 8.5 Also in 3.1-3.2, and where it is taught

Three standard-library additions landed in this window that have nothing to do with the GIL and are
not taught here, because forcing them into a concurrency chapter would be exactly the changelog-with-
prose this book avoids. They are named here with their canonical homes so nothing is lost:

- **`OrderedDict`** (PEP 372, 3.1). A `dict` that remembers insertion order via an internal linked
  list. Since Python 3.7 made insertion order a language guarantee for plain `dict`, most of its
  original purpose is gone, but two behaviors remain distinct: its `==` is *order-sensitive*, and it
  offers `move_to_end()`. Taught in full in **Deep Q** (the collections module).
- **`Counter`** (3.1). A `dict` subclass for tallying, with `most_common()` and multiset arithmetic.
  Also **Deep Q**.
- **`argparse`** (3.2). The declarative command-line parser that replaced `optparse`. Taught in full,
  with subcommands and custom actions, in **Deep S** (system and tooling).

That is the honest treatment: a release note, not a lesson pretending these three share a theme with
Pitrou's GIL.

---

## 8.6 Edges and failure modes

**Threads for CPU-bound work.** §8.4. The classic mistake, and it produces no speedup or a slight
slowdown from GIL contention. CPU work needs processes (or the free-threaded build, **Deep L**).

**Process pools over microtasks.** §8.3. If a task is faster than pickling plus IPC, the pool loses to
serial code. Batch work into coarse chunks; pass references or handles, not megabytes of data.

**Missing `if __name__ == "__main__"` with a process pool under spawn.** §8.3. Re-runs module-level
code in every worker and can fork-bomb. Always guard.

**Unpicklable pool payloads.** Lambdas, closures, local functions, open sockets. A process pool can
only take top-level functions and picklable arguments.

**Tuning `setswitchinterval` blindly.** Lowering it increases handoff fairness but raises switching
overhead, and it does *not* add parallelism (§8.2). Profile before touching it; the default 5 ms is
right for almost everything.

**Assuming the GIL is gone because you read that it was being removed.** The free-threaded build exists
(3.13+) but is not the default, and a default build still has the GIL, as `sys._is_gil_enabled()`
confirms. Do not design around GIL-free execution you have not verified is enabled (**Deep L**).

---

## 8.7 Connections

**Backward.** The reference counting the GIL protects, and the reason per-object locking would
otherwise be needed, is Chapter 19 (**Deep A**). The eval loop that checks `gil_drop_request` at safe
points is Chapter 2's evaluation loop.

**Forward.** `asyncio` (Chapters 10-11) is the other answer to I/O concurrency, single-threaded
cooperative scheduling that avoids even the thread overhead §8.4 measures. The complete GIL model, the
free-threaded build (PEP 703), and per-interpreter GILs (PEP 684) are **Deep L**, the canonical home
for GIL-free parallelism. Concurrency engineering under latency pressure, the trading loop, is **Deep
K** and the capstone. `OrderedDict`, `Counter`, and `argparse` are **Deep Q** and **Deep S** (§8.5).

**Across books.** The GIL is also the oldest reason the boundary to **Book I** matters: a long C or C++
computation called through `nanobind` can *release the GIL* while it runs (the classic
`Py_BEGIN_ALLOW_THREADS` block), letting other Python threads execute during a heavy native call. This
is real parallelism from Python threads, achieved precisely by leaving Python. The order-book's C++
matching engine releases the GIL during a match, so the Python analytics threads keep running. **Deep
M** owns that boundary, and it is the most practical GIL escape hatch of all.

---

## 8.8 Exercises

**1. Reproduce the opening result.** Write a CPU-bound function and time it serial, across four
threads, and across four processes, to the standard of §8.4. Confirm threads give no speedup. Then
find the smallest task size at which the *process* pool finally beats serial code, and explain what
you are measuring at the crossover.

**2. Watch the GIL release.** Take the I/O task and replace `time.sleep` with a pure-Python busy-wait
loop of equivalent duration. Predict, before running, what happens to the four-thread speedup, then
measure it. Explain the result in terms of which operations release the GIL and which do not.

**3. Break the spawn guard.** Write a process-pool program *without* `if __name__ == "__main__"` and
observe the failure on macOS or Windows (or reason precisely about what would happen on fork-only
Linux, where it differs). Explain why the guard is unnecessary under the `fork` start method and
required under `spawn`.

**4. Tune the interval, measure nothing.** Set `sys.setswitchinterval` to a very small and a very large
value and measure a two-thread CPU-bound workload under each. Show that neither adds parallelism, and
explain what the interval *does* change (fairness and switching overhead) and why that never becomes
throughput for CPU work.

**5. The design question.** The GIL buys single-threaded speed and implementation simplicity at the
cost of multi-core CPU parallelism for threads. The free-threaded build (**Deep L**) reverses that
trade, paying per-object synchronization to remove the lock. Argue which default is right for a
general-purpose language in 2025, given this chapter's measurements and Chapter 19's finding that every
object operation touches a refcount. Your answer must address why the free-threaded build was made
*optional* rather than replacing the GIL outright.

---

## 8.9 Summary and cross-references

- The **GIL** serializes bytecode execution so refcounting (Chapter 19) needs no per-object locking. It
  buys single-threaded speed at the cost of multi-core CPU parallelism *for threads*.
- The **new GIL (3.2)** switches on a **5 ms time interval** (`sys.getswitchinterval()`) via a
  `gil_drop_request` handoff, ending the **convoy effect**. It changed **fairness, not parallelism**.
- **`concurrent.futures`** (PEP 3148) gives one `Executor`/`Future` API over two backends: **threads
  for I/O**, **processes for CPU** (paying a `pickle`+IPC tax). Guard pool code with `if __name__ ==
  "__main__"` under spawn.
- **Measured:** CPU-bound work gets **1.04x** from four threads (no speedup, the GIL), **2.2x** from
  four processes (real parallelism minus the serialization tax), and I/O-bound work gets **~3.9x** from
  four threads (the GIL is released during blocking I/O). This is the whole practical meaning of the
  GIL.
- `OrderedDict`, `Counter`, and `argparse` also landed in 3.1-3.2 and are taught in Deep Q and Deep S;
  they are noted here, not stapled onto a concurrency chapter.

**Cross-references.** Reference counting, why the GIL exists → Chapter 19 (Deep A). The eval loop and
`gil_drop_request` → Chapter 2. `asyncio` and cooperative I/O → Chapters 10-11. The GIL model, the
free-threaded build, and per-interpreter GILs → Deep L. Concurrency under latency pressure → Deep K.
`collections` and `argparse` → Deep Q and Deep S. Releasing the GIL across the C boundary → Deep M.
