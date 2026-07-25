# Chapter 28: PyMalloc, Arenas, Pools, and the Generational GC

Chapter 19 established that every Python value is a heap object with a 16-byte header, and it measured
the consequence: a million integers cost 38 MB. But it left a question unanswered. If Python allocates
an object for *every* intermediate value, every `a + b`, every attribute box, every tuple a function
returns, then it is calling into the memory allocator constantly, millions of times a second in a hot
loop. The system `malloc` was not designed for that. It is a general-purpose allocator tuned for
occasional allocations of varied sizes, and using it for Python's relentless churn of tiny, short-lived
objects would make allocation itself a dominant cost and fragment the heap into uselessness.

Python does not use the system `malloc` for those objects. It uses **PyMalloc**, a custom allocator
(`Objects/obmalloc.c`) built specifically for the small-object churn that dominates Python, layered on
top of a **generational garbage collector** that cleans up the cycles reference counting cannot. This
chapter is the canonical home for both. Chapter 19 introduced the object header and Chapter 3 introduced
the cyclic collector historically; this chapter is the machinery underneath them, the allocator that
makes object churn cheap and the collector that keeps it from leaking.

This chapter opens **Deep B**, the memory volume. It is the mechanism the object-model chapters
deferred to.

## Section index

- **28.1** The problem: allocating for everything
- **28.2** PyMalloc: arenas, pools, and blocks
- **28.3** The free list and size classes
- **28.4** The generational collector
- **28.5** Measurement: the cost of allocation, and the shape of the trade
- **28.6** Edges and failure modes
- **28.7** Connections
- **28.8** Exercises
- **28.9** Summary and cross-references

Listings live under `code/ch028/` and are re-executed by `make verify` on both interpreters.

---

## 28.1 The problem: allocating for everything

Reference counting (Chapter 19) frees an object the instant its count hits zero, which means Python's
memory is in constant motion: objects are created and destroyed continuously, and most of them are
small (an `int` is 28 bytes, a two-tuple is 56) and short-lived (an intermediate value that exists for
one bytecode). A single hot loop can allocate and free millions of small objects per second.

The system `malloc`/`free` is the wrong tool for that pattern. It must handle allocations of any size,
it maintains metadata to coalesce and split blocks, and it makes no assumptions about lifetime or size
distribution. For Python's workload, most of that generality is wasted work, and the per-call overhead,
paid millions of times, would dominate. Worse, interleaving millions of tiny allocations and frees
through a general allocator fragments the heap: free space ends up in pieces too small to reuse.

PyMalloc exists to make the common case, a small object allocated and soon freed, close to free. It
does this by requesting memory from the OS in large chunks and managing the small objects itself, in a
structure tuned for exactly Python's churn.

---

## 28.2 PyMalloc: arenas, pools, and blocks

PyMalloc handles every allocation of **512 bytes or less** (larger objects go straight to the system
allocator). It organizes memory in a three-level hierarchy, which the listing lays out:

```python
# code/ch028/l01_pymalloc.py
```

Verified output (CPython 3.13.5):

```text
--- the arena hierarchy (sizes from sys._debugmallocstats) ---
  ARENA  (1 MB)  requested from the OS with mmap
    POOL (16 KB) one size class per pool
      BLOCK      fixed size for the pool's class; the unit handed out
```

The listing also states the threshold: allocations up to **512 bytes**, in **32 size classes**, go
through PyMalloc pools; larger ones go to the system `malloc` directly. An **arena** is a large chunk
(1 MB) requested from the OS, the unit at which PyMalloc talks to the
kernel. Each arena is divided into **pools** (16 KB each), and each pool serves *one size class*: a
pool for 32-byte blocks holds only 32-byte blocks, a pool for 64-byte blocks only those. A pool is
divided into fixed-size **blocks**, and a block is the unit handed out to satisfy an allocation. When
Python asks for a 30-byte object, PyMalloc rounds up to the next size class (32 bytes), finds a pool for
that class, and returns a block from it.

> **Version note, verified.** The arena size is **1 MB** and the pool size **16 KB** on both
> verification interpreters, read via `sys._debugmallocstats()`. Earlier CPython used a 256 KB arena and
> a 4 KB pool; the exact release each changed is in the verification queue. (This corrects a figure the
> original appendices had wrong, per the Phase 0 audit.)

The reclamation flows back up the hierarchy: a freed block returns to its pool's free list, an
all-empty pool returns to its arena, and a fully-empty arena can be released back to the OS. That last
step is why a program's memory can shrink after a large transient allocation, but only if an entire
1 MB arena becomes empty, which is why memory sometimes stays high after a spike (a few live objects
scattered across an arena keep the whole megabyte pinned).

---

## 28.3 The free list and size classes

The mechanism that makes allocation fast is the **free list**. When a block is freed, PyMalloc does not
return it to the OS or search a data structure; it pushes the block onto a per-size-class free list. The
next allocation of that size pops the block straight off:

```text
--- pymalloc reuses a freed block immediately (the free list) ---
  two same-size allocations reused the block: True
--- object sizes step through the size classes ---
  getsizeof(bytes(  8)) = 41
  getsizeof(bytes( 32)) = 65
  getsizeof(bytes( 64)) = 97
  getsizeof(bytes(512)) = 545
  getsizeof(bytes(513)) = 546
```

Two same-size allocations reused the *same* block: the first `bytes(24)` was freed, its block went on
the free list, and the second `bytes(24)` popped it back off, so `id()` matched. This is the whole
performance story. Allocating a small object that has a free block available is a list pop, no system
call, no search, no coalescing. Freeing it is a list push. For the churn of Chapter 19's per-operation
objects, this is what keeps allocation off the critical path.

There are **32 size classes** up to 512 bytes, spaced 16 bytes apart (16, 32, 48, ..., 512), so an
allocation is rounded up to at most 16 bytes of internal waste. `bytes(513)` at 546 bytes has crossed
the threshold and is a system-`malloc` allocation, not a PyMalloc one. The size-class rounding is why
`getsizeof` steps in chunks rather than tracking the request byte-for-byte.

---

## 28.4 The generational collector

PyMalloc allocates and reference counting frees, but reference counting cannot free a *cycle* (Chapter
3). The **generational cyclic collector** handles what refcounting cannot, and its structure is the
weak generational hypothesis made concrete: most objects die young, so scan the young frequently and
the old rarely.

```python
# code/ch028/l02_generational_gc.py
```

Verified output (CPython 3.13.5):

```text
--- a survivor is promoted through the generations ---
  freshly created: generation 0
  after a gen-0 collection: generation 1
  after a gen-1 collection: generation 2
--- the thresholds that trigger each generation ---
  gen-0 collected when (allocations - deallocations) exceeds 2000
  gen-1 collected after 10 gen-0 collections
  gen-2 collected after 10 gen-1 collections
```

A tracked object starts in **generation 0**. Each collection it *survives* promotes it to an older
generation, and the listing shows a survivor moving 0, 1, 2 across three collections. The thresholds
`(2000, 10, 10)` govern the cadence: generation 0 is collected when net allocations since the last
collection exceed 2000, generation 1 after 10 generation-0 collections, generation 2 after 10
generation-1 collections. So generation 0 is scanned constantly and cheaply, because it holds only the
young objects allocated since the last scan, most of which are already dead; generation 2 holds the
long-lived heap and is scanned rarely, because scanning it is expensive and it rarely contains new
garbage.

This is why the tuning levers of Chapter 3 work the way they do. `gc.freeze()` moves everything
currently alive into a permanent generation that is *never* scanned, which is Chapter 3's "building
long-lived state" case (§3.5) made structural: freezing after startup removes the entire startup heap
from every future generation-2 scan. And the finding from Chapter 3, that disabling the collector helps
when building survivors and hurts when churning cycles, is exactly this structure seen from the outside:
survivors are the objects that would be promoted and rescanned for nothing, cycles are the garbage only
a collection reclaims.

---

## 28.5 Measurement: the cost of allocation, and the shape of the trade

**Methodology.** `code/ch028/bench_allocation.py`, through `_harness/bench.py`. Repeatedly allocating a
small object (64 bytes, PyMalloc's free-list path) versus a large one (2 KB, the system `malloc`). `min`
over 15 batches; within one interpreter; CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| allocation | ratio |
|---|---|
| small (64 B, PyMalloc) | 1.00x |
| large (2 KB, system malloc) | **1.92x** |

A small allocation is about **half the cost** of a large one, because the small one pops a block off
PyMalloc's free list, no system call, no search, while the large one calls the system allocator. Some
of the gap is the size difference itself, but the mechanism is the point: **the common Python case,
churning small short-lived objects, is routed onto the fast path by design.** PyMalloc is why a
language that allocates an object for every `int` result is not dominated by allocation cost. It is the
invisible reason Chapter 17's specialized `BINARY_OP_ADD_INT` is worth specializing, because the
allocation of the result `int` around it is already cheap.

The trade PyMalloc makes is memory for speed and simplicity. Rounding to size classes wastes up to 16
bytes per small object, and pinning whole arenas until they fully empty can hold memory a general
allocator would have returned. For Python's workload, that is the right trade; for an application that
allocates a few enormous objects, PyMalloc is bypassed entirely and the system allocator handles them.

---

## 28.6 Edges and failure modes

**Memory that will not shrink.** §28.2. An arena is released only when *fully* empty; a few live objects
scattered across a 1 MB arena pin the whole thing. This is why a process's memory can stay high after a
transient spike. If it matters, isolate the transient allocation in a subprocess whose exit returns the
memory.

**Assuming `getsizeof` is the allocation.** §28.3. `getsizeof` reports the object's size; the *allocated*
block is rounded up to the size class, and the object also carries a GC header if tracked (Chapter 19).
Neither is the number `getsizeof` returns.

**Fighting the size-class rounding.** Shaving an object from 33 to 32 bytes may not change its size
class and saves nothing; crossing a class boundary (say 512 to 513) moves it from PyMalloc to
`malloc`, a bigger change than the one byte suggests. Know the boundaries before micro-optimizing.

**Tuning GC thresholds blindly.** §28.4. Lowering the generation-0 threshold collects more often (more
CPU, less peak memory); raising it does the reverse. It changes the cadence, not the correctness.
Profile before touching it, and see Chapter 3's measurement of when disabling helps or hurts.

**Large-object fragmentation.** §28.2 and §28.5. PyMalloc does not help objects over 512 bytes; a
workload churning many mid-sized objects goes through the system allocator and can fragment. For dense
large data, use `bytes`, `array`, or NumPy (one big allocation) rather than many mid-sized objects.

---

## 28.7 Connections

**Backward.** The object header, the `PyGC_Head` that tracked objects carry, and the million-integer
memory measurement are Chapter 19. The cyclic collector's algorithm (copy-and-subtract to find
unreachable cycles) and the `gc.disable`/`freeze` levers are Chapter 3, whose measurement §28.4
explains structurally. The size classes underlie the container growth policies of **Deep Q**.

**Forward.** `weakref`, which breaks a cycle so plain refcounting reclaims an object with no collector,
is **Deep A**. The free-threaded build's per-thread allocator state and biased reference counting change
this picture and are Chapter 26 and **Deep L**. Profiling memory, `tracemalloc`, and finding leaks are
**Deep K**.

**Across books.** The allocator is why the boundary to **Book I** is worth crossing for large data:
holding a million small Python objects churns PyMalloc and the collector, while holding the same data as
one buffer (Chapter 7's `memoryview`, or a NumPy array) is a single system allocation that PyMalloc
never touches and the collector never scans. The order-book capstone stores its price levels as one
dense buffer for exactly this reason, keeping them out of both PyMalloc's pools and the generational
collector. **Deep M** owns the boundary; this chapter is the allocator cost that makes crossing it
worthwhile.

---

## 28.8 Exercises

**1. Watch the free list.** Allocate and free a small object repeatedly and confirm with `id()` that the
block is reused. Then hold references to a growing list of small objects and show the addresses stop
repeating. Explain, using §28.3, what changed.

**2. Find the size-class boundaries.** Using `sys.getsizeof`, map the size classes by allocating
`bytes(n)` for `n` from 1 to 40 and recording where the allocated size steps. Confirm the 16-byte
spacing, and predict where `bytes(500)` and `bytes(513)` fall relative to the 512-byte threshold.

**3. Promote an object by hand.** Create a tracked object and use `gc.get_objects(generation=g)` to watch
it promote through the generations as you call `gc.collect(0)`, `gc.collect(1)`. Then `gc.freeze()` it
and show it leaves the generations entirely. Explain what `freeze` did.

**4. Measure the arena-pinning effect.** Allocate a large number of small objects, free all but a few
scattered ones, and observe (via `sys._debugmallocstats()` or process memory) that memory does not fully
return. Explain why, and what would make it return.

**5. The design question.** PyMalloc adds a whole allocator layer above the system `malloc`, with its own
arenas, pools, and free lists, rather than tuning `malloc` or using an off-the-shelf allocator. Argue why
a language-specific allocator was worth building. Your answer must address Python's small-object churn
(Chapter 19), the size-distribution assumption PyMalloc can make that `malloc` cannot, and the
interaction with reference counting's immediate frees.

---

## 28.9 Summary and cross-references

- **PyMalloc** (`obmalloc.c`) handles every allocation **512 bytes or less** in a three-level hierarchy:
  **arenas** (1 MB from the OS), **pools** (16 KB, one size class each), and **blocks** (the fixed-size
  unit handed out). Larger objects go to the system allocator.
- The **free list** makes allocation a list pop: a freed block is reused immediately by the next
  allocation of its size class, no system call, which is why churning small short-lived objects is cheap.
  There are **32 size classes** up to 512 bytes, spaced 16 bytes apart.
- The **generational collector** promotes survivors 0, 1, 2; thresholds `(2000, 10, 10)` scan generation
  0 often and cheaply and generation 2 rarely, the weak generational hypothesis, which is why
  `gc.freeze` and `gc.disable` (Chapter 3) behave as they do.
- **Measured:** a small (PyMalloc) allocation is about **half** the cost of a large (system malloc) one;
  PyMalloc is why per-operation object allocation does not dominate.

**Cross-references.** The object header and `PyGC_Head` → Chapter 19. The cyclic collector and GC levers
→ Chapter 3. Container growth policies → Deep Q. `weakref` → Deep A. Free-threading's allocator changes
→ Chapter 26 and Deep L. Memory profiling → Deep K. The large-data boundary to C → Deep M.
