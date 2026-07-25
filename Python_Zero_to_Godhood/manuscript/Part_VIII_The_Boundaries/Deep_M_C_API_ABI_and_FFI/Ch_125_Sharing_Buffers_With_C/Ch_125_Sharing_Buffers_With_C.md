# Chapter 44: Sharing Buffers with C

Chapter 43 ended on a rule and a promise.
The rule: the FFI boundary costs ~10x per call, so cross *rarely* with a lot of work each time.
The promise: to move a hot *loop* into C, you do not call C per element, you **hand C the whole buffer once**.
This chapter makes good on that promise, and the payoff is the largest number in Deep M: zeroing a million bytes with a single C call is ~**8,400x** faster than a Python per-byte loop, because one crossing lets C run the entire loop at memory-bandwidth speed while the Python version pays interpreter overhead a million times.

The mechanism is contiguous, typed memory shared across the boundary.
A `ctypes` array (`c_int * n`) is a C block you can pass whole; a single `libc.qsort` or `libc.memset` call operates on all of it; and `from_buffer` wraps an *existing* Python buffer (a `bytearray`) with **zero copy**, so a C function writes directly into your memory.
Together these are the concrete form of the abstract principle every fast numeric library rests on, NumPy, Arrow, image and audio codecs, database drivers, they all hold data in contiguous typed buffers and cross into C (or vectorized code) *once per operation over the whole buffer*, never once per element.

**This is the second Deep M chapter, on the data side of the boundary.**
Chapter 43 (`ctypes` calls) was the function side; this is the buffer side, and it is the realization of Chapter 19's "escape the `PyObject` header" and Deep T's vectorization (Chapter 96) at the C-interop level. It references Deep Q's buffer protocol / `memoryview` (Chapter 37) as the general, safe consumer API, and shows the `ctypes` producer side.

## Section index

- **44.1** Contiguous buffers, one-call operations, and zero-copy sharing
- **44.2** The callback caveat, and where the boundary still bites
- **44.3** Measurement: one call versus a million
- **44.4** Edges and failure modes
- **44.5** Connections
- **44.6** Exercises
- **44.7** Summary and cross-references

Listings live under `code/ch125/` and are re-executed by `make verify` on both verification interpreters.

---

## 44.1 Contiguous buffers, one-call operations, and zero-copy sharing

```python
# code/ch125/l01_buffers.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a ctypes array is a contiguous C block ---
  array   : [5, 3, 1, 4, 2]
  sizeof  : 20 bytes   (5 x 4-byte int)
--- ONE C call sorts the whole array (libc.qsort) ---
  after qsort : [1, 2, 3, 4, 5]   (one crossing sorted all 5)
--- ONE C call fills a whole block (libc.memset) ---
  after memset(_, 'A', 8) : b'AAAAAAAA'
--- from_buffer: C writes directly into a Python bytearray (ZERO COPY) ---
  the C memset wrote into our bytearray : b'ZZZZZZZZ'
  (data and the C view are the SAME memory, nothing was copied)
--- the rule ---
  hand C a whole contiguous buffer and let ONE call do the loop; use
  from_buffer to share Python memory with C zero-copy
```

Three building blocks, in increasing power.

**A `ctypes` array is a contiguous C block.**
`c_int * 5` is a type; instantiating it gives a block of five 32-bit ints laid end to end (`sizeof` is 20, exactly `5 * 4`), the same dense layout Chapter 19's `array` and Deep T's ndarray use to escape per-element `PyObject`s. It is memory C can address directly.

**One call operates on the whole block.**
`libc.qsort(arr, len, itemsize, cmp)` sorts the *entire* array in a single crossing, and `libc.memset(buf, val, n)` fills a whole block in one call. This is the pattern: the C function does the loop; Python crosses the boundary once. `[5,3,1,4,2]` becomes `[1,2,3,4,5]` with one `qsort`; eight bytes become `AAAAAAAA` with one `memset`.

**`from_buffer` shares Python memory with C, zero-copy.**
`(c_char * 8).from_buffer(data)` wraps an existing `bytearray`'s memory *without copying it*, so when `libc.memset` writes through the `ctypes` view, it writes into `data` itself, the `bytearray` becomes `ZZZZZZZZ`. The Python object and the C view are the **same memory**. This is the crucial capability: you do not copy your data into a C-owned buffer and copy the result back; C operates *in place* on the buffer Python already holds, so a megabyte of data crosses the boundary as a *pointer*, not a copy.

The synthesis: hold data in a contiguous typed buffer, and let a single C call do the whole operation over it, in place. That is the entire performance story of the Python/C boundary, and §44.3 measures how large the win is.

---

## 44.2 The callback caveat, and where the boundary still bites

The `qsort` example hides a subtlety that is worth surfacing, because it is the exact trap Chapter 43 warned about, reappearing inside a "one call".

`qsort` takes a **comparator callback**, and that callback is a *Python* function.
So while the `qsort` *call* is one crossing, the comparator is invoked once per comparison, `O(n log n)` times, and **each invocation crosses the boundary back into Python** (C calls the Python function, which marshals arguments, runs, marshals back).
For a large array, those callback crossings dominate, and the "one C call" is not actually cheap: it is one C call wrapped around thousands of boundary round-trips.
This is Chapter 43's ~10x per-call cost, hidden inside a callback and multiplied by the comparison count.

The lesson refines the rule.
"**Cross once with the whole buffer**" pays off only when the C function does its work **without calling back into Python**, `memset`, `memcpy`, a hashing function, a codec, a numerical kernel, all run entirely in C over the buffer and cross the boundary exactly once.
A C function that takes a Python callback (like `qsort`'s comparator) re-introduces the per-element crossing the pattern was meant to avoid.
So:

- **Best:** a C function that does the whole operation in C (no Python callback). One crossing, full C speed. This is NumPy's model, and `memset`/`memcpy`/library kernels.
- **Worse:** a C function driven by a Python callback per element. The callback crossings dominate; often no faster than pure Python (and sometimes slower).
- To sort with C speed, you want a comparator *in C* (a `key` reduced to a C-comparable buffer, or a library that sorts typed arrays natively), not a Python comparator, exactly why NumPy's `np.sort` is fast (C comparison on typed data) and `sorted(list, key=pyfunc)` is not.

The boundary, in short, is cheap to cross **around** a big C computation and expensive to cross **through** repeatedly. `from_buffer` and whole-buffer C calls put the crossing on the outside; callbacks put it on the inside.

---

## 44.3 Measurement: one call versus a million

**Methodology.** `code/ch125/bench_whole_buffer.py`.
Zeroing 1,000,000 bytes: a single `libc.memset` call versus a Python loop writing each byte.
`min` of runs, `memset` over 200 iterations, the Python loop over 3.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| zero 1,000,000 bytes | time | vs one call |
|---|---|---|
| one C `memset` call | 4.1 us | 1x |
| Python byte loop | 33.9 ms | **8,371x slower** |

One `memset` call is ~**8,400x** faster (8,484x on 3.14.6) than the Python per-byte loop.
The single call crosses the FFI boundary **once** and lets C fill the buffer at memory-bandwidth speed (microseconds for a megabyte); the Python loop pays interpreter overhead on every one of a million iterations, and had you done it via `ctypes` *per element*, you would pay the ~10x boundary cost (Chapter 43) a million times over, worse still.

This is the whole architecture of the Python/C boundary in one number, and it unifies the two Deep M measurements.
Chapter 43's **~10x per call** and this **~8,400x whole-buffer win** are the same rule seen from two sides: **amortize the crossing.**
Cross *rarely* with a *lot* of work each time, and the boundary is nearly free (4 us for a megabyte); cross *often* with a *little* work each time, and the boundary is nearly everything (34 ms for the same megabyte, byte by byte).
This is *exactly* why NumPy (Deep T) beats per-element Python: it does not call C per element, it hands C (or vectorized SIMD code) the whole array and crosses once per operation.
It is why the buffer protocol (Deep Q Chapter 37) exists: to let objects share a buffer so it crosses as a pointer, not a copy.
And it is the design rule for any Python/C system: draw the boundary so that each crossing carries a large, self-contained unit of work, a whole buffer, a whole batch, a whole file, never a single element.
Get that right and Python's ergonomics cost you almost nothing at the boundary; get it wrong and the boundary is your entire runtime.

---

## 44.4 Edges and failure modes

**A Python callback inside a C call re-crosses per invocation.** §44.2.
`qsort` with a Python comparator pays the boundary per comparison. Whole-buffer speed needs the C function to run *without* calling back into Python.

**`from_buffer` requires a writable, contiguous buffer, and pins it.**
`from_buffer` needs a mutable buffer (`bytearray`, `array`, a writable `memoryview`); `bytes` is immutable (use `from_buffer_copy` for a copy). While the `ctypes` view exists, the underlying object must not be resized or freed, doing so invalidates the C view (a dangling pointer, a potential crash).

**Zero-copy sharing means aliasing.**
The `ctypes` view and the Python object are the same memory (§44.1). A C write is immediately visible in Python and vice versa, powerful, but the aliasing bugs of Chapter 99 (views) apply, now across a language boundary with no safety net.

**Buffer bounds are not checked in C.**
`memset(buf, v, n)` with an `n` larger than the buffer is a buffer overrun, a memory-corruption bug or crash, not a Python `IndexError`. You must pass correct sizes; C trusts them.

**Alignment and element size must match.**
`qsort`'s `itemsize` must be the true element size, and a `ctypes` array's element type must match what C expects. A mismatch reinterprets memory (garbage) or oversteps bounds.

**The GIL and callbacks.**
A `ctypes` call releases the GIL, but a Python callback invoked from C must re-acquire it, so callback-heavy C calls serialize on the GIL and lose the parallelism a pure-C call could have had (Deep E / free-threading).

**Prefer the buffer protocol / `memoryview` for safe sharing.** §44.5.
`ctypes.from_buffer` is low-level; the buffer protocol (Deep Q Chapter 37) and `memoryview` provide the same zero-copy sharing with bounds and lifetime managed more safely, and are what most library APIs accept. Reach for `ctypes` buffers when driving a raw C function; prefer `memoryview` for Python-to-Python zero-copy.

---

## 44.5 Connections

**Backward.**
Contiguous typed buffers are Chapter 19's escape from per-element `PyObject`s, realized for C interop. The zero-copy `from_buffer` is the `ctypes` producer side of Deep Q's buffer protocol / `memoryview` (Chapter 37). "One call over the whole array" is Deep T's vectorization (Chapter 96) at the boundary. The aliasing of shared memory is Chapter 99 (views), across a language line.

**Forward.**
The **buffer protocol** proper (`__buffer__`, the `Py_buffer` struct, how an object exports its memory to any consumer) is Deep Q Chapter 37 and the C-API side of Deep M. The **C-API** (writing a real extension that receives a `Py_buffer` and operates on it), NumPy's C interface, and SIMD are later in **Deep M** and Deep T. Releasing the GIL for parallel C work over buffers is Deep E / free-threading.

**Across books.**
Whole-buffer crossing is the performance backbone of **Book I**: market data arrives as contiguous binary buffers, is parsed and processed by C or vectorized code in one pass over each buffer, and is shared zero-copy between stages, never copied or crossed per element. The order-book system holds price levels and quantities in contiguous typed arrays and hands them to its C matching kernel (or NumPy) whole, one crossing per batch, so the FFI boundary carries megabytes as pointers and the ~8,400x whole-buffer advantage is the difference between keeping up with the feed and falling behind, the abstract "amortize the crossing" rule turned into the shape of the data path.

---

## 44.6 Exercises

**1. One call, whole buffer.** Reproduce §44.1: a `ctypes` array sorted by one `qsort`, a block filled by one `memset`, and a `bytearray` written zero-copy via `from_buffer`. Confirm the `bytearray` changed without a copy. Explain what "the same memory" means.

**2. Expose the callback trap.** Sort a large `ctypes` array with `qsort` and a Python comparator, and time it against `sorted()` on the equivalent list. Show the callback version is not faster (maybe slower). Explain, using §44.2, why the "one call" did not help.

**3. Measure the amortization.** Reproduce §44.3. Then also implement the zeroing via `ctypes` *per element* and show it is the slowest of all. Explain the three tiers (one C call, Python loop, per-element ctypes) in terms of boundary crossings.

**4. Zero-copy round trip.** Share a `bytearray` with C via `from_buffer`, have C fill it, and read the result in Python, all with no copy. Then try it with `bytes` and observe the failure. Explain the writable/contiguous requirement and the lifetime hazard.

**5. The design question.** The Python/C boundary is cheap to cross around a big computation and expensive to cross through repeatedly (§44.2, §44.3). Argue how this shapes where you put the boundary in a system, and why "vectorize / batch / pass the whole buffer" is the universal advice for Python performance. Connect it to why NumPy is fast and a Python element loop is not.

---

## 44.7 Summary and cross-references

- To use C for a hot **loop**, cross the boundary **once with the whole buffer**, not per element. A `ctypes` array is a contiguous C block; one `qsort`/`memset` call operates on all of it; **`from_buffer`** shares an existing Python buffer with C **zero-copy** (C writes into your `bytearray` directly).
- **The callback caveat:** a C function driven by a Python callback (like `qsort`'s comparator) re-crosses the boundary per invocation, re-introducing the per-element cost. Whole-buffer speed needs the C function to run **without calling back into Python**.
- **Measured:** one `memset` over 1,000,000 bytes is **~8,400x** faster than a Python byte loop (4.1 us vs 33.9 ms), because one crossing lets C run the loop at memory speed. With Chapter 43's ~10x-per-call, this is one rule: **amortize the crossing**, cross rarely with much work each time.
- This is why **NumPy** and the **buffer protocol** are fast: hand C/vectorized code the whole array, cross once per operation.
- **Edges:** `from_buffer` needs a writable, contiguous, non-resized buffer (aliasing + lifetime hazards); C does not bounds-check (overruns corrupt memory); prefer `memoryview`/the buffer protocol for safe sharing.

**Cross-references.** Escape from per-element `PyObject`s → Chapter 19. Buffer protocol / `memoryview` (safe zero-copy) → Deep Q (Chapter 37). Vectorization (the same principle) → Chapter 96 (Deep T). View aliasing → Chapter 99. FFI call overhead (the other half of the rule) → Chapter 43. The C-API buffer side, SIMD → the rest of Deep M / Deep T. GIL and callbacks → Deep E.
