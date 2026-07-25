# Chapter 100: Matrix Multiply and BLAS

Matrix multiplication is the single most important operation in numerical computing, linear algebra solvers,
physics simulations, and every neural network's forward and backward pass are, at bottom, matrix multiplies, and
it is where NumPy's "let compiled code do the work" reaches its apotheosis. `A @ B` does *not* run a loop in
Python, or even a plain C loop. It dispatches to a **BLAS** library (OpenBLAS, MKL, Accelerate), decades of
hand-tuned assembly that blocks the computation for cache, vectorizes it with SIMD, and runs it across multiple
threads, reaching a large fraction of the CPU's peak floating-point throughput: **184 GFLOPS** on a 512x512
multiply here. Against a naive Python triple loop, the same 128x128 multiply is **4,848x faster** (77
microseconds versus 374 milliseconds), and the gap widens with size. This is the ultimate case of the book's
recurring rule, the Python interpreter *orchestrates*; the arithmetic happens in compiled, vectorized,
parallelized code.

This chapter continues **Deep T** with matrix multiply and BLAS: the `@` operator, why it is thousands of times
faster than a loop, and why you *never* hand-write dense linear algebra. It is the numerical foundation
everything from `numpy.linalg` to PyTorch is built on.

## Section index

- **100.1** `@`, `np.dot`, and BLAS
- **100.2** Why BLAS is thousands of times faster
- **100.3** Measurement: BLAS vs a triple loop
- **100.4** Edges and failure modes
- **100.5** Connections
- **100.6** Exercises
- **100.7** Summary and cross-references

Listings live under `code/ch100/` and are re-executed by `make verify` on both interpreters (both with NumPy
2.1.3).

---

## 100.1 `@`, `np.dot`, and BLAS

```python
# code/ch100/l01_matmul.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- @ is the matrix product (rows dot columns) ---
  A =
[[1 2]
 [3 4]]
  B =
[[5 6]
 [7 8]]
  A @ B =
[[19 22]
 [43 50]]
  (top-left = 1*5 + 2*7 = 19)
--- @ (matrix product) is NOT * (elementwise) ---
  A * B (elementwise) =
[[ 5 12]
 [21 32]]
  A @ B (matrix)      =
[[19 22]
 [43 50]]
--- np.dot / np.matmul are the same operation ---
  np.dot(A, B) == A @ B : True
--- a bigger multiply is dispatched to BLAS (fast, multithreaded) ---
  (X @ Y) matches einsum : True
  NumPy is built against a BLAS library : True
--- the rule ---
  use @ / np.dot / np.matmul for matrix products (BLAS, thousands of x
  faster than a loop); never hand-write the triple loop
```

`A @ B` is the **matrix product**: each output element is a *dot product* of a row of `A` with a column of `B`
(top-left = `1*5 + 2*7 = 19`). The `@` operator (PEP 465), `np.dot`, and `np.matmul` are the same operation. The
critical distinction the second block draws: **`@` is not `*`**. `A * B` is *elementwise* multiplication (each
element times the corresponding element), a completely different, and far cheaper, operation. Confusing them is a
common bug: `*` where you meant `@` silently computes the wrong thing (and only errors if the shapes happen to be
incompatible for elementwise).

The bottom block confirms the machinery: `A @ B` gives the same result as an explicit `einsum` (the same math, a
different route), and NumPy is built against a BLAS library, which is where a real-size `@` executes.

---

## 100.2 Why BLAS is thousands of times faster

Matrix multiply is O(n^3): an n x n multiply does 2n^3 floating-point operations (a multiply and an add per
inner-product term). A **naive triple loop** runs those 2n^3 operations in the Python interpreter, one boxed
`float` multiply-add at a time, with all the per-operation overhead the book has measured (object access,
bytecode dispatch, allocation). For n=128 that is ~4 million iterations of Python-level arithmetic, hundreds of
milliseconds.

**BLAS** (Basic Linear Algebra Subprograms) is the opposite in every dimension. Its matrix-multiply routine
(`dgemm` for `float64`) is *decades* of optimization: it **blocks** the matrices into tiles sized to fit the
CPU's cache levels (so data is reused while hot, not re-fetched from RAM), **vectorizes** the inner loops with
SIMD (processing 4-8 floats per instruction), **unrolls and schedules** instructions to keep the CPU's
floating-point units saturated, and **parallelizes** across all cores. The result reaches a large fraction of the
CPU's *theoretical peak* FLOPS, 184 GFLOPS here (§100.3), where the Python loop achieves a few *mega*-FLOPS. The
ratio, thousands of times, is not NumPy being "a faster loop"; it is the difference between naive interpreted
arithmetic and the most heavily optimized numerical kernel in computing.

The rule: **use `@` / `np.dot` / `np.matmul` for matrix products, and `numpy.linalg` (which calls LAPACK, built on
BLAS) for solves, decompositions, and inverses; never hand-write dense linear algebra.** There is no scenario
where your triple loop (or even your hand-tuned C) beats BLAS, it is the product of specialists optimizing for
specific CPUs over decades. When your computation is a matrix multiply, *express it as one* (reshape and `@`,
`einsum`, batched `matmul`) so it goes through BLAS. This is why numeric Python is fast: the heavy operations
delegate to BLAS/LAPACK, and the interpreter just calls them.

---

## 100.3 Measurement: BLAS vs a triple loop

**Methodology.** `code/ch100/bench_matmul.py`. A 128x128 matrix multiply via `A @ B` (BLAS) versus a naive Python
triple loop, plus the BLAS throughput on a 512x512. `min` per run; results checked equal (`allclose`). CPython
3.13.5, Apple M3 Pro, macOS 27.0, arm64, NumPy 2.1.3.

| 128x128 matrix multiply | time | vs BLAS |
|---|---|---|
| BLAS `A @ B` | **77 us** | 1.0x |
| naive Python triple loop | **374 ms** | **4,848x slower** |
| BLAS 512x512 throughput | **184 GFLOPS** | - |

BLAS does the 128x128 multiply in **77 microseconds**; the naive triple loop takes **374 milliseconds**,
**4,848x** slower, for the *identical* result. On a 512x512, BLAS sustains **184 GFLOPS**, hundreds of billions of
floating-point operations per second, by using cache blocking, SIMD, and multiple threads. The exact multiple
depends on size and the BLAS build (a multithreaded MKL/OpenBLAS on more cores widens it further; the gap grows
with n because O(n^3) work amplifies the per-operation Python overhead), but the order, *thousands* of times, is
the constant.

The rule: **never hand-write matrix multiply or dense linear algebra; express it as `@`/`np.dot`/`np.linalg` and
let BLAS/LAPACK run it.** This is the strongest form of the book's central numeric lesson (Chapter 96): the
interpreter is thousands of times slower than compiled vectorized code for arithmetic-heavy work, and matrix
multiply, the most arithmetic-heavy operation of all, shows the largest gap. Any numeric code that reduces to
matrix operations (a linear layer, a covariance, a projection, a solve) should be *written* as matrix operations,
not loops, so it reaches BLAS. The performance of scientific Python, and of every ML framework, rests on this one
delegation.

---

## 100.4 Edges and failure modes

**`*` where you meant `@`.** §100.1. `A * B` is elementwise, `A @ B` is the matrix product, completely different
results (and `*` silently succeeds if shapes broadcast). Use `@` for matrix multiply; double-check the operator.

**Hand-writing linear algebra.** §100.2. A triple loop (or a Python-level "optimized" version) is thousands of
times slower than BLAS and cannot compete. Use `@`/`np.dot`/`np.linalg`.

**Not shaping a computation as a matmul.** A loop of vector dot products, or a batch of small multiplies done one
at a time, misses BLAS. Batch them into a single `@`/`matmul` (or `einsum`) so the whole thing is one BLAS call.

**dtype and BLAS.** BLAS is fastest on `float32`/`float64` (and their complex forms). An `int` or `object` matrix
`@` does *not* use BLAS (NumPy falls back to a slow generic path). Keep matrices in float dtypes for the fast
path.

**Non-contiguous inputs.** BLAS wants contiguous (or cleanly strided) memory; a `@` on awkwardly-strided views may
trigger a copy first (Chapter 99). Usually fine, but for hot code ensure contiguous inputs
(`np.ascontiguousarray`).

**Thread oversubscription.** BLAS is multithreaded by default; running BLAS calls inside your *own* thread/process
pool (Chapters 8, 48) can oversubscribe cores (BLAS threads x your threads), slowing everything. Control it
(`OMP_NUM_THREADS`, `threadpoolctl`) when combining BLAS with your own parallelism.

**Numerical stability.** For `A^-1 @ b`, prefer `np.linalg.solve(A, b)` over computing the inverse, it is more
accurate and faster. BLAS/LAPACK give the fast *and* numerically sound routines; use the right one
(`solve`, `lstsq`, `qr`, `svd`), not a manual inverse.

---

## 100.5 Connections

**Backward.** Vectorization (Chapter 96) is the elementwise version of this; matrix multiply is the O(n^3) case
where the compiled-vs-interpreted gap is largest. dtype's effect on the BLAS fast path is Chapter 98. Contiguity
and views are Chapter 99. Thread oversubscription connects to Chapters 8, 48.

**Forward.** `numpy.linalg`/LAPACK (solves, eigen, SVD), `einsum` (general tensor contraction), and batched
`matmul` are Deep T. GPU matrix multiply (cuBLAS) and the same operation in PyTorch/JAX are Deep T ML topics.
Sparse matrices (SciPy) for non-dense problems are Deep T.

**Across books.** BLAS matrix multiply is the engine under **Book III**. Every dense layer of a **Book III**
model, every attention score matrix, every embedding projection and similarity search, is a `@`/`matmul` that
runs on BLAS (CPU) or cuBLAS (GPU), which is why a model with billions of parameters is even tractable, the
arithmetic is done by decades-optimized kernels, not Python. The §100.3 thousands-fold gap is the reason
**Book III** code is written as matrix operations end to end, and **Deep T** and **Deep U** enforce that any
numeric hot path reduce to BLAS calls.

---

## 100.6 Exercises

**1. Verify and time.** Reproduce §100.3: confirm `A @ B` equals a naive triple loop, then time both. Explain why
BLAS is thousands of times faster, in terms of blocking, SIMD, and threads.

**2. `@` vs `*`.** Show `A * B` (elementwise) and `A @ B` (matrix) give different results, and construct a case
where `*` silently succeeds with the wrong answer. Explain the distinction.

**3. Batch into one matmul.** Take a loop computing many vector dot products and rewrite it as a single matrix
multiply. Time both. Explain how batching reaches BLAS.

**4. Solve vs invert.** Solve `A x = b` with `np.linalg.solve` and with `np.linalg.inv(A) @ b`, and compare speed
and accuracy. Explain why `solve` is preferred.

**5. The design question.** NumPy delegates matrix multiply to BLAS rather than implementing it. Argue why, and
what it means for how you write numeric code. Your answer must use the §100.3 measurement (and GFLOPS), the
optimizations BLAS applies, and the "express it as a matmul" rule.

---

## 100.7 Summary and cross-references

- **`A @ B`** (matrix product; = `np.dot`/`np.matmul`) dispatches to a **BLAS** library, cache-blocked, SIMD,
  multithreaded, reaching hundreds of **GFLOPS**. It is **not** `A * B` (elementwise).
- **Measured:** a 128x128 BLAS multiply is **4,848x** faster than a naive Python triple loop (77 us vs 374 ms);
  BLAS sustains **184 GFLOPS** on 512x512. The gap grows with size (O(n^3)).
- **Never hand-write matrix multiply or dense linear algebra;** use `@`/`np.dot`/`numpy.linalg` (LAPACK), and
  shape computations as matrix operations so they reach BLAS.
- **Edges:** keep matrices in float dtypes and contiguous for the fast path; batch small multiplies; prefer
  `solve` over `inv`; watch BLAS thread oversubscription inside your own parallelism.

**Cross-references.** Vectorization → Chapter 96; dtype fast path → Chapter 98; contiguity/views → Chapter 99.
Threads/processes → Chapters 8, 48. `numpy.linalg`/LAPACK, `einsum`, GPU/cuBLAS, sparse → the rest of Deep T. The
model-math seam → Deep U (Book III).
