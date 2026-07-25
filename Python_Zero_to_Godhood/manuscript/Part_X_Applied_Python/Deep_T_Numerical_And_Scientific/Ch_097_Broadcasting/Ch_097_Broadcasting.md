# Chapter 97: Broadcasting

To add a per-column offset to every row of a large matrix, the literal approach is to *replicate* the offset
row into a full matrix and add: `mat + np.tile(row, (M, 1))`. It works, and it *doubles the memory*: `np.tile`
materializes an `(M, N)` copy of the row, an intermediate array *as large as the result itself*. **Broadcasting**
does the same computation without that copy. `mat + row` applies the `(N,)` row across all `M` rows *directly in
C*, never building the replicated array, so it allocates only the result. Measured, broadcasting peaks at **30.6
MB** where tiling peaks at **61.0 MB**, **2x** the memory, and the tiling also spends time building the copy.
Broadcasting is not just convenient syntax; it is the *memory-efficient* way to combine arrays of different
shapes.

This chapter continues **Deep T** with broadcasting: the shape-compatibility rules, why the smaller operand is
never materialized, and when broadcasting saves memory that explicit replication wastes. It is what makes NumPy's
whole-array style (Chapter 96) work across *different* shapes, not just identical ones.

## Section index

- **97.1** The broadcasting rules
- **97.2** Why no copy is made
- **97.3** Measurement: broadcasting vs tiling
- **97.4** Edges and failure modes
- **97.5** Connections
- **97.6** Exercises
- **97.7** Summary and cross-references

Listings live under `code/ch097/` and are re-executed by `make verify` on both interpreters (both with NumPy
2.1.3).

---

## 97.1 The broadcasting rules

```python
# code/ch097/l01_broadcasting.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a scalar broadcasts across the whole array ---
  a * 10 : [10, 20, 30, 40]
--- a (N,) row broadcasts across each row of a (M, N) matrix ---
  matrix + row :
[[1 2 3 4]
 [1 2 3 4]
 [1 2 3 4]]
--- a (M, 1) column + a (N,) row -> (M, N) grid (both stretch) ---
  col.shape (3, 1) + row.shape (3,) -> (3, 3):
[[ 1  2  3]
 [11 12 13]
 [21 22 23]]
--- the rule for compatibility (align shapes from the right) ---
  (3, 4) and (4,)   compatible : True  (4==4)
  (3, 1) and (3,)   compatible : True  (1 stretches to 3)
  (3, 4) and (3,)   compatible : False  (4 != 3: ValueError)
--- no expanded copy is made (broadcasting streams the small operand) ---
  matrix + row gives the same result as tiling the row, but without
  allocating M copies of it (the benchmark shows the memory saved)
```

Broadcasting has *one* rule, applied dimension by dimension: **align the shapes from the right; two dimensions
are compatible if they are equal or one of them is 1** (a size-1 dimension *stretches* to match). So a scalar
(shape `()`) broadcasts across any array; a `(N,)` row is compatible with a `(M, N)` matrix (the trailing `N`
matches, and the row is applied to each of the `M` rows); and a `(M, 1)` column combined with a `(N,)` row
produces an `(M, N)` grid, *both* stretch their size-1 (or absent) dimensions. When the rule fails, `(3, 4)` and
`(3,)` (trailing `4 != 3`), NumPy raises `ValueError`, it does *not* silently guess.

The result of `matrix + row` is the row added to *every* row, exactly as if you had replicated the row into an
`(M, N)` array and added, but, as the last block notes and §97.3 measures, *without allocating that replicated
array*.

---

## 97.2 Why no copy is made

The key to broadcasting's efficiency is *strides*. A NumPy array's elements are laid out in a contiguous buffer,
and its *shape* is interpreted through *strides*, the number of bytes to step to reach the next element along
each dimension. Broadcasting a `(N,)` row across `(M, N)` does not copy the row `M` times; it treats the row *as
if* it had shape `(M, N)` by setting the stride along the new `M` dimension to *zero*. A zero stride means
"stepping along this dimension does not move in memory", so every one of the `M` rows *reads the same underlying
`N` values*. NumPy's C loop then walks the output `(M, N)` and, for each element, reads the matrix element and
the (stride-0-shared) row element, computing the result, all without ever materializing the expanded row.

So broadcasting is a *view-like* trick at the computation level: the small operand is *logically* stretched via a
zero stride, not *physically* copied. `np.tile`, by contrast, *physically* builds the `(M, N)` array (allocating
and filling it), which is why it costs the extra memory and time. Broadcasting gets the same result by having the
C loop reuse the small operand's memory.

The rule: **rely on broadcasting to combine arrays of compatible shapes; do not `np.tile`/`np.repeat` to make
shapes match unless you genuinely need the expanded array as data.** Adding a bias vector to a batch of
activations, subtracting a per-feature mean from a data matrix, scaling rows by a weight vector, computing an
outer product or a distance grid, all are broadcasting operations that should *never* materialize the expanded
operand. Explicit tiling is a code smell for a computation broadcasting would do for free; reach for it only when
the replicated array is itself the desired output. This is the array-level version of the whole book's laziness
theme (Chapters 9, 33): do not materialize what you can compute in place.

---

## 97.3 Measurement: broadcasting vs tiling

**Methodology.** `code/ch097/bench_broadcasting.py`. Adding a `(N,)` row to a `(2000, 2000)` `float64` matrix via
broadcasting (`mat + row`) versus explicit tiling (`mat + np.tile(row, (M, 1))`). Peak memory via `tracemalloc`
(deterministic). CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64, NumPy 2.1.3.

| `(2000, 2000) + (2000,)` | peak memory |
|---|---|
| broadcasting | **30.6 MB** (just the result) |
| `np.tile` | **61.0 MB** (result + tiled temporary) |
| ratio | **2.0x** |

The `(2000, 2000)` `float64` result is ~30.6 MB (4 million floats x 8 bytes). Broadcasting allocates *only that
result*. `np.tile` allocates the result *plus* a full `(2000, 2000)` copy of the row, another ~30.6 MB, for a
peak of **61.0 MB**, exactly **2x**. The tiled temporary is *as large as the entire result*, pure overhead for a
value (the row, 2000 numbers) that broadcasting reuses in place.

The rule: **broadcasting is the memory-efficient default for shape-mismatched operations; tiling wastes memory
equal to the result size.** The 2x here is the general shape of it, materializing an operand to `(M, N)` when it
only *has* `N` (or `M`) distinct values duplicates the result-sized array for nothing. For large matrices (a data
batch, an image, a feature matrix) that temporary can be gigabytes, the difference between fitting in memory and
an out-of-memory crash. So express the computation with broadcasting and let NumPy's zero-stride trick apply the
small operand for free; the only time to `tile`/`repeat` is when you actually want the expanded array as data. As
in Chapter 96, the idiomatic NumPy form (broadcast, not replicate) is also the efficient one.

---

## 97.4 Edges and failure modes

**`np.tile`/`np.repeat` to match shapes for an operation.** §97.2. Materializes a result-sized temporary (2x
memory). Rely on broadcasting; tile only when you need the expanded array as data.

**Incompatible shapes.** §97.1. Broadcasting raises `ValueError` when a trailing dimension mismatches (and
neither is 1). This is a *feature* (it catches a shape bug); reshape (`row[:, None]` to add an axis) to make the
intended broadcast explicit rather than forcing it.

**Unintended broadcasting.** Two arrays whose shapes *happen* to be compatible can broadcast when you meant an
error, e.g. a `(3,)` and a `(3, 1)` broadcasting to `(3, 3)` when you expected elementwise `(3,)`. Check shapes;
a silent broadcast producing a wrong-shaped result is a subtle bug.

**Broadcasting that explodes the result.** `col (M, 1) + row (1, N)` produces an `(M, N)` array, which for large
`M`, `N` is huge even though the *inputs* are small. Broadcasting saves the *operand* copy but the *result* is
full-size; an outer operation of two large vectors is O(M x N) memory regardless. Know the result shape.

**Adding an axis for alignment.** To broadcast a `(N,)` against the *columns* of an `(M, N)` (not the rows), you
must reshape to `(M, 1)` (`arr[:, None]`); a bare `(M,)` aligns to the trailing dimension. Use `None`/`np.newaxis`
to place the size-1 axis where you intend.

**In-place broadcasting limits.** `mat += row` broadcasts in place (no result allocation at all), but `row +=
mat` fails (the result shape does not fit the smaller operand). In-place ops require the *left* operand to be the
full-shaped one.

---

## 97.5 Connections

**Backward.** Broadcasting is the shape-general extension of Chapter 96's vectorization. The zero-stride view
trick is the strides/views mechanism (a Deep T and Chapter 37/44 memory theme). The "do not materialize" lesson
is Chapters 9 and 33 (laziness), at the array level.

**Forward.** Strides, memory layout (C vs Fortran order), and views vs copies in depth are the next Deep T
chapters. `np.einsum` and matrix products (which broadcast batch dimensions) are Deep T. Broadcasting underlies
tensor operations in ML frameworks (PyTorch/JAX follow the same rules).

**Across books.** Broadcasting is how Book II applies per-feature and per-batch operations to **Book III**'s data
matrices without blowing up memory. A **Book III** pipeline subtracts a per-feature mean, scales by a per-feature
std, and adds a per-example bias to a `(batch, features)` matrix, all broadcasts, so a large batch is normalized
in place without materializing feature- or batch-sized copies. The §97.3 tiling waste is exactly the out-of-
memory trap that naive shape-matching creates on large tensors, which **Deep T** and **Deep U** avoid by
broadcasting.

---

## 97.6 Exercises

**1. Apply the rules.** For several shape pairs (`(3,4)`+`(4,)`, `(3,1)`+`(3,)`, `(3,4)`+`(3,)`), predict whether
they broadcast and to what shape, then check. Explain the align-from-the-right, size-1-stretches rule.

**2. Measure the saving.** Run §97.3's benchmark and confirm tiling uses ~2x the memory of broadcasting. Explain
what the tiled temporary is and why broadcasting avoids it.

**3. Normalize a matrix.** Subtract a per-column mean and divide by a per-column std from a data matrix using
broadcasting (no loops, no tiling). Explain each broadcast.

**4. Add the right axis.** Broadcast a `(M,)` vector against the *columns* vs the *rows* of an `(M, N)` matrix
using `[:, None]`, and show the different results. Explain the axis alignment.

**5. The design question.** Broadcasting combines different shapes without materializing the smaller operand,
using zero strides. Argue why this is superior to explicit replication. Your answer must use the §97.3 memory
measurement, the strides mechanism, and the cases where you genuinely need `tile`.

---

## 97.7 Summary and cross-references

- **Broadcasting** combines arrays of different shapes by the rule: **align from the right; dimensions are
  compatible if equal or one is 1** (size-1 stretches). Incompatible trailing dimensions raise `ValueError`.
- The stretched operand is **never copied**: NumPy uses a **zero stride** so the small operand's memory is reused
  across the broadcast dimension, computing in C without materializing the expansion.
- **Measured:** `(2000,2000) + (2000,)` peaks at **30.6 MB** broadcasting vs **61.0 MB** with `np.tile` (**2x**),
  because tiling materializes a result-sized copy of the row.
- **Rely on broadcasting** for shape-mismatched operations (bias/mean/scale on batches and matrices); use
  `tile`/`repeat` only when you need the expanded array as data. Mind result-shape explosions and axis alignment
  (`[:, None]`).

**Cross-references.** Vectorization → Chapter 96. Strides/views and memory → the next Deep T chapters, Chapters
37, 44. Laziness/don't-materialize → Chapters 9, 33. `einsum`/matrix products → Deep T. The numeric-data seam →
Deep U.
