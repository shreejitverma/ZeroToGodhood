# Chapter 10: Asyncio Inception, Pathlib, and Enum (Python 3.4)

Serve five hundred network clients that each spend most of their time waiting. Do it the obvious way,
one after another, and five hundred half-second waits take four minutes. The clients are not slow;
your code is, because it insists on finishing each wait before starting the next, when the whole
point of waiting is that the CPU is idle and could be doing something else.

Python 3.4 shipped the standard answer to that problem, `asyncio`, and it collapses those four minutes
to about a tenth of a second by overlapping the waits on a single thread. But 3.4's contribution was
broader than one library: it shipped three additions that share a single design idea. Each replaced a
grab-bag of primitive-based idioms with a proper object model. `asyncio` (PEP 3156) replaced callback
spaghetti and thread-per-connection with an event loop and coroutines. `pathlib` (PEP 428) replaced
string-based path juggling with path *objects*. `enum` (PEP 435) replaced bare integer constants with
real enumerations. This chapter teaches the model behind each, with `asyncio` as the deepest treatment
because it is the through-line to Chapter 11's `async`/`await` syntax.

## Section index

- **10.1** Asyncio inception: the event loop, Futures, and Tasks (PEP 3156)
- **10.2** `pathlib`: object-oriented filesystem paths (PEP 428)
- **10.3** `enum`: enumerations via a metaclass (PEP 435)
- **10.4** Measurement: what asyncio buys, and what it does not
- **10.5** Edges and failure modes
- **10.6** Connections
- **10.7** Exercises
- **10.8** Summary and cross-references

Listings live under `code/ch010/` and are re-executed by `make verify` on both interpreters.

---

## 10.1 Asyncio inception: the event loop, Futures, and Tasks (PEP 3156)

**Why this exists.** For I/O-bound workloads, thousands of sockets mostly *waiting*, a thread per
connection wastes memory and pays context-switch and GIL-contention costs (Chapter 8), while raw
callback code becomes "callback hell." `asyncio` offers a third model: one thread, one event loop,
cooperative multitasking. Tasks voluntarily suspend at `await` points; while one waits on I/O, the
loop runs others. No preemption, no per-connection thread, no data races on state touched only between
awaits.

**What the loop actually does.** `asyncio` is built on the OS's I/O multiplexing. The loop registers
each descriptor with the `selectors` module, which maps to the best available syscall (`epoll` on
Linux, `kqueue` on macOS, `select`/`poll` elsewhere), noting which event each task awaits. It calls
`selector.select()`, which blocks the single thread in the kernel until at least one descriptor is
ready or a timer fires. On wake, it runs each ready descriptor's callback, which resumes the suspended
task. Two objects carry results: a **`Future`** is a placeholder for a value that will exist later
(PENDING to FINISHED/CANCELLED, with done-callbacks); a **`Task`** is a `Future` subclass that drives
a coroutine, calling `coro.send(...)` to advance it to the next suspension point, registering itself
as the done-callback of whatever future the coroutine awaits, and yielding to the loop.

That `coro.send(...)` is the connection to Chapter 9: a Task drives a coroutine using the exact
send-into-a-suspended-frame mechanism generators gave us. In 3.4, a coroutine was literally a generator
decorated with `@asyncio.coroutine` that delegated with `yield from`. That decorator was removed in
3.11, which the listing confirms, but the model is unchanged:

```python
# code/ch010/l01_asyncio_loop.py
async def worker(name, delay):
    await asyncio.sleep(delay)
    return f"{name} done"

async def main():
    results = await asyncio.gather(worker("A", 0.05), worker("B", 0.05), worker("C", 0.05))
    ...
```

Verified output (CPython 3.13.5):

```text
--- the 3.4-era @asyncio.coroutine decorator was removed in 3.11 ---
  hasattr(asyncio, 'coroutine'): False
--- three 0.05s waits run concurrently on one thread ---
  results: ['A done', 'B done', 'C done']
  overlapped (elapsed well under the 0.15s serial sum): True
```

The three 0.05-second waits overlap: the total is one delay, not three, on a single thread. (The
listing checks `elapsed < 0.12` structurally rather than printing the exact timing, which varies per
run; the timing itself is §10.4.)

**The senior-engineer contrast.** This is cooperative scheduling, like Go's goroutines or Node's event
loop, but explicit: a task runs uninterrupted until it `await`s, so there is no preemption and no lock
needed for data touched only between awaits. The flip side, and the headline anti-pattern (§10.5), is
that a *blocking* call (a synchronous `requests.get`, a CPU-bound loop) stalls the entire loop and
every other task. The `async`/`await` syntax is Chapter 11; event-loop internals, `TaskGroup`,
cancellation, and structured concurrency are **Deep H**.

---

## 10.2 `pathlib`: object-oriented filesystem paths (PEP 428)

**Why this exists.** Before 3.4, a path was a `str`, and manipulating it meant a grab-bag of `os.path`
functions (`join`, `dirname`, `splitext`) plus manual separator handling. `pathlib` makes a path a
typed object with methods, an overloaded `/` join operator, and a clean split between *pure*
(string-only, no I/O) and *concrete* (touches the filesystem) operations.

```python
# code/ch010/l02_pathlib.py
from pathlib import Path, PureWindowsPath
p = Path("/var") / "log" / "nginx.log"     # __truediv__ joins, per-OS separators
```

Verified output (CPython 3.13.5):

```text
--- component algebra with no syscalls ---
  joined     : /var/log/nginx.log
  parts      : ('/', 'var', 'log', 'nginx.log')
  name       : nginx.log
  suffix     : .log
  stem       : nginx
  with_suffix: /var/log/nginx.gz
  parent     : /var/log
--- a pure path can parse a foreign OS's paths on this host ---
  PureWindowsPath('C:/a/b'): C:\a\b
  Path('.') concrete type  : PosixPath
```

The type hierarchy is the design: `PurePath` does path *algebra* with no syscalls (and can parse a
foreign OS's paths, as the `PureWindowsPath` line shows, printing a Windows path on this POSIX host);
`Path` adds filesystem operations and instantiates as a `PosixPath` or `WindowsPath` for the host. The
`/` operator (`__truediv__`) reads naturally and handles separators per-OS, so the same code is correct
on Windows and POSIX. `Path` also unifies what used to be scattered calls: `read_text(encoding=...)`,
`write_bytes(...)`, `glob("*.log")`, `mkdir(parents=True)`, `exists()`, `stat()`. Prefer `pathlib`
over `os.path` in new code; the standard library now accepts path-like objects everywhere via
`os.PathLike`.

---

## 10.3 `enum`: enumerations via a metaclass (PEP 435)

**Why this exists.** Before 3.4, "enums" were bare module constants (`RED = 1`): no namespacing, no
type safety, no iteration, no readable `repr`, and any int compared equal to them. `enum` provides
real enumerations, named, singleton, immutable, iterable members.

**What the metaclass does.** An `Enum` subclass is built by the `EnumMeta` (aka `EnumType`) metaclass
(the metaclass machinery is Chapter 4 and **Deep C**). It uses a custom namespace dict during class
creation to capture member definitions in order and reject duplicate *names*, then replaces each `NAME
= value` with a singleton instance carrying that name and value, and installs lookup hooks.

```python
# code/ch010/l03_enum.py
from enum import Enum, unique
class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3
```

Verified output (CPython 3.13.5):

```text
--- iteration, dual-key lookup, singleton identity, immutability ---
  members (declaration order): ['RED', 'GREEN', 'BLUE']
  by name  Color['RED']       : Color.RED
  by value Color(2)           : Color.GREEN
  singleton  Color.RED is Color(1): True
  Color.RED.value = 99        -> AttributeError (immutable)
--- duplicate VALUES create aliases, not new members ---
  Status.RUNNING is Status.ACTIVE: True
  distinct members              : ['ACTIVE']
--- @unique forbids that when you want distinct values enforced ---
  @unique with duplicate value -> ValueError: duplicate values found in <enum 'MustDiffer'>: B -
```

Members are singletons (`Color.RED is Color(1)`), so compare them with `is`/`==` and switch on them in
`match`/`case` (Chapter 16). Two behaviors worth internalizing from the output. Iteration is in
declaration order, and lookup is dual-keyed, by name (`Color['RED']`) and by value (`Color(2)`). And
the subtle one: **duplicate *values* create aliases, not new members.** `Status.RUNNING = 1` after
`ACTIVE = 1` makes `RUNNING` a second name for the `ACTIVE` member, and iteration shows only `ACTIVE`.
When you want distinct values enforced, `@enum.unique` turns that into a `ValueError` at class
creation. The `enum` family extends well beyond this base, `IntEnum`, `Flag`/`IntFlag`, `auto()`,
`StrEnum` (3.11), all developed in **Deep Q**.

---

## 10.4 Measurement: what asyncio buys, and what it does not

The chapter opened by claiming asyncio collapses four minutes to a tenth of a second. That is true, and
also incomplete, because the more common comparison is not against sequential code but against threads,
and there the answer is more interesting.

**Methodology.** `code/ch010/bench_asyncio_scaling.py`. 500 concurrent 0.05-second I/O waits, run
sequentially, with `asyncio.gather`, and with 500 threads. Then asyncio's scaling from 100 to 2000
tasks, and per-Task memory via `tracemalloc`. `min` of three runs; coarse-grained timing done directly
(an event loop is not a microbenchmark). CPython 3.13.5, Apple M3 Pro (12 cores), macOS 27.0, arm64.

| approach | time | vs asyncio |
|---|---|---|
| sequential | 26.8 s | 479x slower |
| asyncio `gather` | 0.056 s | 1.00x |
| 500 threads | 0.071 s | 1.27x slower |

And the scaling and memory:

| | value |
|---|---|
| asyncio, 100 tasks | 0.052 s |
| asyncio, 2000 tasks | 0.069 s |
| per asyncio Task | **~810 bytes** |
| per thread | a full stack (OS default, ~8 MB of virtual address space) |

**Against sequential code, asyncio is a rout at 479x**, because it overlaps 500 waits that were being
done one at a time. That is the chapter opening, confirmed.

**Against threads, asyncio is only 1.27x faster at this scale**, and that is the correction most guides
skip. Threads overlap blocking I/O too, because a blocking syscall releases the GIL (Chapter 8), so at
500 tasks threads and asyncio finish in comparable time. If you believed asyncio's value was raw speed
over threads, this is where that belief fails.

**asyncio's real advantage is scale, visible in the last two rows.** Going from 100 to 2000 tasks adds
17 milliseconds: the loop is one thread and a Task costs about 810 bytes, so ten thousand concurrent
connections is ten thousand cheap objects on one thread. Ten thousand *threads* is ten thousand stack
reservations and enough scheduler pressure to hit OS limits. **asyncio is how you serve C10k**, tens of
thousands of concurrent I/O operations, on hardware where a thread-per-connection model runs out of
memory. Reach for asyncio when the concurrency count is high, not when you want a task to run faster
than it would on a thread.

---

## 10.5 Edges and failure modes

**Blocking the event loop.** §10.1. A synchronous network call, file read, or CPU-bound loop inside a
coroutine freezes *every* task, because there is one thread and it is busy. Use async libraries, or
offload blocking work with `loop.run_in_executor`/`asyncio.to_thread` (**Deep H**). This is the single
most common asyncio bug.

**Expecting asyncio to parallelize CPU work.** §10.4 and Chapter 8. asyncio is I/O concurrency on one
thread; one thread is one core. CPU parallelism still needs processes or the free-threaded build
(**Deep L**).

**Choosing asyncio for raw speed over threads.** §10.4. At moderate task counts they are comparable.
The reason to choose asyncio is task-count scale and memory, not per-task latency.

**`pathlib` in a tight loop over millions of paths.** Each operation constructs a new immutable `Path`,
which has slight overhead versus raw `str`. For millions of path manipulations, `os.path` string ops
can be faster; everywhere else, prefer `pathlib` for correctness and readability.

**Enum aliasing.** §10.3. Duplicate *values* create aliases, not new members, silently. Use
`@enum.unique` to forbid it when values must be distinct.

**`IntEnum` comparing equal to plain ints.** An `IntEnum` member `== 1` is `True`, which can mask type
errors. Prefer a plain `Enum` unless int-compatibility is genuinely required (for a C API or a wire
protocol).

---

## 10.6 Connections

**Backward.** The `coro.send(...)` a Task uses to drive a coroutine is the generator send protocol of
Chapters 5 and 9, and `yield from` (Chapter 9) is the delegation channel 3.4's `@asyncio.coroutine`
built on. The GIL that makes one loop one core, and that threads release during blocking I/O, is
Chapter 8. The `EnumMeta` metaclass is Chapter 4.

**Forward.** Native `async`/`await` syntax, the same event-loop model with dedicated keywords, is
Chapter 11. Event-loop internals, `TaskGroup`, cancellation, and structured concurrency are **Deep H**;
the free-threaded build is **Deep L**. The full `enum` family and `graphlib` are **Deep Q**; the
`pathlib`/`os` filesystem reference is **Deep R**. Benchmarking concurrency is **Deep K**.

**Across books.** asyncio is how Book II feeds **Book III** at scale: a retrieval service handling
thousands of concurrent embedding requests runs them on one event loop, each request a cheap Task
awaiting a model call, rather than a thread per request. The order-book's market-data ingest is an
asyncio consumer of thousands of concurrent socket streams. When one of those coroutines needs CPU-
heavy work (a C++ inference kernel), it offloads across the boundary to **Book I** via `run_in_executor`
so the loop keeps serving. **Deep M** owns that offload path; asyncio is the scheduler that decides
when to take it.

---

## 10.7 Exercises

**1. Reproduce the opening number.** Run 500 I/O waits sequentially, with `asyncio.gather`, and with
500 threads, to the standard of §10.4. Confirm asyncio's huge win over sequential and its modest win
over threads. Then increase the task count until the thread version fails or slows sharply, and report
where that happens on your machine and why.

**2. Block the loop, watch everything stall.** Write two coroutines, one that `await asyncio.sleep`s
and one that does a synchronous `time.sleep` (a stand-in for a blocking call), run them concurrently,
and show that the blocking one prevents the other from making progress. Then fix it with
`asyncio.to_thread` and show the overlap return. Explain what the fix actually moved off the loop.

**3. Measure the Task footprint.** Create N asyncio Tasks (that await a long sleep) for increasing N and
measure the memory with `tracemalloc`, confirming the per-Task cost from §10.4. Then estimate how many
threads would fit in the same memory, and state the concurrency ceiling each model implies on a machine
with 8 GB of RAM.

**4. Find the enum alias.** Define an enum with a deliberate duplicate value, show that iteration hides
the alias and that the two names are the same object, then add `@enum.unique` and show the `ValueError`.
Explain, using §10.3, why aliasing is the default and when it is actually the behavior you want.

**5. The design question.** asyncio, threads, and processes are three concurrency models with different
costs (this chapter and Chapter 8 measured all three). Write the decision procedure you would give a
new engineer: given a workload, how do they choose? Your answer must cover I/O-bound versus CPU-bound,
low versus high task count, and the one measurement from each chapter that most drives the choice.

---

## 10.8 Summary and cross-references

- **asyncio** (PEP 3156) is a **single-threaded cooperative event loop** over OS I/O multiplexing
  (`selectors` to `epoll`/`kqueue`/`select`); **Futures** hold pending results and **Tasks** drive
  coroutines by `send`-ing them forward when their awaited future completes. The 3.4
  `@asyncio.coroutine` + `yield from` syntax is gone (removed 3.11); the model is unchanged.
- **pathlib** (PEP 428) makes paths objects: `PurePath` (algebra) versus `Path` (I/O), the `/` join
  operator, and a rich component and I/O API. Prefer it over `os.path`.
- **enum** (PEP 435) builds **singleton, immutable, iterable** members via `EnumMeta`, dual-keyed by
  name and value; duplicate *values* create **aliases**, forbidden by `@unique`.
- **Measured:** for 500 concurrent I/O waits, asyncio is **479x** faster than sequential but only
  **1.27x** faster than threads; its real advantage is scale, **~810 bytes per Task** against a
  thread's full stack, which is how it serves tens of thousands of connections on one thread.

**Cross-references.** `yield from` and the suspendable frame → Chapter 9. Native `async`/`await` →
Chapter 11. Event-loop internals, `TaskGroup`, structured concurrency → Deep H. The GIL and one-loop-
one-core → Chapter 8; the free-threaded build → Deep L. The full `enum` family → Deep Q; `pathlib`/`os`
→ Deep R. Benchmarking concurrency → Deep K. The offload path to Book I → Deep M.
