# Chapter 37: Binary Data and the Buffer Protocol

A network server reads a 14 MB frame and processes it in overlapping windows, one slice per record.
Written the obvious way, `frame[start:end]`, each window *copies* its bytes out of the frame, and a loop
over a thousand records copies gigabytes in aggregate, most of it immediately discarded. The profiler
blames memory allocation, and the fix is not a faster copy but *no copy*: a `memoryview` slice is a
zero-copy window onto the original buffer. Measured, slicing a 14 MB region as `bytes` peaks at **14 MB**
of new allocation; slicing it as a `memoryview` peaks at **496 bytes**, a **28,000x** difference, because
the view copies nothing, it references the same buffer with adjusted bounds.

That is the headline, and it is the reason the buffer protocol exists: to let objects share a block of
memory without copying it. This chapter covers the binary data types, `bytes` (immutable), `bytearray`
(mutable), `memoryview` (a zero-copy window), and `struct` (packing fixed binary layouts), and it is part
of **Deep Q**. Where Chapter 7 covered text (`str`, encodings), this chapter covers *bytes*, the raw
binary side that protocols, file formats, and C interop live on.

## Section index

- **37.1** The four types and how they share memory
- **37.2** `struct`: fixed binary layouts
- **37.3** Measurement: the copy you did not need to make
- **37.4** Edges and failure modes
- **37.5** Connections
- **37.6** Exercises
- **37.7** Summary and cross-references

Listings live under `code/ch037/` and are re-executed by `make verify` on both interpreters.

---

## 37.1 The four types and how they share memory

```python
# code/ch037/l01_buffers.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- bytes (immutable) vs bytearray (mutable) ---
  bytes     : b'hello' (immutable)
  bytearray : b'Hello' (mutated in place)
--- memoryview: a zero-copy window; edits write through ---
  after mv edit  : b'ccccBBBB'
  mv[4:] slice   : b'BBBB' (a view, not a copy)
--- struct: pack/unpack a fixed binary layout ---
  packed (10 bytes): 00010000fffd4048f5c3
  unpacked        : (65536, -3, 3.140000104904175)
  float32 note    : 3.14 came back as 3.140000104904175
```

**`bytes`** is an immutable sequence of 8-bit values, the type for binary data you read but do not modify
(a received message, a file's contents). **`bytearray`** is its mutable sibling: `ba[0] = ord("H")` edits
in place, the type for a buffer you build or patch. Both are sequences of integers `0..255`, not
characters, the boundary with `str` (Chapter 7) is exactly `encode`/`decode`.

**`memoryview`** is the important one: a zero-copy *window* onto any object that exposes the buffer
protocol (`bytes`, `bytearray`, `array`, NumPy arrays, and more). Two properties matter. First, a
`memoryview` slice does not copy, `mv[4:]` is a new view over the same memory, not a new buffer, which is
what §37.3 measures. Second, on a *mutable* source a memoryview *writes through*: `mv[0:4] = b"cccc"`
changes the underlying `bytearray` (`b'ccccBBBB'`), because the view and the buffer are the same memory. A
memoryview is how you process large binary data in windows without copying, and how Python code shares a
buffer with C extensions and NumPy without a round trip through `bytes`.

---

## 37.2 `struct`: fixed binary layouts

`struct` converts between Python values and a fixed C-style binary layout, the tool for network protocols,
binary file headers, and C-struct interop. The format string names the byte order and each field:
`">Ihf"` is big-endian (`>`) followed by a `uint32` (`I`), an `int16` (`h`), and a `float32` (`f`).
`struct.pack` produces the 10-byte encoding (`4 + 2 + 4`), and `struct.unpack` reverses it.

The listing surfaces one subtlety worth naming: `3.14` packed as a `float32` (`f`) and unpacked comes back
as `3.140000104904175`, not `3.14`. That is not a `struct` bug; it is the 32-bit float's precision (Chapter
35), `3.14` has no exact 32-bit representation, and packing narrows the 64-bit Python `float` to 32 bits.
Use `d` (float64) when you need the full double precision, and know that any float field is subject to the
representation limits Chapter 35 measured. The byte-order prefix is mandatory for interop: `>` (big-endian,
network order) and `<` (little-endian) produce different bytes, and omitting the prefix uses native order
*and* native alignment padding, which is almost never what a wire protocol wants.

---

## 37.3 Measurement: the copy you did not need to make

**Methodology.** `code/ch037/bench_memoryview.py`. Slicing a 14 MB region out of a 16 MB `bytes` buffer as
a `bytes` copy versus as a `memoryview`. Peak memory via `tracemalloc`, which is deterministic. CPython
3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| slice of 14 MB | peak memory |
|---|---|
| `bytes` slice (copy) | **14,000,033 bytes** |
| `memoryview` slice (view) | **496 bytes** |
| ratio | **~28,000x** |

The `bytes` slice allocates and copies the full 14 MB region: O(n) memory and O(n) time. The `memoryview`
slice allocates a small (496-byte) view object and copies *nothing*, it records an offset and length into
the existing buffer: O(1). Both give access to the same bytes (`same bytes? True`), but one materializes a
second copy and the other does not.

The discipline: **when you process large binary data in windows, slice with `memoryview`, not by copying.**
A protocol framer, a file-format parser, or a chunked reader that walks a large buffer can do all its work
through views and copy out only the small pieces it actually keeps. Reach for a `bytes` copy only when you
need an *independent, immutable* value, one that must survive after the source buffer is freed or mutated.
The trap in the other direction, holding a `memoryview` onto a buffer you then try to resize, is §37.4's
first edge.

---

## 37.4 Edges and failure modes

**A memoryview pins its buffer.** An open `memoryview` onto a `bytearray` blocks operations that would
resize or reallocate it: `ba.append(...)` while a view is live raises `BufferError`. The view must be
released (or fall out of scope, or be used in a `with` block) before the buffer can be resized. This is a
safety guard, resizing would invalidate the view's pointer, not a bug.

**Zero-copy means shared mutation.** §37.1. A memoryview onto a mutable buffer writes through, so a view
handed to another function can mutate your buffer. When you need to share bytes but not mutation, pass a
`memoryview` of a `bytes` (read-only), or copy.

**`struct` float precision.** §37.2. Packing a Python `float` as `f` (float32) narrows it and loses
precision (`3.14` becomes `3.140000104904175`). Use `d` (float64) for full precision, and see Chapter 35
for why the narrowing is lossy.

**`struct` byte order and alignment.** Omitting the `>`/`<`/`!` prefix uses native order *and* inserts
native alignment padding between fields, so the packed size can exceed the sum of field sizes and differ
across platforms. Always specify byte order explicitly for any data that crosses a process or wire.

**`bytes` vs `str` confusion.** Indexing `bytes` yields an `int` (`b"A"[0]` is `65`), not a one-character
`bytes`. Concatenating `bytes` and `str` raises `TypeError`. The `encode`/`decode` boundary (Chapter 7) is
where you cross between them, deliberately.

**Slicing still copies for `bytes`/`bytearray`.** Only `memoryview` slicing is zero-copy. `bytes[a:b]` and
`bytearray[a:b]` both copy. If the win you want is zero-copy, you must be slicing a `memoryview`, not the
underlying sequence.

---

## 37.5 Connections

**Backward.** The `str`/`bytes` boundary and `encode`/`decode` are Chapter 7; this chapter is its binary
counterpart. The float precision that `struct`'s `f` format exposes is Chapter 35. The immutability of
`bytes` (versus mutable `bytearray`) is the value-semantics theme of Chapter 4, applied to binary data.

**Forward.** The buffer protocol at the C level, the `Py_buffer` struct and `tp_as_buffer` slot that let
objects export memory, is **Deep A**. NumPy arrays, the most important buffer-protocol producer/consumer,
and the zero-copy interop between Python buffers and NumPy, are **Deep T**. Reading and framing binary data
off sockets and files is **Deep R**.

**Across books.** Zero-copy buffers are how Book II moves large binary payloads into **Book III** without
doubling memory. A **Book III** pipeline that reads model weights, image tensors, or a serialized index
frames the bytes with `memoryview` and hands the views to NumPy/`array` without copying, so a multi-
gigabyte payload never exists twice. The §37.3 zero-copy property is exactly what makes that payload size
feasible in a bounded-memory service. **Deep U** owns the binary seam.

---

## 37.6 Exercises

**1. Reproduce the zero-copy win.** Run §37.3's benchmark and confirm the `bytes` slice's O(n) memory
against the `memoryview` slice's O(1). Then slice in a loop (many windows) and show the `bytes` version's
memory scales with the number of windows while the `memoryview` version stays flat. Explain why.

**2. Write through a view.** Build a `bytearray`, take a `memoryview`, and mutate the buffer through the
view. Confirm the change is visible in the original. Then take a `memoryview` of a `bytes` and show the
write is refused. Explain the read-only-vs-mutable distinction.

**3. Pin and resize.** Hold a live `memoryview` onto a `bytearray` and try to `append` to the bytearray.
Observe the `BufferError`, then release the view and show the append succeeds. Explain what the view was
protecting.

**4. Pack a protocol header.** Use `struct` to pack and unpack a small binary header (a magic number, a
version, a length) with explicit big-endian order. Then pack a float as `f` and as `d` and compare the
round-trip precision. Explain the float32 loss in terms of Chapter 35.

**5. The design question.** Python provides a zero-copy view type (`memoryview`) alongside copying
sequences (`bytes`, `bytearray`). Argue why both exist rather than making all slicing zero-copy. Your
answer must address the safety cost of shared mutable memory, why a view must pin its buffer against
resizing, and when an independent copy is the correct, safer choice despite the memory cost.

---

## 37.7 Summary and cross-references

- **`bytes`** (immutable) and **`bytearray`** (mutable) are sequences of `0..255` integers, the binary
  counterpart to `str`; the boundary is `encode`/`decode`.
- **`memoryview`** is a **zero-copy window** onto any buffer-protocol object: slicing it copies nothing,
  and on a mutable source it writes through. It pins its buffer against resizing.
- **`struct`** packs and unpacks fixed binary layouts; specify byte order explicitly, and know that the
  `f` (float32) format narrows precision (Chapter 35).
- **Measured:** slicing a 14 MB region as `bytes` peaks at **14 MB**; as a `memoryview`, **496 bytes**, a
  **~28,000x** difference. Process large binary data in `memoryview` windows; copy to `bytes` only when you
  need an independent value.

**Cross-references.** `str`/`bytes` and encodings → Chapter 7. Float precision → Chapter 35. Value
semantics → Chapter 4. The C buffer protocol → Deep A. NumPy zero-copy interop → Deep T. Binary I/O →
Deep R. The binary seam → Deep U.
