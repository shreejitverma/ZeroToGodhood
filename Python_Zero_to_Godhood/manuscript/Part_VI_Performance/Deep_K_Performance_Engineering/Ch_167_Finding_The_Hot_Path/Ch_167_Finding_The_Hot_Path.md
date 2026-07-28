# Chapter 86: Finding the Hot Path

Chapter 85 established how to measure one operation honestly. This chapter is about the question that comes first: **which operation**.

The instinct, when a program is slow, is to look for the function that runs most often. That instinct is wrong often enough to be dangerous, and a profile contains the evidence in three columns that answer three different questions. `ncalls` says how often a function ran. `tottime` says how long was spent *inside* it, excluding what it called. `cumtime` says how long was spent inside it *and everything it called*. Only the last two are about time, and they are for different purposes: **cumtime chooses the subtree, tottime chooses the line, and ncalls is not a proxy for either**.

Then a harder problem, and the one this chapter exists for. A deterministic profiler hooks every call and every return, so the cost of observing is proportional to how many calls a piece of code makes, and that cost is charged to the code being observed. The profiler therefore does not merely run the program slower; it runs it slower **unevenly**. Measured here: two halves of a workload that cost within 2% of each other unprofiled come out **82% against 18%** under `cProfile`, and the half the profiler names as dominant is in truth the *smaller* of the two.

**This is a Deep K chapter.**
`cProfile`'s mechanics are Chapter 51's subject; this chapter is about reading a profile without being misled by it.

## Section index

- **86.1** Three columns, three questions
- **86.2** Reading a profile without being misled
- **86.3** Measurement: the profiler re-ranks the program
- **86.4** Edges and failure modes
- **86.5** Connections
- **86.6** Exercises
- **86.7** Summary and cross-references

Listings live under `code/ch167/` and are re-executed by `make verify` on both verification interpreters.

---

## 86.1 Three columns, three questions

```python
# code/ch167/l01_finding_the_hot_path.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- how often each function ran ---
  workload   ncalls =     1
  wrapper    ncalls =     1
  hot_leaf   ncalls =     1
  cheap      ncalls =  1000
--- three orderings of the same profile ---
  by ncalls  : ['cheap', 'hot_leaf', 'workload', 'wrapper']
  by tottime : ['hot_leaf', 'workload', 'cheap', 'wrapper']
  by cumtime : ['workload', 'wrapper', 'hot_leaf', 'cheap']
--- and they disagree, which is the point ---
  most-called function        : cheap
  function holding the time   : hot_leaf
  they are different          : True
  optimising the most-called one would change nothing measurable
--- tottime excludes callees; cumtime includes them ---
  wrapper's own body is nearly free  : True
  but its cumtime contains the leaf  : True
  so cumtime says WHERE to look, tottime says WHAT to change
--- how much of the program is in one function ---
  hot_leaf's share of measured time is above 90% : True
  number of functions holding the first 90%      : 1
--- the rule ---
  read cumtime to choose the subtree, tottime to choose the line, and never
  read ncalls as a proxy for either
```

The listing reports **ranks and call counts**, which are deterministic, rather than times, which are not. That is the same discipline the chapter argues for when reading a real profile: the numbers move between runs, the ordering and the structure do not.

**The three orderings disagree by construction.**
`cheap` is called a thousand times and does almost nothing. `hot_leaf` is called once and does all the work. Ranking by `ncalls` puts `cheap` first; ranking by `tottime` puts `hot_leaf` first. A morning spent making `cheap` twice as fast would change nothing measurable, and the profile said so on the line the reader skipped.

**`cumtime` and `tottime` answer different questions, and both are needed.**
`wrapper`'s own body is a single `return`, so its `tottime` is negligible, but its `cumtime` contains all of `hot_leaf`. Reading only `tottime` you would never look at `wrapper`; reading only `cumtime` you would see `workload` and `wrapper` at the top and conclude, wrongly, that they need changing.

The working procedure follows directly:

1. **Sort by `cumtime`** and walk down from the top. The first entry is always `main` or the entry point; keep descending until `cumtime` drops sharply. That fall marks the boundary of the subtree that holds the time.
2. **Sort by `tottime`** and look inside that subtree. The top entry there is the function whose *own body* you would have to change.
3. **Ignore `ncalls` for ranking.** Use it for a different purpose: to check whether a function is called far more often than you expected, which is a design question ("why is this in a loop?") rather than a speed question.

**The 90% concentration is normal, and it is the reason profiling works at all.**
In this program one function holds over 90% of the measured time. Real programs are less extreme but not much: performance work is viable precisely because time concentrates. If it were spread evenly over four hundred functions there would be nothing to optimise, only a rewrite.

---

## 86.2 Reading a profile without being misled

**The profiler changes the program.** §86.3 measures how much and in which direction. The consequences for how you read the output are concrete.

**Do not compare two candidates that are close.**
If the top two entries are within a factor of two, the profiler's own distortion is large enough to have reordered them. Take both candidates out of the profile and measure each with a focused benchmark (Chapter 85). A profile is a search tool, not a scale.

**Watch for the function that is fast but called from everywhere.**
A `tottime` of 8% spread over 40,000 calls from twelve call sites is usually not an invitation to optimise the function; it is an invitation to ask why it is called 40,000 times. `pstats`' `print_callers()` answers that, and the fix is nearly always at the call site.

**Distinguish "slow" from "waiting".**
`cProfile` measures wall time by default, so a function blocked on a socket or a lock appears expensive. That is true and usually not actionable in the same way: the fix is concurrency (Deep E) or an architecture change, not a faster function body. Profiling with `time.process_time` as the timer separates CPU from wall, and the difference between the two profiles is the waiting.

**Beware the aggregate that hides a bimodal distribution.**
A profile reports totals. A function called 1,000 times, of which 998 return in a microsecond and 2 take a second, looks identical in aggregate to one that always takes two milliseconds. The first is a cache miss or a slow path and is fixed differently. When the `ncalls`-to-`tottime` ratio looks implausible for the work involved, instrument the function directly.

**Profile the workload you care about.**
This restates Chapter 85's fifth failure mode at program scale. A profile of a test suite tells you about a test suite. A profile of a warm cache tells you about a warm cache. Where the two differ, they differ enormously.

**And the alternative worth knowing about.**
A **sampling** profiler interrupts the program periodically and records the stack, so its cost is proportional to the sampling rate rather than to the call count. That removes exactly the distortion §86.3 measures, at the price of statistical rather than exact attribution and of missing functions that never appear in a sample. On modern CPython, `sys.monitoring` (PEP 669, Chapter 22) is the low-overhead substrate that makes such tools cheap; the same mechanism this book uses in Chapter 76 to count instructions.

---

## 86.3 Measurement: the profiler re-ranks the program

**Methodology.** `code/ch167/bench_profiler_distortion.py`.
A workload with two halves, tuned to cost about the same when nothing is watching: 200,000 calls to a trivial function against one call doing an equivalent amount of arithmetic in a loop. Each half is first timed alone with no profiler (`min` of 9 runs) to establish the true split, then both run under `cProfile` and the split is recomputed from `tottime`, with the trivial function's time attributed to the half that calls it.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| half | unprofiled | true share | profiled `tottime` | profiled share |
|---|---|---|---|---|
| call-heavy (200,000 calls) | 4.9 ms | **49%** | 22.2 ms | **82%** |
| compute-heavy (one loop) | 5.1 ms | **51%** | 4.9 ms | **18%** |

The profiler moved the call-heavy half's apparent share by **+33 percentage points**. And the direction is the damaging one: unprofiled, the compute-heavy half is fractionally the *larger* of the two, so **the profile names the smaller half as dominant**.

**Why it happens, precisely.**
`cProfile` installs a C-level hook on every call and every return. The hook's cost is charged to the frame that triggered it, so a function making 200,000 calls absorbs 200,000 hook invocations while a function running a 200,000-iteration arithmetic loop absorbs one. The compute-heavy row confirms this: its profiled `tottime` (4.9 ms) is essentially its unprofiled time (5.1 ms), because there were no calls to hook. The entire 17 ms of inflation landed on the other half.

**This is not an argument against profiling.**
It is an argument for what a profile is *for*. The distortion is systematic and in a known direction, so a profile remains reliable for finding a subtree that holds most of the time, which is usually a factor of ten or more above its neighbours and cannot be reordered by a factor of four. It is unreliable for choosing between two functions that are close, which is exactly when people reach for it.

**The procedure that follows.**
Profile to find the subtree. Then take the candidate out of the program and measure it with a benchmark that has no per-call hook, using Chapter 85's methodology. If the profile and the focused benchmark disagree about which of two candidates matters, **the focused benchmark is right**, and the disagreement is this table.
**Book I**'s profilers have the same property for the same reason: an instrumenting profiler charges its instrumentation to the instrumented code, and a sampling profiler does not. The shared order-book system is profiled by sampling on both sides precisely because the call-frequency profile of the C++ and Python halves differ so much that an instrumenting profile would compare them unfairly.

---

## 86.4 Edges and failure modes

**`cProfile` cannot see inside a C function.** A call into `sorted`, `re.match`, or a NumPy ufunc appears as one entry with its whole cost attributed to it, and nothing below. That is often fine and occasionally hides the real work entirely.

**Recursive functions report `ncalls` as `total/primitive`.**
`5/1` means five calls of which one was not recursive. `cumtime` for a recursive function is not the sum of its invocations; `pstats` corrects for the recursion, and reading it as a plain total will mislead.

**The profiler's own frames are excluded, its overhead is not.** §86.3.
`pstats` will not show you `cProfile`'s hook, but the hook's time is inside the numbers you are reading.

**Profiling multi-threaded code needs care.**
`cProfile` profiles the thread that enabled it. Other threads run unprofiled, and their contention shows up as inflated times in the profiled thread. Use `threading.setprofile`, or profile one thread's work in isolation.

**`tottime` on a generator is charged where it resumes, not where it is defined.**
A generator's body time accumulates against the generator function, but it is *spent* wherever the consumer pulled from it. A profile of a pipeline of generators reads oddly for this reason, and the fix is to read `cumtime` at the consumer.

**Sorting by `percall` is almost always a mistake.**
It ranks by cost per invocation, which surfaces functions called twice. Interesting for a design review, useless for finding where the time went.

**Do not leave `cProfile` enabled in production to "get real numbers".** §86.3.
The numbers you get will be systematically wrong in the direction of call-heavy code, and the service will be several times slower. Sample instead.

---

## 86.5 Connections

**Backward.**
How to measure a candidate once you have found it is Chapter 85. `cProfile` and `pstats` mechanics, and the magnitude of the overhead, are Chapter 51 (Deep S). `sys.monitoring` as a low-overhead observation substrate is Chapter 22 and is used in Chapter 76. Why time concentrates in a few functions at all, and what the per-element cost model is, are Chapters 76 to 78.

**Forward.**
Once the hot path is found, the first question is whether its complexity is wrong rather than its constant, which is Chapter 87. Container choice as the most common complexity fix is Chapter 88. Memory as a performance problem, which a time profile does not show at all, is Chapter 89. When to stop is Chapter 92.

**Across books.**
The reason the shared system is profiled by sampling on both sides is §86.3's result. **Book I**'s half makes very few calls per unit of work and Python's makes many, so an instrumenting profiler would report the Python half as dominant regardless of the truth. Comparing across a language boundary requires a measurement whose cost does not depend on the calling convention, and sampling is the only one available.

---

## 86.6 Exercises

**1. Make the orderings disagree.** Reproduce §86.1 with your own workload. Construct a case where `ncalls`, `tottime`, and `cumtime` give three different first entries, and explain each.

**2. Walk a real profile.** Profile a program you maintain. Sort by `cumtime`, find the point where it falls sharply, then sort by `tottime` within that subtree. Report what you would change and why the other candidates are not it.

**3. Reproduce the re-ranking.** Reproduce §86.3. Then tune the two halves until the profiler and the truth agree, and report how far apart the halves had to be before the profile became reliable.

**4. Separate slow from waiting.** Profile a program that does I/O, once with the default timer and once with `time.process_time`. Explain every function whose rank changes.

**5. Find the bimodal function.** Instrument a function whose aggregate profile looks unremarkable but whose per-call distribution is bimodal (a cache with misses is the easiest to build). Show what the profile hides and what a histogram reveals.

**6. The design question.** `cProfile` charges its hook to the observed frame, which produces the distortion in §86.3. Argue why a deterministic profiler cannot easily do better: what it would take to subtract the hook's cost accurately, why the subtraction is not simply "hook cost times call count", and what a sampling profiler gives up in exchange for not having the problem.

---

## 86.7 Summary and cross-references

- A profile has **three columns answering three questions**: `ncalls` (how often), `tottime` (time in the body, excluding callees), `cumtime` (body plus callees). **`cumtime` chooses the subtree, `tottime` chooses the line, `ncalls` is not a proxy for either.**
- Demonstrated on a workload built so the orderings disagree: the most-called function is `cheap`, the function holding the time is `hot_leaf`, and optimising the first would change nothing measurable.
- **The procedure:** sort by `cumtime` and descend until it falls sharply; sort by `tottime` inside that subtree; read `ncalls` as a design signal ("why is this called 40,000 times?"), not a speed signal.
- **The profiler re-ranks the program.** Measured: two halves within 2% of each other unprofiled come out **82% / 18%** under `cProfile`, a **+33 percentage-point** shift, and the profile names the half that is actually the *smaller* one. The cause is that the per-call hook is charged to the frame that triggered it, so cost scales with call count; the compute-heavy half's profiled time equalled its unprofiled time almost exactly.
- **So a profile is a search tool, not a scale.** Reliable for finding a subtree that dominates by a factor of ten; unreliable for choosing between two close candidates, which is exactly when it is reached for. When a profile and a focused benchmark disagree, the benchmark is right.
- **Sampling profilers do not have this problem**, at the price of statistical attribution; `sys.monitoring` (PEP 669) is the modern low-overhead substrate.
- **Edges:** C functions are opaque; recursive `ncalls` is `total/primitive`; `cProfile` profiles one thread; generator time is charged where it resumes; sorting by `percall` surfaces rarely-called functions; wall-clock profiling conflates slow with waiting.

**Cross-references.** Measuring a candidate → Chapter 85. `cProfile`/`pstats` mechanics and overhead → Chapter 51. `sys.monitoring` → Chapter 22, used in Chapter 76. Per-element cost models → Chapters 76 to 78. Complexity over constants → Chapter 87. Container choice → Chapter 88. Memory → Chapter 89. When to stop → Chapter 92.
