# Chapter 43: Calling C with `ctypes`

Deep A opened with a number: a million Python integers cost 38 MB against C's 8 MB, because every value carries a `PyObject` header (Chapter 19).
Deep A closed by naming the escape hatch, "crossing to C", as **Deep M**'s subject.
This is Deep M, and it opens at the most accessible crossing: `ctypes`, the standard library's **foreign function interface**, which loads a shared C library and calls its functions directly, with no compiler, no build step, and no C source of your own.
It is how a pure-Python program reaches an existing C library, a codec, a crypto primitive, a hardware driver, a numerical kernel, and it is the gentlest introduction to the boundary that the rest of this volume (the C-API, extension modules, the ABI) explores in depth.

The whole discipline of the boundary is **types**, and that is the chapter's spine.
Python has one unbounded `int` and one `float`; C has a family of fixed-width types (`int` is 32 bits, `unsigned char` is a wrapping 8-bit byte, `double` is 64 bits), and it lays structs out as contiguous typed memory.
Calling C correctly means declaring those types so `ctypes` can marshal Python values into the right C representation and back, and it means accepting C's semantics on the other side: fixed widths, wrapping arithmetic, explicit memory layout, pointers.
The measurement makes the boundary's *cost* concrete, a `ctypes` call is ~**10.8x** a builtin, because every call marshals across, which tells you exactly what `ctypes` is for (calling into C libraries that do real work per call) and what it is not (speeding up small operations call-by-call).

**This is the canonical home for `ctypes` and the FFI boundary.**
It is the payoff of Deep A's "escape the header" thread (Chapter 19), uses the fixed-binary-layout ideas of Deep Q (`struct`, the buffer protocol, Chapter 37, which it references rather than re-derives), and opens **Deep M**, whose later chapters cover the C-API, writing extension modules, and the ABI.

## Section index

- **43.1** Calling C functions, and C's fixed-width types
- **43.2** Structures and pointers: C memory layout from Python
- **43.3** Measurement: the cost of the FFI boundary
- **43.4** Edges and failure modes
- **43.5** Connections
- **43.6** Exercises
- **43.7** Summary and cross-references

Listings live under `code/ch124/` and are re-executed by `make verify` on both verification interpreters.

---

## 43.1 Calling C functions, and C's fixed-width types

```python
# code/ch124/l01_calling_c.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- call C functions from libc, declaring their signatures ---
  libc.strlen(b'hello') : 5
  libc.abs(-42)         : 42
--- C types have FIXED widths (unlike Python's unbounded int) ---
  sizeof(c_int)    : 4 bytes
  sizeof(c_double) : 8 bytes
  sizeof(c_uint8)  : 1 byte
--- C arithmetic WRAPS at the type's width (no arbitrary precision) ---
  c_uint8(255).value + 1 = 0   (wraps to 0; Python int would be 256)
  c_int8(127).value + 1  = -128   (wraps to -128, two's complement)
--- the rule ---
  ctypes calls C directly; declare argtypes/restype so values marshal
  correctly, and remember C types are fixed-width and wrap on overflow
```

`ctypes.CDLL(...)` loads a shared library (here the C standard library) and exposes its functions as attributes.
Calling one requires declaring its **signature**: `restype` (the return type) and `argtypes` (the argument types).
`libc.strlen` returns a `c_size_t` and takes a `c_char_p` (a C string); `libc.abs` returns and takes a `c_int`.
With those declared, `ctypes` marshals the Python `bytes`/`int` into the C representation, calls the function, and marshals the result back, `strlen(b'hello')` is `5`, `abs(-42)` is `42`.
Declaring the types is not optional politeness: without correct `argtypes`/`restype`, `ctypes` guesses (defaulting to `int`), and on a 64-bit platform a function returning a pointer or a `long` guessed as `int` returns a *truncated, wrong* value, a silent, dangerous bug.

The second half is the conceptual heart: **C types are fixed-width**, and their arithmetic **wraps**.
`sizeof(c_int)` is 4 bytes, `c_double` is 8, `c_uint8` is 1, these are the machine widths Chapter 19 contrasted with Python's header-carrying, arbitrary-precision `int`.
And crossing into those types means crossing into C's overflow semantics: `c_uint8(255).value + 1` is **0** (an 8-bit unsigned type wraps), and `c_int8(127).value + 1` is **-128** (two's-complement signed overflow).
Python's `int` would give `256` and `128`, it never overflows.
So the boundary is not just a performance frontier; it is a *semantic* one: on the C side, integers have a width and wrap, and code that crosses over must respect that or produce silently wrong numbers.
This is the price and the point of leaving the `PyObject` world: you get C's compact, fast, fixed-width values, and you take on C's rules for them.

---

## 43.2 Structures and pointers: C memory layout from Python

Calling functions is half of FFI; the other half is building the *data* C expects, and that means laying out memory exactly.

```python
# code/ch124/l02_structures.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a Structure lays out fields exactly like a C struct ---
  Point(3, 4).x, .y : 3, 4
  sizeof(Point)     : 8 bytes   (two 4-byte ints)
--- fields are mutable, in place ---
  after p.x = 100   : 100
--- structs nest and their size is the sum (plus any alignment) ---
  Rect.topleft.x, width, height : 0, 640, 480
  sizeof(Rect)      : 16 bytes   (Point + 2 ints)
--- pointers: pass a pointer so C can read/write your memory ---
  ptr.contents.value       : 10
  after *ptr = 20, n.value : 20
```

A `ctypes.Structure` with `_fields_` declares a struct whose memory layout **matches the equivalent C struct**: the fields sit contiguously, in declaration order, with the platform's alignment.
`Point` (two `c_int`s) is `8` bytes, exactly `2 * sizeof(int)`; it reads and writes like a Python object (`p.x = 100`) but *is* a block of C-laid-out memory.
Structs **nest** as in C: `Rect` embeds a `Point` and adds two ints, and its size is the sum (`16` bytes here), the same accounting Chapter 19 applied to `PyVarObject` and Deep Q's `struct` applies to binary formats.
This is how you hand C a struct it understands: build the `ctypes.Structure`, fill its fields, pass it (or its address) to the function.

**Pointers** are the second C idiom, and `ctypes` models them directly.
`ctypes.pointer(n)` makes a pointer to a `c_int`; `.contents.value` dereferences it, and assigning through it (`ptr.contents.value = 20`) **writes back into `n`'s memory** (`n.value` becomes `20`).
This is the pervasive C pattern of "pass a pointer for the function to fill in", `int result; parse(input, &result);`, where the caller allocates and the callee writes.
In `ctypes` you allocate the `c_int` (or struct or buffer), pass `ctypes.byref(...)` or a `pointer(...)`, and read the result out afterward.
Together, structures (C's aggregate memory) and pointers (C's indirection) let Python construct and manipulate exactly the memory a C API expects, which is what makes `ctypes` able to drive real C libraries and not just call leaf functions.

---

## 43.3 Measurement: the cost of the FFI boundary

**Methodology.** `code/ch124/bench_ffi.py`.
A `ctypes` call to `libc.abs` versus Python's builtin `abs`, both on `-42`, `min` of 5 runs, 5,000,000 calls.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| call `abs(-42)` | ns/call | vs builtin |
|---|---|---|
| builtin `abs` | 15.3 | 1.0x |
| `ctypes` `libc.abs` | 165.1 | **10.8x** |

The `ctypes` call is **10.8x** slower than the builtin (10.2x on 3.14.6), and the reason is the boundary itself, not the C code.
C's `abs` is a single machine instruction; it is not slow.
But *each* `ctypes` call must **marshal** the argument (Python `int` object to a C `int`), invoke the foreign function through `libffi`, and marshal the result back (C `int` to a Python `int` object).
That fixed per-call cost dominates completely for a function this small, the crossing costs far more than the work.

This measurement is the whole design guidance for `ctypes`, and for FFI in general.
**Use `ctypes` to call into C libraries where each call does substantial work** that amortizes the boundary: decode a JPEG, hash a megabyte, run a numerical solve, talk to a device.
There, the C function's real work dwarfs the ~150 ns crossing, and you get C's speed for the heavy part.
**Do not use `ctypes` to replace a small Python operation call-by-call**, wrapping `abs` or a per-element arithmetic op in `ctypes` makes it *slower*, because you pay the boundary on every tiny call.
And when you *do* want to move a hot **loop** into C, the correct pattern is not "call the C function per element" but "**pass the whole buffer once**": hand C a pointer to the entire array (via the buffer protocol, Deep Q Chapter 37, or a `ctypes` array) so a *single* crossing does *all* the work, which is exactly how NumPy and the buffer protocol beat per-element Python (Chapter 19's escape hatch, realized).
The rule: **amortize the boundary, cross rarely with a lot of work each time, never often with a little.**
The FFI is a door between two worlds, and doors are cheap to walk through occasionally and expensive to walk through constantly.

---

## 43.4 Edges and failure modes

**Declare `argtypes`/`restype`, always.** §43.1.
Without them `ctypes` assumes `int`, which truncates pointers and `long`s on 64-bit platforms, a silent wrong-value (or crash) bug. Declaring signatures is mandatory, not optional.

**C arithmetic wraps; Python's does not.** §43.1.
Values crossing into C types (`c_int`, `c_uint8`) overflow at the type width. Code that assumes Python's arbitrary precision produces wrong results at the boundary.

**`ctypes` bugs crash the interpreter.**
A wrong signature, a bad pointer, a buffer overrun, or a use-after-free in `ctypes` is a **segfault** of the whole Python process, not a Python exception. `ctypes` bypasses Python's safety; you are writing C-level code with C-level consequences. There is no traceback for a segfault.

**Memory ownership is manual.**
If a C function returns allocated memory, *you* must free it (via the library's free function through `ctypes`), or you leak. If you pass Python-owned memory to C that keeps it, you must keep a reference alive or it is freed under C (a use-after-free). The refcounting of Chapter 31 does not extend across the boundary.

**Struct layout depends on alignment and packing.** §43.2.
Default `ctypes.Structure` uses the platform's natural alignment (padding fields to their boundaries), so `sizeof` may exceed the sum of field sizes. To match a packed C struct or a wire format, set `_pack_`, and match the exact layout the C side uses (Deep Q's `struct` format).

**The FFI boundary has ~10x per-call overhead.** §43.3.
Cross rarely with much work each time. Never wrap a tiny operation in `ctypes` expecting a speedup.

**Strings and encodings need care.**
`c_char_p` is bytes (a C `char*`); passing a `str` requires encoding first (Deep D). A C string is NUL-terminated, so embedded NULs truncate. `c_wchar_p` is for wide strings, with its own platform width.

**Calling conventions and the GIL.**
`CDLL` uses the C calling convention; Windows `stdcall` needs `WinDLL`. By default a `ctypes` call *releases the GIL* around the C call (good for blocking C work, but the C code must be thread-safe and must not touch Python objects without re-acquiring).

---

## 43.5 Connections

**Backward.**
`ctypes` is the realization of Chapter 19's "escape the `PyObject` header": C's fixed-width types are the compact values without per-element objects. The struct layout of §43.2 is Deep Q's `struct`/binary-layout (Chapter 37) and mirrors Chapter 19's `PyVarObject` accounting. Manual memory ownership across the boundary is where Chapter 31's reference counting stops.

**Forward.**
The **buffer protocol** and `memoryview` (Deep Q Chapter 37), the zero-copy way to hand C a whole array so one call does a loop's work (§43.3's amortization), are the companion to per-call FFI. The **C-API** proper (`PyObject *` at the C level, writing extension modules, `Py_INCREF`/`Py_DECREF` from C), the **ABI** (the stable-ABI `abi3`), and higher-level FFI tools (`cffi`, and the compiled paths of Cython/pybind11/PyO3) are the rest of **Deep M**. Releasing the GIL around C calls connects to the concurrency volumes (Deep E, free-threading).

**Across books.**
`ctypes` is one way **Book I** reaches performance-critical or hardware-adjacent C: a market-data feed's C decoder, a vendor's C pricing library, an OS call not exposed by the standard library. The order-book system uses FFI at exactly the §43.3 granularity, one crossing that does a lot (decode a whole message batch, run a C matching kernel over an array), never a crossing per tiny operation, and it passes buffers by pointer (Deep Q's buffer protocol) so the C side processes the whole block in one call, the amortization this chapter measures turned into the architecture of the boundary.

---

## 43.6 Exercises

**1. Call C correctly.** Reproduce §43.1: load libc, declare and call `strlen` and `abs`. Then call one *without* declaring `restype`/`argtypes` and, on a function returning a pointer or `long`, observe a wrong (truncated) value. Explain why declaring signatures is mandatory.

**2. Feel the overflow.** Show `c_uint8` and `c_int8` wrapping at their bounds, and contrast with Python `int`. Explain what "crossing into C types" means for arithmetic, and one bug it could cause.

**3. Build a struct.** Reproduce §43.2's `Point`/`Rect`. Confirm the sizes. Then add a `_pack_ = 1` and a mixed-width field set and show the size change from alignment. Explain how you would match a specific C struct's layout.

**4. Measure and amortize.** Reproduce §43.3. Then write a version that sums an array two ways: a `ctypes` call *per element*, and a single C call over the whole `ctypes` array (or a `memoryview`). Show the per-element version is slow and the whole-buffer version is fast. Explain the amortization.

**5. The design question.** `ctypes` bypasses Python's safety (a bug segfaults the process) and pays ~10x per call. Argue when FFI is nonetheless the right tool (§43.3's "substantial work per call"), and when a C extension (compiled, Deep M) or staying in Python is better. What does the ~10x boundary cost imply about *where* to draw the Python/C line in a system?

---

## 43.7 Summary and cross-references

- **`ctypes`** is the standard-library **FFI**: it loads a shared C library and calls its functions directly, no compiler needed. Correct use requires declaring **`argtypes`/`restype`** so values marshal to the right C types (omitting them truncates pointers/longs, a silent bug).
- **C types are fixed-width and wrap on overflow** (`c_uint8(255)+1 == 0`), unlike Python's unbounded `int`, crossing the boundary is a *semantic* frontier, not just a performance one.
- **`ctypes.Structure`** mirrors C struct memory layout (contiguous, typed, aligned); **pointers** (`pointer`/`byref`) let C read and write your memory, the standard "pass a pointer to fill in" idiom.
- **Measured:** a `ctypes` call is **10.8x** a builtin (165 vs 15 ns), because each call marshals across the boundary. Use FFI where **each call does substantial work** (amortizing the crossing); to move a hot *loop* into C, **pass the whole buffer once** (Deep Q's buffer protocol), never call per element.
- **Edges:** `ctypes` bugs **segfault** the process (no traceback); memory ownership is manual (refcounting does not cross); struct alignment/packing must match the C side; `ctypes` releases the GIL around the call.

**Cross-references.** Escaping the `PyObject` header → Chapter 19. Binary layout, `struct`, buffer protocol, `memoryview` → Deep Q (Chapter 37). Reference counting (stops at the boundary) → Chapter 31. The C-API, extension modules, the stable ABI, `cffi`/Cython → the rest of Deep M. Releasing the GIL for C calls → Deep E / free-threading.
