# Chapter 39: Typed Arrays

A service loads a million sensor readings into a Python `list` of integers and the process footprint jumps
by **40 megabytes** for numbers that are, physically, eight megabytes of data. The list is not storing a
million integers; it is storing a million *pointers* to a million separate integer *objects*, each object
carrying a type pointer, a reference count, and its value, about 32 bytes apiece, on top of the 8-byte
pointer slot. The `array` module fixes exactly this: `array.array('q', readings)` stores the raw 64-bit
values inline, no per-element object, and holds the same million readings in **8.2 megabytes**, a
**4.9x** reduction, measured. It also, because the values are a contiguous block of memory, exports that
memory zero-copy through the buffer protocol of Chapter 37.

That is the headline and the chapter's place in the arc: from `list` (flexible, pointer-based) through
`collections` (Chapter 32) and the buffer protocol (Chapter 37) to `array`, the compact typed sequence
that is the standard library's bridge to NumPy and numeric computing (**Deep T**). This chapter, part of
**Deep Q**, closes the volume by making the memory cost of Python's object model concrete and showing the
escape hatch.

## Section index

- **39.1** A typed sequence, and the buffer bridge
- **39.2** Why a list costs so much more
- **39.3** Measurement: bytes per element
- **39.4** Edges and failure modes
- **39.5** Connections
- **39.6** Exercises
- **39.7** Summary and cross-references

Listings live under `code/ch039/` and are re-executed by `make verify` on both interpreters.

---

## 39.1 A typed sequence, and the buffer bridge

```python
# code/ch039/l01_array.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a typed sequence: one typecode, fixed-width elements ---
  array('q')          : [10, 20, 30]
  typecode / itemsize : q / 8 bytes
  after append(40)    : [10, 20, 30, 40]
--- the type is enforced (unlike a list) ---
  append(3.14) -> TypeError: 'float' object cannot be interpreted as an integer
--- buffer protocol: zero-copy view onto the raw memory ---
  memoryview format   : q (itemsize 8)
  after mv[0] = 99    : [99, 20, 30, 40]
--- frombytes/tobytes: the raw little- or big-endian layout ---
  tobytes() length    : 32 bytes (4 x 8)
  round-trip equal    : True
```

An `array.array` is a sequence of one fixed-width numeric type, named by a *typecode*: `'q'` is a signed
64-bit integer (8 bytes), `'d'` a float64, `'b'` a signed byte, and so on. Every element is that type and
that width, stored inline, which is why the array knows its `itemsize` and why appending a `float` to an
`'q'` array raises `TypeError`, the type is enforced on every insertion, unlike a `list`, which accepts
anything. That constraint is the price of the compactness.

The second half is the bridge. Because an array's elements are a contiguous block of raw values, it
exports the **buffer protocol** (Chapter 37): `memoryview(arr)` is a zero-copy window whose `format` is the
typecode, and writing through it (`mv[0] = 99`) mutates the array's memory directly. `tobytes()`/`frombytes()`
give the raw little- or big-endian layout for serialization or wire transfer. This is what makes `array`
the interoperability type: it hands its memory to `struct`, to a socket, or to NumPy without a copy,
exactly the zero-copy discipline Chapter 37 measured, now applied to numbers instead of bytes.

---

## 39.2 Why a list costs so much more

The memory difference is structural, not an optimization detail. A Python `list` is an array of
`PyObject*` pointers (Chapter 4, **Deep A**): each slot is 8 bytes and points to a separate object. For a
list of integers, each of those objects is a full `int`, a `PyObject` header (type pointer + reference
count) plus the value, roughly 28 to 32 bytes depending on magnitude. So a million-integer list is a
million 8-byte pointers *plus* a million ~32-byte int objects: about 40 bytes per element, and the int
objects are scattered across the heap, not contiguous.

An `array.array('q')` is a single contiguous block of a million 8-byte fields. There is no per-element
object, no pointer indirection, no header per value: 8 bytes per element, laid out contiguously. The list's
flexibility (any type per slot, shared int objects, `is`-identity per element) is real and worth its cost
when you need it; for a large *homogeneous numeric* sequence you need none of it, and `array` gives you the
data without the object tax. §39.3 measures the gap the object model creates.

---

## 39.3 Measurement: bytes per element

**Methodology.** `code/ch039/bench_footprint.py`. Held memory of `list(range(N))` versus
`array.array('q', range(N))` for N = 1,000,000, via `tracemalloc` (deterministic). CPython 3.13.5, Apple
M3 Pro, macOS 27.0, arm64.

| million 64-bit ints | held memory | per element |
|---|---|---|
| `list` | **39,991,832 bytes** | **40.0 bytes** |
| `array('q')` | **8,183,816 bytes** | **8.2 bytes** |
| ratio | | **4.9x** |

The list holds **40 bytes per element**: 8 for the pointer slot plus ~32 for the distinct `int` object.
The array holds **8.2 bytes per element**: the 8-byte value inline, plus a small fixed overhead amortized
across a million elements. The 4.9x is the object model made visible, it is the cost of every element
being a first-class Python object, and it is exactly the cost `array` (and NumPy) exist to avoid for bulk
numbers.

The decision this frames: use a `list` when you need heterogeneous elements, per-element identity, or the
elements to *be* Python objects (the common case, and the right default). Use an `array` when you have a
large homogeneous numeric sequence and the 4.9x memory (and the contiguous, buffer-exportable layout)
matters, sensor data, audio samples, a numeric column, anything you might later hand to NumPy. And when the
numeric work grows beyond storage into computation, `array` is the on-ramp to **Deep T**'s NumPy, which
adds vectorized operations over the same contiguous, buffer-protocol layout.

---

## 39.4 Edges and failure modes

**One type, enforced.** §39.1. An array holds exactly one typecode; inserting the wrong type raises
`TypeError`, and there is no "array of mixed numbers." Choose the typecode wide enough for your values
(`'q'` for large ints, `'d'` for floats) up front.

**Overflow on narrow typecodes.** Assigning a value outside a typecode's range (e.g. 40000 into a signed
16-bit `'h'`) raises `OverflowError`. Unlike Python's arbitrary-precision `int` (Chapter 35), an array
element is fixed-width and *can* overflow; pick the width deliberately.

**A memoryview pins the array.** §39.1 and Chapter 37. A live `memoryview` onto an array blocks resizing
(`append`, `extend`) with `BufferError`. Release the view before mutating the array's length.

**Endianness in `tobytes`.** §39.1. `tobytes()` uses the machine's native byte order. For data that crosses
machines, record or normalize the byte order (or use `struct` with an explicit prefix, Chapter 37), or the
receiver may misread it.

**`array` is not NumPy.** `array` stores compactly but does *not* vectorize: arithmetic still iterates in
Python. For elementwise math over large arrays, `array` is only the storage; the computation belongs to
NumPy (**Deep T**). Using `array` and then looping in Python throws away half the reason to leave `list`.

**Text arrays are gone.** The `'u'` (unicode) typecode is deprecated; for text use `str`/`bytes` (Chapter 7),
not `array`. `array` is for numbers.

---

## 39.5 Connections

**Backward.** The `PyObject*`-pointer structure of `list` and the per-object header that makes it costly are
Chapter 4 and **Deep A**. The buffer protocol `array` exports is Chapter 37, this chapter applies it to
numbers. The fixed-width numeric types and their overflow (versus Python's arbitrary-precision `int`) are
Chapter 35. `array` sits alongside the specialized containers of Chapter 32 as another "right container for
the job" choice.

**Forward.** NumPy, which adds vectorized computation over the same contiguous buffer-protocol layout, is
**Deep T**, and `array` is its standard-library precursor. The C-level buffer export (`Py_buffer`) is
**Deep A**. Serializing arrays to disk or socket is **Deep R**.

**Across books.** `array` (and its NumPy successor) is how Book II holds bulk numeric data cheaply before
handing it to **Book III**. A **Book III** feature or embedding pipeline stores vectors in contiguous typed
buffers, not lists of Python floats, so a million-vector batch costs its raw byte size and can be handed to
NumPy or a GPU zero-copy. The §39.3 per-element measurement is the reason the pipeline can hold that batch
in bounded memory at all. **Deep U** owns the numeric-data seam; **Deep T** owns the computation.

---

## 39.6 Exercises

**1. Reproduce the footprint gap.** Run §39.3's benchmark and confirm the ~5x difference. Then try
typecodes `'i'` (int32) and `'d'` (float64) and explain how the per-element bytes track the `itemsize`,
while the list's per-element cost stays ~40 bytes regardless.

**2. Cross the buffer bridge.** Build an `array('d')`, take a `memoryview`, and write through it to mutate
the array. Then `tobytes()` and `frombytes()` to round-trip it and confirm equality. Explain what "zero-
copy" means for the memoryview step.

**3. Overflow deliberately.** Put a value just inside a `'h'` (int16) array, then one just outside, and
observe the `OverflowError`. Explain why an array element can overflow when a Python `int` cannot (Chapter
35).

**4. Pin and fail.** Hold a live `memoryview` onto an array and try to `append`. Observe the `BufferError`,
release the view, and show the append works. Explain what the view was protecting (Chapter 37).

**5. The design question.** `array` stores numbers compactly but does not vectorize computation. Argue what
`array` is *for*, given that NumPy exists. Your answer must address the standard-library-only constraint
(no third-party dependency), the buffer-protocol interop that lets `array` feed `struct`/sockets/NumPy, and
why storing in an `array` and then looping in Python is usually the wrong shape.

---

## 39.7 Summary and cross-references

- An **`array.array`** is a compact, fixed-width, single-type numeric sequence: raw values stored inline,
  no per-element object, type enforced on insertion.
- It **exports the buffer protocol** (Chapter 37): zero-copy `memoryview`, `tobytes`/`frombytes`, and
  interop with `struct`, sockets, and NumPy without a copy.
- **Measured:** a million 64-bit ints cost **40 bytes/element in a `list`** (pointer + int object) versus
  **8.2 bytes/element in an `array('q')`**, a **4.9x** reduction, the object model's cost made visible.
- **Use `list`** for heterogeneous elements and per-element objects (the default); **use `array`** for
  large homogeneous numeric data where memory and contiguous layout matter, and as the on-ramp to NumPy
  (**Deep T**). `array` stores; it does not vectorize.

**Cross-references.** `list` structure and the object header → Chapter 4 and Deep A. The buffer protocol →
Chapter 37. Fixed-width numbers and overflow → Chapter 35. Specialized containers → Chapter 32. NumPy and
vectorized computation → Deep T. Serialization → Deep R. The numeric-data seam → Deep U.
