# Chapter 85: Memory Debugging with `tracemalloc`

A long-running service leaks memory, its resident set grows hour by hour until the process is killed, and the
usual tools tell you *that* it is growing but not *where* the memory is allocated. `tracemalloc` answers the
"where": it records the *allocation site* (a full traceback) for every allocation, so a snapshot lists the top
allocators by line, and comparing two snapshots taken at different times tells you *what grew between them*, the
leak, pinpointed to the exact line. It is the memory analogue of the profiler (Chapter 51), and it shares the
profiler's defining property: it is a *diagnose-then-disable* tool, not a production setting. Enabling it hooks
*every* allocation to record its traceback, so allocation-heavy code runs **7.7x** slower while it is on. You
enable it to find the leak, read the top growers, fix it, and turn it off, never ship with it running.

This chapter closes **Deep O** with `tracemalloc`, the memory-debugging tool behind every memory measurement in
this book: how it locates allocations and diffs snapshots to find leaks, and why its overhead confines it to
debugging. It is the observability counterpart to profiling: profiling finds where *time* goes, `tracemalloc`
finds where *memory* goes.

## Section index

- **85.1** Finding the allocation site
- **85.2** Diffing snapshots to find leaks
- **85.3** Measurement: the tracing overhead
- **85.4** Edges and failure modes
- **85.5** Connections
- **85.6** Exercises
- **85.7** Summary and cross-references

Listings live under `code/ch085/` and are re-executed by `make verify` on both interpreters.

---

## 85.1 Finding the allocation site

```python
# code/ch085/l01_tracemalloc.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
  tracing enabled : True
--- compare_to finds what grew between the snapshots ---
  top grower is in this file : True
  it is the build() line     : True
  the structure built        : 1000 lists of 100 ints
--- current traced memory is nonzero while data is alive ---
  current > 0 : True
  peak >= current : True
  tracing after stop : False
  (enable to diagnose a leak, read the top growers, then disable)
```

`tracemalloc.start()` begins recording; from then on, every allocation carries its allocation *traceback*. A
`take_snapshot()` captures the current state, and `snapshot.statistics("lineno")` (or `"traceback"`) ranks
allocations by the line (or full stack) that made them, so you see *which code* holds the memory, not just how
much. The listing allocates a known structure in `build()` and confirms `tracemalloc` attributes it correctly:
the top grower is in this file, on the `build()` allocation line. `get_traced_memory()` returns the current and
peak traced bytes. And `stop()` disables tracing (`is_tracing()` is then `False`), returning the program to full
speed.

The listing reports *deterministic qualitative* facts, which line allocated, how many objects, rather than exact
byte counts, because a `tracemalloc` snapshot includes the interpreter's *internal* allocations, which vary
slightly by version and run. In real debugging you read the *ranked* output (this line is the top allocator),
which is stable and actionable, not a precise byte total.

---

## 85.2 Diffing snapshots to find leaks

The single most useful `tracemalloc` technique is the **snapshot diff**, and it is how you find a leak. Take a
snapshot at a *baseline* (after startup, or at the start of a request), let the suspected-leaking work run, take
a *second* snapshot, and call `after.compare_to(before, "lineno")`. The result is a list of `StatisticDiff`
entries sorted by *how much each line's allocation grew*, `size_diff` and `count_diff`, so the line at the top is
the one that allocated the most *new, still-live* memory between the two snapshots. That is the leak: memory
allocated and not freed.

This works because a leak is, by definition, *growth that does not go away*. A single snapshot shows where memory
*is*, which includes legitimate long-lived data; the *diff* isolates what *grew*, which is what leaks. Run the
suspected operation many times between snapshots to amplify the signal (a small per-iteration leak becomes a
large diff), and diff repeatedly across a long run to watch the leak accumulate at a specific line. The listing's
`compare_to` finds the `build()` line as the top grower, exactly the leak-localization you would do in
production: "between these two points, *this line* allocated memory that is still alive".

The rule: **to find a leak, diff two snapshots around the suspected work and read the top grower.** `tracemalloc`
turns "the process is growing" into "*this line* is growing", which is the difference between guessing and
fixing. Combine it with `get_traced_memory()` to confirm the total is rising, and `statistics("traceback")` (full
stacks) when the allocating line is called from many places and you need the *path*, not just the line.

---

## 85.3 Measurement: the tracing overhead

**Methodology.** `code/ch085/bench_tracemalloc.py`. An allocation-heavy loop (10,000 small list allocations) with
`tracemalloc` off versus on. `min` per run. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| allocation-heavy loop | min per run | ratio |
|---|---|---|
| `tracemalloc` off | **864 us** | 1.00x |
| `tracemalloc` on | **6,685 us** | **7.7x** |

With `tracemalloc` enabled, the allocation-heavy loop runs **7.7x** slower, because *every* allocation now also
records its traceback (capturing the call stack and storing it keyed by the allocation). The overhead scales with
*allocation rate*, code that allocates little is barely affected, code that allocates in a tight loop is hit
hard, which is why the worst-affected code is often exactly the code you are debugging.

The rule, identical in shape to the profiler of Chapter 51: **`tracemalloc` is a diagnose-then-disable tool.**
Enable it, reproduce the memory problem, read the top allocators (or diff snapshots), fix the leak, and disable
it, do not leave it running in production, where the 7.7x allocation overhead is unacceptable. For *production*
memory observability you use lighter signals (RSS from the OS, `gc` stats, periodic sampling) to detect *that*
memory is growing, then reproduce and use `tracemalloc` in a *debugging* run to find *where*. You can reduce its
cost by limiting the traceback depth (`tracemalloc.start(1)` records only the immediate frame) when the top line
is enough. As with profiling, the tool that pinpoints the problem is too heavy to run always, so you run it
deliberately, and this is the last of Deep O's recurring lesson, the diagnostic that finds the fault costs more
than the fault-free path, so you pay it only when diagnosing.

---

## 85.4 Edges and failure modes

**Leaving `tracemalloc` on in production.** §85.3. 7.7x allocation overhead. Enable it to diagnose, then disable;
do not ship with it running.

**Reading a single snapshot for a leak.** §85.2. A single snapshot shows all live memory, including legitimate
long-lived data. Use `compare_to` (a diff) to isolate *growth*, which is what leaks.

**Trusting exact byte counts.** §85.1. Snapshots include internal allocations that vary by version/run. Read the
*ranking* (which line dominates), not a precise total.

**Deep tracebacks are expensive.** The default records a shallow traceback; `tracemalloc.start(n)` sets the depth.
Deeper tracebacks cost more memory and time; use the shallowest depth that identifies the site.

**Missing the leak because it is in C.** `tracemalloc` traces *Python* allocations; memory allocated by a C
extension (NumPy buffers, a database driver) outside the Python allocator may not appear. For those, use the
extension's own tools or OS-level memory profiling.

**Confusing a leak with a cache or fragmentation.** Growth can be a legitimate unbounded cache (Chapter 34's
unbounded `@cache`), a large legitimate structure, or allocator fragmentation, not a "leak" per se. `tracemalloc`
tells you *where* the memory is; deciding whether it *should* be there is your judgment.

---

## 85.5 Connections

**Backward.** `tracemalloc` is the tool behind every memory benchmark in this book (Chapters 9, 33, 37, 39, 56,
61, and more), where it gave *deterministic* peak-memory numbers. The profiler it parallels (find where *time*
goes) is Chapter 51. The allocations it traces are the object model and PyMalloc of Chapter 4 and Deep A/B. The
unbounded-cache growth it can reveal is Chapter 34.

**Forward.** OS-level and production memory observability (RSS, cgroup limits, sampling profilers) are Deep O/Deep
U operational topics. The garbage collector's view of memory (`gc` stats, reference cycles) is Chapters 3 and 30.
C-extension memory profiling (NumPy, native libraries) is Deep T.

**Across books.** `tracemalloc` is how Book II localizes the memory problems that would otherwise crash a
**Book III** service. A **Book III** pipeline whose resident set grows is diagnosed by diffing `tracemalloc`
snapshots around a batch to find the leaking line, an unbounded cache, a retained reference, a growing buffer,
then fixed and the tool disabled, so production runs at full speed with only lightweight RSS monitoring. The
§85.3 overhead is why the pinpointing tool runs in a debugging session, not in the hot serving path, the same
profile-to-find, benchmark-to-measure discipline **Deep U** applies to every performance and memory
investigation.

---

## 85.6 Exercises

**1. Locate an allocation.** Reproduce §85.1: allocate a structure, snapshot, and confirm `tracemalloc` names the
allocating line as the top site. Explain what information a single snapshot gives.

**2. Find a leak by diff.** Write code that leaks (appends to a module-level list each call), snapshot before and
after many calls, and use `compare_to` to identify the leaking line by its growth. Explain why the diff, not a
single snapshot, finds the leak.

**3. Measure the overhead.** Run §85.3's benchmark and confirm `tracemalloc` slows allocation-heavy code several-
fold. Then reduce the traceback depth and show the overhead drops. Explain what the overhead pays for.

**4. Distinguish leak from cache.** Diff snapshots around code that grows an unbounded `@cache` (Chapter 34) and
show `tracemalloc` points at the cache. Discuss whether it is a "leak" and how you would decide.

**5. The design question.** `tracemalloc` finds where memory goes but costs 7.7x while enabled. Argue how to use
it in a production investigation. Your answer must use the §85.3 overhead, the §85.2 diff technique, and the
split between lightweight production monitoring and heavy on-demand diagnosis.

---

## 85.7 Summary and cross-references

- **`tracemalloc`** records the **allocation site** of every allocation, so a snapshot ranks allocators by line
  and **`compare_to`** (a snapshot **diff**) isolates what **grew**, the leak, pinpointed to the line.
- **To find a leak, diff two snapshots** around the suspected work and read the top grower; a single snapshot
  shows all live memory (including legitimate long-lived data).
- **Measured:** `tracemalloc` adds **7.7x** overhead on allocation-heavy code (it hooks every allocation), so it
  is a **diagnose-then-disable** tool, enable to find the leak, then turn it off; never ship with it on.
- **Edges:** read the ranking, not exact byte counts (internal allocations vary); it traces Python, not C
  allocations; growth may be a cache or fragmentation, not a leak.

**Cross-references.** Memory benchmarks throughout → Chapters 9, 33, 37, 39, 56, 61. Profiling (time) → Chapter
51. Object model/PyMalloc → Chapter 4, Deep A/B. Unbounded cache growth → Chapter 34. GC and cycles → Chapters 3,
30. Production monitoring → Deep U. C-extension memory → Deep T.
