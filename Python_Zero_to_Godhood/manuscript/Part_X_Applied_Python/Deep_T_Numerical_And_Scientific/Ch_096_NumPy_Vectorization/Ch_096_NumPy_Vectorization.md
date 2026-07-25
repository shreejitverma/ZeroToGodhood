# Chapter 96: NumPy Vectorization

Everything this book has said about Python's per-element cost, an `int` is a heap object, a loop runs bytecode
per iteration, attribute and method lookups happen every time, converges here into one number. Summing the
squares of a million integers in a Python loop takes ~22 ms; the same computation as a NumPy vectorized
expression, `(arr * arr).sum()`, takes **0.67 ms**, **32x faster**. And the worst way, a Python loop that
*indexes* a NumPy array element by element, `arr[i]`, takes **119 ms**, **177x slower** than the vectorized
form, because it pays the Python-per-element cost *and* unboxes a NumPy scalar each step. NumPy exists to move
numeric computation *out* of the Python interpreter and into *compiled C loops over contiguous typed memory*,
and that move is the difference between numeric Python being unusably slow and being fast enough to underlie
scientific computing, data analysis, and machine learning.

This chapter opens **Deep T** (numerical and scientific Python) with vectorization: what an ndarray is, why
whole-array operations run in C, and why looping element-by-element over an array is the cardinal NumPy sin. It
is the payoff of the `array.array` on-ramp (Chapter 39) and the answer to the object-model overhead measured
throughout the book.

## Section index

- **96.1** The ndarray and vectorized operations
- **96.2** Why the loop is slow and the array is fast
- **96.3** Measurement: vectorized vs looping
- **96.4** Edges and failure modes
- **96.5** Connections
- **96.6** Exercises
- **96.7** Summary and cross-references

Listings live under `code/ch096/` and are re-executed by `make verify` on both interpreters (both with NumPy
2.1.3).

---

## 96.1 The ndarray and vectorized operations

```python
# code/ch096/l01_vectorization.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- an ndarray: contiguous, fixed dtype, a shape ---
  array   : [1, 2, 3, 4, 5, 6]
  dtype   : int64
  shape   : (6,), contiguous: True
--- vectorized elementwise math (whole array at once, in C) ---
  a * 2       : [2, 4, 6, 8, 10, 12]
  a * a       : [1, 4, 9, 16, 25, 36]
  a > 3       : [False, False, False, True, True, True]
--- reductions run in C too ---
  a.sum()     : 21
  a.mean()    : 3.5
  (a * a).sum(): 91   (sum of squares)
--- broadcasting: a scalar (or smaller array) applies across the array ---
  matrix      :
[[0 1 2]
 [3 4 5]]
  m + 10      :
[[10 11 12]
 [13 14 15]]
  column sums : [3, 5, 7]
--- same result as a Python loop, computed in C (benchmark: tens of x faster) ---
  vectorized (big*big).sum() == python loop : True
```

An **ndarray** is a block of *contiguous, fixed-width* numbers, `int64` here, with a `shape` and a `dtype`,
exactly the compact layout of `array.array` (Chapter 39) generalized to N dimensions. The crucial addition is
that *math is defined on the whole array*: `a * 2`, `a * a`, `a > 3` apply the operation to *every element* and
return a new array, and reductions (`sum`, `mean`) collapse the array to a scalar. **Broadcasting** extends this:
a scalar (or a smaller array) is applied across a larger one, `m + 10` adds 10 to every element, `m.sum(axis=0)`
sums each column, without any explicit loop in Python.

Every one of these operations runs as a *single compiled C loop* over the contiguous memory. `a * a` does not
execute Python bytecode six times; it calls a C function that multiplies the whole buffer. The last line
confirms the payoff is *correct*: the vectorized `(big * big).sum()` equals the Python-loop result exactly, same
answer, computed in C.

---

## 96.2 Why the loop is slow and the array is fast

The speed difference is the accumulation of every per-element cost the book has measured, now paid a million
times. A Python loop `for x in lst: total += x*x` does, *per element*: fetch the next `int` *object* (a boxed
heap object, Chapter 4), execute the `*` and `+=` *bytecode* (dispatched by the interpreter, Chapters 17, 50),
create a *new* `int` object for each intermediate result, and manage reference counts. That is dozens of
interpreter operations and several allocations *per element*, so a million elements is tens of millions of
interpreter operations.

The vectorized `(arr * arr).sum()` does *none* of that per element. `arr * arr` is a *single* C function call
that walks the contiguous `int64` buffer in a tight machine loop, multiplying raw 64-bit integers (no objects,
no boxing, no bytecode), and `.sum()` is another C loop. The whole computation is two C passes over memory,
which the CPU does at memory-bandwidth speed, often with SIMD (Chapter's later topic) processing multiple
elements per instruction. The Python interpreter runs *twice* (to call the two C functions), not two million
times.

This is why the **worst** case is a Python loop that *indexes* a NumPy array (`arr[i]`): it pays the full
Python-per-element interpreter cost *and*, at each step, *unboxes* a NumPy scalar into a Python object (an extra
allocation the list loop does not even do), making it slower than the pure-Python list loop (§96.3). The rule
that defines idiomatic NumPy: **express computation as whole-array (vectorized) operations; never loop element by
element over a NumPy array in Python.** If you find yourself writing `for i in range(len(arr)): arr[i] = ...`, you
are using NumPy the slowest possible way; there is almost always a vectorized expression (elementwise ops,
broadcasting, reductions, `np.where`, fancy indexing) that does the same thing in C.

---

## 96.3 Measurement: vectorized vs looping

**Methodology.** `code/ch096/bench_vectorization.py`. Sum of squares over 1,000,000 `int64`s: vectorized
`(arr*arr).sum()`, a Python loop over a `list`, and a Python loop *indexing* the NumPy array. `min` per run.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64, NumPy 2.1.3.

| sum of squares, 1,000,000 ints | min per run | vs vectorized |
|---|---|---|
| vectorized `(arr*arr).sum()` | **0.67 ms** | 1.0x |
| Python loop over a `list` | **21.6 ms** | **32x slower** |
| Python loop *indexing* the array | **119 ms** | **177x slower** |

The vectorized form is **32x** faster than the pure-Python list loop and **177x** faster than the array-indexing
loop. The ordering is the lesson: vectorized (C loop, no per-element Python) is fastest; a Python loop over a
plain `list` is 32x slower (per-element interpreter overhead and boxing); and a Python loop *indexing the NumPy
array* is *slower still* (177x), because it adds NumPy-scalar unboxing to the per-element Python cost, the
anti-pattern that makes NumPy *slower* than a list if used wrongly.

The rule: **vectorize.** Reach for whole-array operations, elementwise math, broadcasting, reductions, boolean
masks, `np.where`, `np.dot`/`@`, and let NumPy run the loop in C; never write a Python `for` loop over array
elements. The 32-177x here is per-operation and compounds across a real computation (a data pipeline, a model's
forward pass), which is why numeric Python is built *entirely* on this move: the interpreter orchestrates, and
the arithmetic happens in compiled code over contiguous memory. (The exact multiple depends on the operation and
data size, larger arrays amortize NumPy's fixed call overhead and widen the gap; tiny arrays can even favor a
plain loop, §96.4, but for any real numeric workload, vectorization wins by orders of magnitude.)

---

## 96.4 Edges and failure modes

**Looping element-by-element over an array.** §96.2. The cardinal sin, slower than a `list` loop. Replace with a
vectorized expression (elementwise ops, broadcasting, `np.where`, reductions).

**Vectorizing tiny arrays.** NumPy operations have fixed call overhead (a few microseconds); for a handful of
elements, a plain Python loop or scalar arithmetic can be faster. Vectorization wins at *scale*; do not NumPy-ify
a 3-element computation in a hot loop.

**Intermediate-array memory.** `(arr*arr).sum()` allocates a full temporary `arr*arr` array. For huge arrays this
is O(n) extra memory; `np.dot(arr, arr)` or `np.einsum` computes the sum of products without the temporary. Watch
for large intermediates in chained expressions.

**dtype overflow.** A vectorized `int64` operation *overflows silently* (wraps) where Python's arbitrary-precision
`int` would not (Chapter 35). `arr * arr` on large values can wrap to negative. Choose a wide enough dtype, or
use `float64`, and know NumPy's fixed-width arithmetic can overflow.

**Accidental copies vs views.** Slicing an ndarray returns a *view* (shares memory, Chapter 37/44), but fancy
indexing (`arr[mask]`, `arr[[1,3,5]]`) returns a *copy*. Mutating a view changes the original; mutating a copy
does not. Know which you have (`.base`), a source of both bugs and surprise memory use.

**Mixing Python and NumPy scalars.** Pulling values out with `arr[i]` (a NumPy scalar) into Python arithmetic
reintroduces per-element overhead and boxing. Keep data in arrays and operate on arrays; extract scalars only at
the boundary.

---

## 96.5 Connections

**Backward.** The contiguous typed buffer is `array.array` (Chapter 39) and the buffer protocol (Chapter 37); an
ndarray exposes it, so NumPy and Python buffers interoperate zero-copy. The per-element Python cost NumPy avoids
is the object model (Chapter 4), bytecode dispatch (Chapters 17, 50), and int boxing (Chapter 35). The fixed-
width overflow is Chapter 35.

**Forward.** Broadcasting rules, memory layout (strides, C vs Fortran order), views vs copies, ufuncs, SIMD, and
GPU offload are the rest of **Deep T**. `numpy.memmap` (array-backed by a memory-mapped file) is Chapter 44's
`mmap` for arrays. SciPy, pandas, and Arrow build on the ndarray.

**Across books.** Vectorization is how Book II makes numeric work fast enough to feed **Book III**. A **Book III**
ML/retrieval pipeline represents embeddings, features, and scores as ndarrays and computes with vectorized
operations and matrix products, so a batch of thousands of vectors is processed in a few C calls, not thousands
of Python loops, and the same code offloads to SIMD or a GPU (Deep T). The §96.2 loop-vs-vectorize gap is the
reason numeric Python code *must* be array-oriented, which **Deep U** and **Deep T** enforce on every hot numeric
path.

---

## 96.6 Exercises

**1. Vectorize a loop.** Take a Python loop computing an elementwise result (e.g. `y = a*x + b` over arrays) and
rewrite it as a vectorized NumPy expression. Confirm identical results and measure the speedup.

**2. Reproduce the anti-pattern.** Run §96.3's benchmark and confirm the array-indexing loop is the *slowest*,
slower than a list loop. Explain the extra unboxing cost.

**3. Broadcast.** Use broadcasting to add a per-column offset to a 2D array without a loop, and to compute
row/column reductions. Explain how broadcasting avoids materializing the offset array.

**4. View vs copy.** Slice an array (view) and fancy-index it (copy), mutate each, and observe which changes the
original. Explain the difference and its memory implication.

**5. The design question.** NumPy moves numeric computation from the Python interpreter into compiled C loops
over contiguous memory. Argue why this is the only way numeric Python is fast, using the per-element costs the
book measured. Your answer must use the §96.3 measurement and explain why element-by-element array loops are the
worst case.

---

## 96.7 Summary and cross-references

- A **NumPy ndarray** is a contiguous, fixed-dtype block of numbers with math defined on the **whole array**;
  elementwise ops, broadcasting, and reductions run as **single compiled C loops** over memory, no Python object
  or bytecode per element.
- **Measured:** sum of squares over a million ints is **32x** faster vectorized than a Python `list` loop, and
  **177x** faster than a Python loop *indexing* the array (the anti-pattern that adds scalar unboxing).
- **Vectorize:** express computation as whole-array operations; **never loop element-by-element over a NumPy
  array in Python**. Vectorization wins at scale; tiny arrays can favor a plain loop.
- **Edges:** watch intermediate-array memory, fixed-width `int` overflow (unlike Python `int`), and view-vs-copy
  semantics.

**Cross-references.** `array.array` and the buffer protocol → Chapters 39, 37. Object-model/bytecode overhead →
Chapters 4, 17, 50. Fixed-width int overflow → Chapter 35. `mmap`/`memmap` → Chapter 44. Broadcasting, strides,
SIMD, GPU, SciPy/Arrow → the rest of Deep T. The numeric hot-path seam → Deep U.
