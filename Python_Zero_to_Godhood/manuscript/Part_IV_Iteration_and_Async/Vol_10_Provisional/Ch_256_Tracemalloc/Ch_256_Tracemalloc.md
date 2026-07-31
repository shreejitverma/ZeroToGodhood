# Chapter 256: Tracemalloc

## The constraint

"Why is this process using so much memory?" is one of the hardest questions to answer about a running Python program, and for most of the language's history it was nearly unanswerable *from inside Python*.
The operating system could tell you the total resident size, and that number was often alarming, but it was opaque: it told you *how much* memory was in use, never *which lines of your Python code* had allocated it.
You could guess, add manual instrumentation, or reach for external C-level tools that spoke in addresses rather than Python tracebacks - but there was no way to ask the interpreter itself, "which of my lines is responsible for this memory?"

That gap made memory problems disproportionately hard compared to time problems.
For CPU, you had profilers that attributed time to functions.
For memory, you had a single opaque total and your intuition.

The constraint Python 3.4 (2014, PEP 454) answered: **let the interpreter record, per allocation, the Python code that made it, so memory can be attributed to exact lines and localized by comparing snapshots.**

This is a two-track chapter.
The cost model - *when* memory matters, how the allocator and object layout produce it, the discipline of measuring before optimizing - is Deep Volume K's subject.
What this chapter owns is the release: the day the measurement itself became possible from inside Python.

## What shipped

`tracemalloc` hooks CPython's memory allocator and records the Python traceback behind each allocation.
You `start` it, take `snapshot`s, read per-line `statistics`, and `compare_to` two snapshots to see what a block of code allocated.
Listing 256.1 shows the workflow on today's interpreters, reporting only directions and flags (memory rose, peak at least current) so the demo is machine-independent - in a real investigation you read the actual byte counts.

Verified output (CPython 3.13.5):

```text
--- tracemalloc hooks the allocator; you can ask if it is tracing ---
  before start, is_tracing() : False
  after start,  is_tracing() : True
  start() begins recording the Python traceback behind every
  allocation. it is off by default (it has overhead) and turned on
  for the duration of an investigation
--- allocate memory and watch the traced total rise ---
  current memory rose after allocating 100k objects : True
  peak >= current (peak tracks the high-water mark)  : True
  get_traced_memory() returns (current, peak) in bytes. we report
  only the DIRECTION here so the demo is machine-independent, but in
  practice you read the actual numbers to size the problem
--- a snapshot attributes memory to the LINES that allocated it ---
  snapshot has per-line statistics : True
  the top entry is a real code location : True
  the top entry accounts for some bytes : True
  each statistic ties a byte count to a file and line, so 'what is
  using memory' becomes a ranked list of code locations - the answer
  that was impossible to get before
--- comparing two snapshots isolates what a block of code allocated ---
  compare_to() found lines that GREW between snapshots : True
  the diff shows size_diff per line - exactly what the code BETWEEN
  the two snapshots allocated. this is how you localise a leak: snap,
  run the suspect code, snap, and read what grew
--- stop() when done: tracing has overhead ---
  after stop(), is_tracing() : False
  tracing every allocation costs time and memory, so you stop it once
  the investigation is over - it is a diagnostic tool, not something
  you leave on in production
--- the constraint answered ---
  'which Python lines are using the memory?' had no answer from
  inside the language. tracemalloc (3.4) records the traceback behind
  each allocation, so snapshots and their diffs attribute bytes to
  exact code locations. Deep K says measure before optimising; this
  release made memory measurable from inside Python
```

## Why each part answers the constraint

**Tracing is an explicit, toggleable mode.**
The first block shows `is_tracing()` flipping from `False` to `True` after `start()`.
Recording the traceback behind every allocation has real overhead, so tracing is off by default and switched on for the duration of an investigation - a diagnostic mode, not an always-on cost.

**The traced total responds to allocation.**
The second block allocates 100,000 objects and confirms the traced current memory rose, with `peak` tracking the high-water mark at least as high as current.
`get_traced_memory()` returns `(current, peak)` in bytes; the listing reports only the direction to stay machine-independent, but in practice those numbers are how you *size* a problem - is it megabytes or gigabytes.

**Snapshots attribute bytes to lines.**
The third block is the capability that was previously impossible.
A `snapshot`'s per-line `statistics` tie a byte count to a specific file and line, so "what is using memory" becomes a *ranked list of code locations*.
The listing confirms the top entry is a real `.py` location accounting for real bytes.
This is the memory analogue of a CPU profiler's per-function times - the attribution that turns a mysterious total into an actionable list.

**Comparing snapshots localizes growth.**
The fourth block shows the technique that finds leaks.
Take a snapshot, run the suspect code, take another, and `compare_to` reports `size_diff` per line - exactly what the code *between* the two snapshots allocated.
The listing confirms lines that grew were detected.
This snapshot-diff workflow is how you isolate a leak to the code responsible: bracket the suspect region and read what grew.

**Stop when done.**
The fifth block shows `is_tracing()` back to `False` after `stop()`.
Because tracing every allocation costs time and memory, you turn it off once the investigation is over.
`tracemalloc` is a tool you reach for during diagnosis, not something you leave running in production.

## The two-track note

The reasoning that makes a memory measurement *actionable* - whether the memory matters, what object layout or retention is producing it, the discipline of measuring before changing anything - is Deep Volume K's subject.
`tracemalloc` is the instrument that discipline requires: without it, "reduce memory" is guesswork; with it, you can point at the lines that allocate and confirm a change actually helped.
What the timeline records is the release act: in 3.4, PEP 454 gave the interpreter the ability to attribute allocations to Python tracebacks.
The modern consequence, verified above, is that memory investigations in Python start with `tracemalloc` snapshots and diffs, the same way time investigations start with a profiler.

## Where this lands, and the close of Provisional

`tracemalloc` closed the gap that made memory problems harder than time problems: it made "which of my lines is using this memory?" a question the interpreter can answer.
Reach for it whenever memory is the concern - turn it on, snapshot before and after the suspect code, read the per-line statistics or the snapshot diff, and turn it off when done.
Report what you find in real bytes and real locations, not intuition.
Deep Volume K explains when and why memory matters and how to reason about it; this chapter is the record of the release that made it measurable from inside Python.

This closes Volume 10, Provisional.
The volume's name comes from its headline: `asyncio` shipped in 3.4 with *provisional* status (Chapter 10), an explicit admission that the API might change - and following its evolution to a stable form is the story Part IV is telling.
Around that centerpiece, 3.4 was a rich consolidation release: `singledispatch` for type-based overloading, the `statistics` module, the `contextlib` toolkit, `pathlib` and `enum` (Chapter 10), and `tracemalloc` for memory analysis.
Part IV continues with Volume 11, where `async` and `await` become native syntax and the provisional experiment becomes a permanent part of the language.
