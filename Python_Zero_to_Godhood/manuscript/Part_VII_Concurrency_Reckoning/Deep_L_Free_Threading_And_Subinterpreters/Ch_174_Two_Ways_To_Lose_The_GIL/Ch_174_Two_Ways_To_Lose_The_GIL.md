# Chapter 93: Two Ways to Lose the GIL

For thirty years, every chapter of Python's concurrency story ended the same way: the threads were real, the parallelism was not. Chapter 8 measured it, Chapter 80 measured it again at the C boundary, and Deep E built an entire discipline around it. This volume is about the two escapes CPython built between 3.12 and 3.14, and it opens with the number the whole project exists for.

The same CPU-bound function, four calls, on four threads: on the GIL build of CPython 3.14.6 the threads buy a factor of **1.06**. On the free-threaded build of the *same version*, they buy **3.69**. Three lines of `threading` code, unchanged, and the wall clock divides by nearly the core count.

This volume measures that machine instead of citing it, because the free-threaded build is now in this book's verification matrix, which is the event Chapter 26 said would convert its cited figures into measured ones. And the first measured figure is a correction to folklore: on this workload the free-threaded build's *single-threaded* run was not 10% slower, it was 10% **faster**. The suite-average overhead PEP 779 tracks is real; per-workload deltas point both ways, and only measurement tells you which way yours points.

**This is a Deep L chapter, and it opens Deep L.**
Chapters 23, 26, and 27 own the release story, how subinterpreters, the free-threaded build, and the JIT arrived. Deep E owns threads, locks, and the discipline of using them. This volume owns the mechanisms that replaced the GIL and the measurements they change; this chapter owns the map.

## Section index

- **93.1** Two builds, one API, counted
- **93.2** What the GIL was actually doing, and what replaced each job
- **93.3** Measurement: the headline, on both builds
- **93.4** Edges and failure modes
- **93.5** Connections
- **93.6** Exercises
- **93.7** Summary and cross-references

Listings live under `code/ch174/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 93.1 Two builds, one API, counted

```python
# code/ch174/l01_two_builds_one_api.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- build identity ---
  compiled with Py_GIL_DISABLED : False
  abiflags                      : ''
  sys._is_gil_enabled()         : True
```

Verified output (CPython 3.14t, the free-threaded build at 3.14.6):

```text
--- build identity ---
  compiled with Py_GIL_DISABLED : True
  abiflags                      : 't'
  sys._is_gil_enabled()         : False
```

And the remainder is Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- the API is unchanged, and so is the discipline ---
  4 threads x 100,000 locked increments : 400,000
  same Thread, same Lock, same result on every build: code that locked
  its compound operations (Chapter 46) does not notice the GIL leaving
--- single container operations stay atomic ---
  4 threads x 100,000 list.append, no lock : 400,000
  on the GIL build the GIL made one append atomic; on the free-threaded
  build the LIST'S OWN LOCK does (Chapter 96). the guarantee survives;
  the mechanism providing it changed completely
```

**The identity trio is a build fact, a filename fact, and a runtime fact, in that order.**
`Py_GIL_DISABLED` is compiled in; `abiflags` of `'t'` is why the build needs its own wheels (`cp314t`, §93.4); and `sys._is_gil_enabled()` is the *runtime* report, which can disagree with the build: `-X gil=1` re-enables the GIL on a free-threaded build for one run, and importing an extension that declares no free-threaded support re-enables it automatically, silently changing the answer mid-process. Detect the build with `sysconfig`; detect the moment with `sys._is_gil_enabled()`.

**The two 400,000s are the volume's ground rule.**
The locked counter is Deep E's discipline surviving intact: code that already locked its compound operations does not notice the GIL leaving. The unlocked `append` is more subtle and more important: **per-operation atomicity on the builtin containers is preserved**, but by a completely different mechanism, the container's own lock (Chapter 96), engineered specifically so that the enormous corpus of existing threaded Python does not corrupt its lists and dicts on the new build.

**And the closing block states what was never promised.**
`counter += 1` without a lock loses updates under the GIL too, Chapter 46 measured it, because the GIL serializes bytecode instructions, not your invariants. The free-threaded build raises the frequency of that loss (Chapter 99 measures how much); it does not create the obligation. If a program is correct on the free-threaded build's terms, it was correct before; a program that breaks was broken.

---

## 93.2 What the GIL was actually doing, and what replaced each job

The GIL was one lock doing five jobs. Removing it meant hiring five replacements, and the volume's structure is that list:

| the GIL's job | its replacement (PEP 703) | chapter |
|---|---|---|
| make refcount `+= 1` safe across threads | biased and atomic reference counting, immortality, deferred refcounts | 94 |
| make the allocator and GC safe | mimalloc-based thread-aware allocator; stop-the-world collection with QSBR reclamation | 95 |
| make one `list.append` / `dict[k] = v` atomic | per-object locks and critical sections | 96 |
| keep the specializing interpreter's caches coherent | thread-safe specialization, rebuilt for 3.14 | 97 |
| give the C-API its serialized world | the `t` ABI, and extensions opting in | 94, and Deep M |

**Two properties of that table drive everything else in the volume.**
First, every replacement is **per-object or per-thread machinery where one global lock used to be**, which is why the single-threaded cost question (§93.3, Chapter 97) is the project's central tension: the replacements must be cheap enough that the build is viable *before* the threads arrive. Second, the replacements preserve **observable semantics**, not implementation behaviour: refcounts still reach zero, containers still refuse to tear, but `sys.getrefcount` reports differently (Chapter 94) and timing-sensitive code notices everything.

**The second escape refuses the whole table.**
A subinterpreter (PEP 684, and PEP 734's `concurrent.interpreters` in 3.14) keeps a GIL, one *each*. Nothing is shared, so nothing above needs replacing; the cost moves to the boundary, where every object that crosses must be copied or explicitly shared (Chapter 98). Free-threading pays per-object coordination to keep shared memory; subinterpreters pay per-byte crossing costs to avoid coordination entirely. They are the two ends of the oldest trade in concurrent systems, and Chapter 100 closes the volume by choosing between them, and processes, and `asyncio`, with measurements.

---

## 93.3 Measurement: the headline, on both builds

**Methodology.** `code/ch174/bench_thread_scaling.py`.
One CPU-bound function (`total += i*i` over two million iterations, ~50 ms per call), run once, four times sequentially, and four times on four threads. `min` of 5. Ratios within one build only.
CPython 3.14.6, GIL and free-threaded builds; Apple M3 Pro (12 cores), macOS 27.0, arm64. The two builds match on every other dispatch-critical flag (`OPT`, computed gotos, PGO, LTO; `make interpreters` verifies this).

**The GIL build.**

| CPython 3.14.6 (GIL) | time | vs sequential |
|---|---|---|
| one call | 51.1 ms | — |
| 4 calls, sequential | 219.6 ms | 1.00x |
| 4 calls, on 4 threads | 206.9 ms | **1.06x** |

**The free-threaded build.**

| CPython 3.14.6t (free-threaded) | time | vs sequential |
|---|---|---|
| one call | 45.8 ms | — |
| 4 calls, sequential | 182.9 ms | 1.00x |
| 4 calls, on 4 threads | 49.6 ms | **3.69x** |

The GIL table is Chapter 8's result, still true on 3.14 (and measured at 1.08x on 3.13): four threads re-serialise into the sequential time, give or take switching costs. The free-threaded table is the same source code buying 3.69 of a possible 4, with the shortfall being thread start-up, join, and the shared allocator's coordination, and nothing else, because this workload shares no objects. Chapter 96 measures what happens when it does.

**The cross-build observation, stated with its caveat.**
The two "one call" rows, 51.1 ms against 45.8 ms, differ by about 10% *in the free-threaded build's favour*. This is a cross-build comparison, which this book's harness treats as invalid for ranking (Chapter 85), and the flag that differs, `Py_GIL_DISABLED`, is the subject itself; every other dispatch-critical flag matches. So the honest statement is: on this allocation-heavy arithmetic workload, the free-threaded build's machinery did not cost single-threaded time, it saved some, most plausibly in the allocator (Chapter 95). PEP 779's ~10% single-threaded overhead is a **suite average** on pyperformance; per-workload deltas point both ways, and Chapter 97 dissects where they come from. Neither number transplants; measure your workload.

**Book I**'s side of the shared system has run its threads in parallel since its first chapter, and the asymmetry between the two languages' halves of the design, C++ threads for the hot path, Python processes for the orchestration, was priced around exactly the 1.06x table. The 3.69x table is the first time in the series that the Python half can renegotiate that design, and Chapter 100 does the renegotiation with numbers.

---

## 93.4 Edges and failure modes

**The build can re-serialise itself without telling you loudly.**
On a free-threaded build, `PYTHON_GIL=1` or `-X gil=1` forces the GIL on; importing an extension module that does not declare free-threaded support (`Py_mod_gil` slot) re-enables it for the whole process, with a `RuntimeWarning`. A deployment that quietly imports one legacy wheel gets the old scaling and keeps the new overheads. Check `sys._is_gil_enabled()` *after* imports, not at startup.

**The `t` ABI is a separate wheel universe.**
`cp314t` wheels are distinct artifacts (Chapter 82's flags made this an import error rather than a crash), so an environment is only as free-threaded as its least-ported dependency. This is the adoption bottleneck Chapter 82 flagged, and the ecosystem's coverage improves monthly; pin and verify rather than assume.

**Scaling is a property of the workload, not the build.**
This chapter's 3.69x shares nothing between threads. Threads that hammer one shared dict, one hot object's refcount, or one lock will serialise on that object's coordination instead of the GIL (Chapters 94 and 96 measure both), and can come out *slower* than the GIL build. The free-threaded build removes the global bottleneck; it does not forbid you from building your own.

**Single-threaded cost is workload-dependent in both directions.** §93.3.
This chapter measured -10%; PEP 779's suite average is ~10% the other way on 3.14, down from ~40% on 3.13, whose free-threaded build also disabled the specializing interpreter (Chapter 97). Do not size a migration on either number; size it on your own `one call` row.

**I/O-bound threading was never the GIL's victim, and does not become faster.**
Threads that wait on sockets released the GIL all along (Deep E); their scaling was already real. The free-threaded build changes CPU-bound threading only, and `asyncio` (Deep H) remains the right tool where the concurrency is waiting, not computing.

**Daemon threads, `join`, `Thread` lifecycle: unchanged.**
The API surface is deliberately identical, which is the trap: nothing in the *code* signals which build it needs. State the requirement in deployment configuration, and assert it, because the same program is parallel on one build and sequential on the other with no other observable difference.

**And the GIL never protected compound operations.** §93.1.
The volume will not repeat this again: every unlocked check-then-act that "worked" under the GIL was a race with favourable odds (Chapter 46). Chapter 99 measures how the odds change, and the discipline that survives both builds is the one Deep E taught: lock compound operations, or do not share.

---

## 93.5 Connections

**Backward.**
The GIL as a release-history fact, and the honest cited-not-measured treatment this volume now supersedes, are Chapters 23, 26, and 27. Threads, locks, atomicity under the GIL, and the discipline of sharing are Deep E (Chapters 46 to 53, especially 46 and 51). Releasing the GIL at the C boundary, the pre-703 escape for native code, is Chapter 80; immortal objects, built *for* this project, are Chapter 81's measurement (and Chapter 19's `ob_refcnt` story). The ABI flags that make `cp314t` a separate universe are Chapter 82.

**Forward, through the volume this chapter opens.**
Biased and atomic reference counting, Chapter 94. The thread-aware allocator and the stop-the-world collector, Chapter 95. Per-object locks and what container atomicity costs under contention, Chapter 96. The specializing interpreter without its one-thread assumption, and where single-threaded overhead lives, Chapter 97. Subinterpreters and PEP 734, Chapter 98. Writing code that is correct on both builds, Chapter 99. Choosing between threads, subinterpreters, processes, and `asyncio` with a measured table, Chapter 100, which closes the volume.

**Across books.**
This volume is where Book II's concurrency model converges with **Book I**'s. C++ has been free-threaded since before Python existed, and every mechanism in §93.2's table has a C++ cousin: atomic refcounts are `shared_ptr`'s control block, per-object locks are fine-grained locking, QSBR is hazard-pointer territory. The difference is that C++ made the programmer pay these costs explicitly from day one, and CPython is retrofitting them under an unchanged API, which is why the retrofit took a PEP, three releases, and a compatibility story this volume keeps returning to.

---

## 93.6 Exercises

**1. Detect everything.** Write the four-line function that reports build (`Py_GIL_DISABLED`), ABI (`abiflags`), runtime state (`sys._is_gil_enabled()`), and whether any imported extension re-enabled the GIL. Run it on every interpreter you have.

**2. Reproduce the headline.** Run `bench_thread_scaling.py` on a GIL and a free-threaded build. Report both within-build tables, then vary the thread count through 2, 4, 8, and your core count, and plot scaling against threads on the t-build. Identify where it bends and hypothesise why.

**3. Break the scaling.** Modify the benchmark so all four threads append to one shared list. Measure the scaling factor's change on the free-threaded build and explain it in terms of §93.2's table (the answer is Chapter 96's subject; predict it before reading).

**4. The silent re-serialisation.** Build a tiny extension (or find a legacy wheel) without free-threaded support, import it on the t-build, and capture the `RuntimeWarning` and the flipped `sys._is_gil_enabled()`. State the deployment check that would have caught it.

**5. The I/O control.** Replace the CPU-bound work with a 50 ms `socket`/`sleep` wait and rerun both builds. Show that the GIL build scales fine and the t-build changes nothing, and state precisely which workloads the free-threaded build helps.

**6. The design question.** PEP 703 chose to preserve per-operation container atomicity (§93.1) at the cost of a lock in every list and dict, when a "you lock it or you lose it" model, C++'s model, would have made the fast path faster. Argue the choice: what the installed base of threaded Python would have done under the C++ model, why "your program was correct before iff it is correct now" was made a design invariant, and what that invariant cost (Chapter 96 has the number). Then argue the opposite side, using Chapter 46's point that unlocked compound operations were already broken, so the corpus being protected is partly a corpus of latent bugs.

---

## 93.7 Summary and cross-references

- **The free-threaded build is a separate build** (`Py_GIL_DISABLED`, `abiflags 't'`, its own wheels), not a switch; `sys._is_gil_enabled()` reports the runtime state, which imports can silently change.
- **The headline, measured on 3.14.6 both builds**: four CPU-bound threads buy **1.06x** on the GIL build and **3.69x** on the free-threaded build, from identical source code.
- **On this workload the t-build's single-threaded row was ~10% faster**, against PEP 779's ~10% suite-average overhead: per-workload deltas point both ways; measure, never transplant.
- **The API and the discipline are unchanged**: locked code ports untouched; single container operations remain atomic (by per-object locks now, not the GIL); compound operations were never protected on any build.
- **The GIL was one lock doing five jobs**, and the volume's chapters are its five replacements: biased refcounting (94), thread-aware memory (95), per-object locks (96), thread-safe specialization (97), plus the escape that refuses all five, subinterpreters (98).
- **Scaling is the workload's property**: share nothing and approach the core count; hammer one object and serialise on its lock instead of the GIL.
- **I/O threading was never the GIL's victim**; the free-threaded build changes CPU-bound threading only.

**Cross-references.** The release story → Chapters 23, 26, 27. Threads and locks → Deep E (Chapters 46, 49, 51). Releasing the GIL at the boundary → Chapter 80. Immortality → Chapter 81. The `t` ABI → Chapter 82. Refcounting without the GIL → Chapter 94. Memory → Chapter 95. Container locks → Chapter 96. The interpreter → Chapter 97. Subinterpreters → Chapter 98. Correctness → Chapter 99. The choice → Chapter 100.
