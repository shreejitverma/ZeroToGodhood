# Chapter 79: `memoryview`: Slicing, Casting, and the Export Count

Chapter 44 handed a whole buffer to C and made the argument that the way to use C for a hot loop is to cross the boundary once.
This chapter is about the object that makes that safe from the Python side.

A `memoryview` is **not a container**. It owns no bytes. It is a borrowed pointer into memory that some other object owns, together with the metadata a C consumer needs to interpret it: the element format, the item size, the shape, the strides, and whether the memory is writable and contiguous.
Slicing it produces another borrowed pointer, which is why slicing a megabyte costs **28 nanoseconds** where slicing the equivalent `bytes` costs **14 microseconds**, a factor of over 500.

And borrowing a pointer into a buffer that could be reallocated is a dangling pointer, so there has to be a mechanism preventing it. CPython's mechanism is an **export count**: the owner tracks how many live views exist and refuses to move its memory while any of them do. That is why `bytearray.append` can raise `BufferError`, an error most Python programmers meet once and never understand, and it is the single most important thing to know about this object.

**This is a Deep M boundary chapter.**
It is about the Python-visible half of the buffer protocol: what a view can express, what it refuses, and what it costs.

## Section index

- **79.1** Borrowing, reinterpreting, and refusing
- **79.2** The export count, and why `BufferError` exists
- **79.3** Measurement: the cost of a view against the cost of a copy
- **79.4** Edges and failure modes
- **79.5** Connections
- **79.6** Exercises
- **79.7** Summary and cross-references

Listings live under `code/ch160/` and are re-executed by `make verify` on both verification interpreters.

---

## 79.1 Borrowing, reinterpreting, and refusing

```python
# code/ch160/l01_memoryview.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a memoryview borrows; writing through it mutates the owner ---
  owner after view[0] = 'A' : b'Abcdef'
  view and owner share memory: True
--- slicing a memoryview is a VIEW; slicing bytes is a COPY ---
  owner after middle[0] = 'C' : b'AbCdef'
  bytes(owner)[2:5] is a copy : True
--- format, itemsize, shape: the metadata C needs ---
  raw.format / itemsize / shape : B / 1 / (8,)
  raw.nbytes                    : 8
--- .cast() reinterprets the SAME bytes under another C type ---
  as 'H' : itemsize 2, shape (4,), nbytes 8
  as 'Q' : itemsize 8, shape (1,), nbytes 8
  no copy was made: same nbytes  : True
--- a strided view is legal in Python and NOT contiguous for C ---
  raw.c_contiguous         : True
  raw[::2].c_contiguous    : False
  raw[::2].tolist()        : [0, 2, 4, 6]
  casting a strided view   : TypeError: memoryview: casts are restricted to C-contiguous views
--- readonly views: bytes exports one, and it refuses writes ---
  memoryview(b'...').readonly : True
  writing to it               : TypeError: cannot modify read-only memory
  .toreadonly() on a writable view : True
--- the safety mechanism: the owner counts live exports ---
  append with no view outstanding : b'xyz'
  append while a view is live     : BufferError: Existing exports of data: object cannot be re-sized
  append after view.release()     : b'xyz!'
--- release is what `with` does, and using a released view raises ---
  first byte inside the block : 115
  after the block             : ValueError: operation forbidden on released memoryview object
```

**Borrowing, demonstrated by mutation.**
`view[0] = ord("A")` changes `owner`. There is no copy anywhere in that statement: the view holds a pointer into the `bytearray`'s buffer, and the assignment writes a byte through it. `view.obj is owner` confirms the view knows who it borrowed from, which is also how it keeps the owner alive: the view holds a strong reference to the object, and a borrowed reference to its memory.

**Slicing is where the cost model diverges.**
`view[2:5]` produces a second view onto the same memory, offset by two; writing through it is visible in `owner`. `bytes(owner)[2:5]` allocates three fresh bytes and copies them, so the result is independent. Both spellings look like slicing and only one of them is O(1). §79.3 measures the gap.

**The metadata is the interesting part.**
`format`, `itemsize`, and `shape` are the fields a C consumer reads from `Py_buffer` to know how to interpret the memory. `raw.format` is `B` (unsigned char) and `raw.shape` is `(8,)`: eight one-byte items. `.cast("H")` re-reads the *same eight bytes* as four two-byte unsigned shorts, and `.cast("Q")` as one eight-byte unsigned long long. `nbytes` is 8 in all three cases, which is the proof that nothing was copied, only reinterpreted. This is what makes `memoryview` the natural Python-side partner to `struct` (Deep P) and to any C routine that wants typed access to a byte buffer.

**Non-contiguous views are legal, and are the trap.**
`raw[::2]` is a perfectly good Python object: `tolist()` gives `[0, 2, 4, 6]`. But `c_contiguous` is `False`, and `.cast("H")` on it raises `TypeError: memoryview: casts are restricted to C-contiguous views`. The reason is not arbitrary. A strided view does not correspond to any block of memory a C function can be handed; delivering it would require either copying it into a fresh contiguous block, which defeats the purpose, or teaching every consumer about strides, which most C APIs do not want. Python therefore lets you *build* the strided view and refuses to hand it to anything that needs contiguity, which is exactly the boundary this volume is about.

**Read-only is part of the protocol, not a convention.**
`memoryview(b"immutable").readonly` is `True` and writing through it raises `TypeError`. That is not `bytes` being polite; it is the buffer protocol's `readonly` flag, which the exporter sets and the consumer must respect. `.toreadonly()` (3.8+) downgrades a writable view, which is the right thing to pass to a function you do not want writing into your buffer.

---

## 79.2 The export count, and why `BufferError` exists

This is the mechanism worth internalising, because it is the reason the whole design is memory-safe and it is the source of the one error message that surprises people.

**The problem.**
A `bytearray` grows by reallocating: when `append` outgrows the current allocation, it asks for a larger block, copies, and frees the old one. Any pointer into the old block is now dangling. A `memoryview` is exactly such a pointer.

**The mechanism.**
Every object that exports a buffer keeps a count of outstanding exports. `memoryview(obj)` increments it; releasing the view decrements it. While the count is non-zero, any operation that would move or resize the memory fails with `BufferError`. The listing shows all three states in sequence: `append` succeeds with no view outstanding, raises `BufferError: Existing exports of data: object cannot be re-sized` while one is live, and succeeds again after `release()`.

**The senior-engineer contrast.**
This is a **dynamic borrow check**. Rust does the same analysis statically: a `&mut Vec<u8>` and a `&[u8]` into it cannot coexist, and the compiler proves it. CPython cannot prove it, because the view may be created in one module and the `append` performed in another at runtime, so it counts instead and fails at the moment of conflict. The trade is Rust's compile-time error against Python's `BufferError` at exactly the operation that would have been unsafe. In C the same code is a use-after-free that runs fine in testing.

**The practical discipline.**
A view held longer than it is needed blocks the owner from growing, and the failure surfaces far from the code that created the view. Three habits make this manageable:

- Use `with memoryview(buf) as mv:` when the view's lifetime is a block. The listing shows the exit releasing it, and shows that touching the view afterwards raises `ValueError: operation forbidden on released memoryview object`, which is a far better failure than a stale pointer.
- Call `.release()` explicitly when the view escapes a block, for instance when it was stored on an object.
- Do not store views in long-lived structures unless you mean to pin the buffer. If you need the bytes to outlive the borrow, materialise them (`bytes(mv)`) and accept the copy, which §79.3 prices.

**What the count does not protect.**
The export count protects the *buffer's* address. It does not protect against a C extension that ignores the protocol, does not protect a view of memory owned by something outside Python (an `mmap` that gets unmapped, a `ctypes` block whose owner is collected), and does not make concurrent writes safe. It is a lifetime mechanism, not a synchronisation one.

---

## 79.3 Measurement: the cost of a view against the cost of a copy

**Methodology.** `code/ch160/bench_memoryview.py`.
Three groups: one slice of a large and a small buffer, a thousand successive header strips over a 1 MB buffer, and the cost of materialising a view back into `bytes`. `min` of 9 batches (5 for the parse loop).
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**One slice.**

| slice | time |
|---|---|
| `view[1:]` on 1 MB | 28 ns |
| `view[1:]` on 64 B | 28 ns |
| `bytes[1:]` on 64 B | 25 ns |
| `bytes[1:]` on 1 MB | 14,457 ns (**517x**) |

The view's cost is flat: allocate a small object, record an offset and a length. The `bytes` slice is linear in what it copied. At 64 bytes the copy is *cheaper* than the view, by about 12%, because a small `memcpy` costs less than constructing a view object with its metadata. At a megabyte it is 517 times more expensive. There is no general answer to "is a view faster"; there is a crossover, and it is at a few dozen bytes.

**The parse loop, where the difference becomes algorithmic.**

| strip a 16-byte header 1,000 times from a 1 MB buffer | time |
|---|---|
| over a `memoryview` | 34 us |
| over `bytes` | 13,670 us (**402x**) |

This is the pattern that actually appears in code: read a frame header, keep the remainder, repeat. Each `bytes` slice copies everything that remains, so a thousand strips copy roughly a gigabyte in total and the loop is **quadratic** in the number of frames. Each view slice copies nothing, so the loop is linear. The 402x here is not a constant factor; it grows with the buffer and with the number of strips, which is what makes this the canonical `memoryview` use case rather than a micro-optimization.

**The other half, stated honestly.**

| materialise 1 MB | time |
|---|---|
| `view[1:]` (no copy) | 28 ns |
| `bytes(view)` | 13,026 ns |
| `view.tobytes()` | 13,064 ns |

The copy did not disappear; it moved. If the consumer needs a real `bytes` object, you pay the same 13 microseconds you were avoiding, plus the complexity of having introduced a view. `bytes(view)` and `view.tobytes()` are the same operation to within measurement error, so choose on readability.

**The decision, therefore.**
A view pays off when the consumer can take a buffer without materialising it: `socket.send`, `file.readinto`, `struct.unpack_from`, `hashlib.update`, a `ctypes` call, a NumPy array constructor. It pays nothing, and costs clarity, when the consumer needs `bytes` and you must materialise at the end anyway. The question to ask is not "is this buffer large" but "does anything downstream accept a buffer".
**Book I** is the strongest case of a downstream that does: the tick stream crosses to the matching engine as a buffer, and the 13 microseconds per megabyte that a materialising design would pay on every hop is precisely the cost the seam exists to avoid.

---

## 79.4 Edges and failure modes

**`BufferError` on `append` is the export count, not a bug.** §79.2.
The fix is to release the view, not to copy the buffer. `with memoryview(buf) as mv:` is the idiom.

**A released view raises `ValueError` on every operation.** §79.1.
This includes `len()` and indexing. If a view escapes the `with` block that released it, the failure is loud, which is the intended design.

**Casts require C-contiguity.** §79.1.
`mv[::2].cast("H")` raises `TypeError`. So does casting a multi-dimensional non-C-contiguous view. If you need a contiguous copy of a strided view, `bytes(mv)` gives one, at the price §79.3 measured.

**`.cast()` requires the total size to divide evenly.**
Casting an 8-byte view to `"Q"` gives shape `(1,)`; casting a 7-byte view to `"Q"` raises `TypeError`. Check `nbytes % itemsize` before casting a buffer whose length you do not control.

**A view keeps its owner alive, which can look like a leak.**
The view holds a strong reference to the exporting object. A small view of a 100 MB buffer pins all 100 MB. This is correct, and it is the memory-profiling puzzle that `memoryview` most often causes: the retained object is the buffer, and the retainer is a view you forgot to release.

**Views are not thread-safe and the export count is not a lock.** §79.2.
Two threads writing through views of the same buffer race exactly as they would through the buffer. Under free-threading (Deep L) this matters more, not less.

**Equality and hashing are not what you may expect.**
`memoryview(b"ab") == b"ab"` is `True`, comparison is by content. But a view is hashable only if it is read-only *and* its underlying object is hashable, so `hash(memoryview(bytearray(b"ab")))` raises `ValueError`. Using views as dict keys is usually a mistake for that reason.

**`sys.getsizeof` on a view reports the view, not the memory.**
It is a small object, tens of bytes, regardless of how much memory it addresses. Memory accounting that walks views will under-report unless it follows `.obj`.

---

## 79.5 Connections

**Backward.**
Handing whole buffers to C, and the one-call-not-a-million argument, is Chapter 44. The FFI boundary's per-call cost, which is why the whole-buffer approach exists, is Chapter 43. The C-API from the Python side is Chapter 45. The general principle that the copy is the cost, and that avoiding it means building in the right container, is Chapter 74.

**Forward.**
Releasing the GIL around a buffer operation, which is what makes a large `memoryview`-based C call parallelisable, is Chapter 80. Reference counting across the boundary, of which the export count is a specialised instance, is Chapter 81. `struct.unpack_from` over a view, and binary record layout in general, is Deep P. `array.array` and NumPy as buffer exporters are Chapter 39 and Deep T. `mmap`, the buffer whose owner is the operating system, is Chapter 44 of Deep R.

**Across books.**
This is the object that makes the seam between the books cheap. **Book I** exports a tick buffer; Python wraps it in a `memoryview`, slices frames off it without copying, and unpacks fields with `struct.unpack_from` directly out of the borrowed memory. The export count is what makes that safe to do while the C side is still writing into an adjacent region, and §79.3's 402x is what it is worth on the parse loop.

---

## 79.6 Exercises

**1. Prove the borrow.** Reproduce §79.1's first block. Then take a view of a `bytes` object and confirm it is read-only, and explain why `bytes` exports a read-only buffer and `bytearray` exports a writable one.

**2. Trigger the export count.** Write code that raises `BufferError`, then fix it three ways: `with`, explicit `release()`, and copying. Say which you would ship for a network read loop and why.

**3. Find the crossover.** Reproduce §79.3's first table at 16, 64, 256, 1,024, and 4,096 bytes. Find the size at which the view starts winning, and explain both sides of the crossover from the cost model.

**4. Make the loop quadratic.** Reproduce §79.3's parse loop. Then plot its time against the number of strips for `bytes` and for a view, and confirm one curve is linear and the other quadratic.

**5. Cast and refuse.** Build a view whose `nbytes` is not a multiple of 8 and cast it to `"Q"`. Build a strided view and cast it. Explain both errors in terms of what a C consumer would have to do with the result.

**6. The design question.** CPython could make a strided `memoryview` usable by C consumers by silently copying it into a contiguous block. Argue why it raises `TypeError` instead: what the silent copy would cost, how a caller would find out it happened, and what the equivalent decision looks like in NumPy, which *does* make that copy and names it (`np.ascontiguousarray`).

---

## 79.7 Summary and cross-references

- A `memoryview` is a **borrowed pointer plus metadata**: format, itemsize, shape, strides, `readonly`, `c_contiguous`. It owns no bytes and holds a strong reference to the object that does.
- **Slicing a view is a view; slicing `bytes` is a copy.** `.cast()` reinterprets the *same* bytes under another C type with no copy, which is why `nbytes` is unchanged across casts.
- **A strided view is legal in Python and unusable by C.** `c_contiguous` is `False` and `.cast()` raises `TypeError`, because a strided view corresponds to no block of memory a C function can be handed.
- **The export count is a dynamic borrow check.** The owner refuses to resize or move memory while a view is live: `BufferError: Existing exports of data: object cannot be re-sized`. `with memoryview(...) as mv:` releases it; using a released view raises `ValueError`.
- **Measured on 3.13.5:** slicing a 1 MB `memoryview` costs **28 ns** against **14.5 us** for the equivalent `bytes` slice (**517x**), and at 64 bytes the `bytes` slice is 12% *cheaper*, so there is a crossover at a few dozen bytes. Stripping a 16-byte header 1,000 times costs **34 us** over a view and **13.7 ms** over `bytes` (**402x**), because the `bytes` version is quadratic.
- **The honest other half:** `bytes(view)` on 1 MB costs **13 us**. The copy did not vanish, it moved to wherever a real `bytes` object is finally required. A view pays off only when something downstream accepts a buffer.
- **Edges:** a view pins its owner's memory (looks like a leak); casts need contiguity and an even division; views are content-comparable but hashable only when read-only over a hashable owner; `sys.getsizeof` reports the view, not the memory; the export count is a lifetime mechanism, not a lock.

**Cross-references.** Whole-buffer C calls → Chapter 44. FFI per-call cost → Chapter 43. The C-API from Python → Chapter 45. Copy avoidance as a general principle → Chapter 74. Releasing the GIL at the boundary → Chapter 80. Refcounts across the boundary → Chapter 81. `struct` and binary records → Deep P. `array.array` → Chapter 39. NumPy as a buffer exporter → Deep T. `mmap` → Deep R.
