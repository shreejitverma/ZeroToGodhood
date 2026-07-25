# Chapter 101: Reductions and Axes

`arr.sum(axis=0)` and `arr.sum(axis=1)` are the two most-confused calls in NumPy, and mixing them up is a
*silent* bug: both return a valid array, just the wrong numbers. The confusion is that `axis` names the axis that
**disappears**, not the one you keep. For a `(2, 3)` matrix (2 rows, 3 columns), `sum(axis=0)` *removes the row
dimension*, collapsing down the rows to leave a **per-column** result of shape `(3,)`; `sum(axis=1)` *removes the
column dimension*, collapsing across the columns to leave a **per-row** result of shape `(2,)`. Get the mental
model right, "`axis=k` is the axis that vanishes", and the rest of NumPy's reductions (`mean`, `max`, `std`,
`argmax`, ...) fall into place. And these reductions run in C: summing a million-element matrix's columns is
**381x** faster than a Python nested loop.

This chapter continues **Deep T** with reductions and the axis parameter: what `axis` means, the `keepdims`
trick for broadcasting a reduction back, and the speed of C reductions. It is how you aggregate arrays, and the
source of the most common NumPy shape bug.

## Section index

- **101.1** `axis` is the axis that vanishes
- **101.2** `keepdims` and broadcasting back
- **101.3** Measurement: reduction vs loop
- **101.4** Edges and failure modes
- **101.5** Connections
- **101.6** Exercises
- **101.7** Summary and cross-references

Listings live under `code/ch101/` and are re-executed by `make verify` on both interpreters (both with NumPy
2.1.3).

---

## 101.1 `axis` is the axis that vanishes

```python
# code/ch101/l01_reductions.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
  matrix (shape (2, 3)):
[[1 2 3]
 [4 5 6]]
--- no axis: reduce the whole array to a scalar ---
  m.sum()  : 21   m.max() : 6   m.mean() : 3.5
--- axis=0 removes the ROW dimension -> a result PER COLUMN ---
  m.sum(axis=0) : [5, 7, 9]   (col sums; shape (3,))
--- axis=1 removes the COLUMN dimension -> a result PER ROW ---
  m.sum(axis=1) : [6, 15]   (row sums; shape (2,))
--- the mental model: axis=k is the axis that DISAPPEARS ---
  (2, 3) with axis=0 -> (3,)   (2 removed)
  (2, 3) with axis=1 -> (2,)   (3 removed)
--- keepdims=True keeps the reduced axis as size 1 (for broadcasting back) ---
  m.mean(axis=1, keepdims=True) shape : (2, 1)
  m - row_mean (broadcasts, centers each row):
[[-1.  0.  1.]
 [-1.  0.  1.]]
--- the rule ---
  axis=k reduces ALONG (removes) axis k; axis=0 -> per-column, axis=1 -> per-row
  use keepdims=True to broadcast the reduction back against the original
```

A reduction with **no axis** collapses the *whole* array to a scalar (`m.sum()` is 21). With an **axis**, it
collapses *along* that axis, and the reliable way to predict the result is by *shape*: reducing a `(2, 3)` array
`axis=0` produces shape `(3,)` (the `2` was removed), and `axis=1` produces `(2,)` (the `3` was removed). So
`sum(axis=0)` = `[5, 7, 9]` is the *column* sums (`1+4`, `2+5`, `3+6`), and `sum(axis=1)` = `[6, 15]` is the
*row* sums (`1+2+3`, `4+5+6`).

The trap: people read "`axis=0`" as "operate on rows" and expect row sums, but `axis=0` *removes* the row axis,
giving *column* sums. The correct reading is **"`axis=k` is the dimension that disappears from the shape"**. Once
you predict the *output shape* by deleting axis `k`, you cannot get it wrong. This generalizes to N dimensions:
`sum(axis=(0, 1))` removes *both* those axes, and negative axes count from the end (`axis=-1` is the last).

---

## 101.2 `keepdims` and broadcasting back

A reduction *removes* an axis, which changes the shape, and that often *breaks* a subsequent broadcast against
the original array. To center each row of `m` (subtract each row's mean from that row), you compute
`m.mean(axis=1)`, but that has shape `(2,)`, which does *not* broadcast against `m`'s `(2, 3)` the way you want
(NumPy would try to align `(2,)` with the trailing `3` and fail or misalign). **`keepdims=True`** fixes this: it
keeps the reduced axis as size **1**, so `m.mean(axis=1, keepdims=True)` has shape `(2, 1)`, which *broadcasts*
cleanly against `(2, 3)`, stretching the size-1 column across all 3 columns (Chapter 97). The result centers
each row (`m - row_mean` gives `[-1, 0, 1]` per row).

This is the standard pattern for *per-axis normalization*: reduce with `keepdims=True`, then broadcast the
reduction back. Subtract a per-column mean (`axis=0, keepdims=True`), divide by a per-row norm (`axis=1,
keepdims=True`), scale by a per-feature std, all follow the same shape-preserving-then-broadcast recipe. Without
`keepdims`, you would have to manually re-insert the axis (`row_mean[:, None]`, Chapter 97), which `keepdims`
does for you.

The rule: **predict a reduction's result by deleting axis `k` from the shape; use `keepdims=True` whenever you
will broadcast the reduction back against the original.** This makes per-axis aggregation-then-combine (the
bread and butter of data normalization and feature engineering) both correct and loop-free. As throughout Deep T,
reductions are whole-array operations that run in C (§101.3), so expressing an aggregation as an axis reduction,
not a Python loop, is both correct and fast.

---

## 101.3 Measurement: reduction vs loop

**Methodology.** `code/ch101/bench_reductions.py`. Column sums of a `1000 x 1000` `float64` matrix via
`m.sum(axis=0)` (a C reduction) versus a Python nested loop accumulating into a list. `min` per run. CPython
3.13.5, Apple M3 Pro, macOS 27.0, arm64, NumPy 2.1.3.

| column sums of 1000x1000 | time | vs vectorized |
|---|---|---|
| `m.sum(axis=0)` | **141 us** | 1.0x |
| Python nested loop | **53.5 ms** | **381x slower** |

The vectorized reduction is **381x** faster. `m.sum(axis=0)` is a single C pass over the contiguous matrix,
accumulating column sums with SIMD; the Python nested loop walks all one million elements in the interpreter,
boxing each `float` and adding it, the per-element overhead the book has measured, paid a million times.

The rule: **express aggregations as axis reductions, not loops.** Sum, mean, max, min, std, `argmax`, `cumsum`,
`prod`, over an axis, all run in C at reduction speed; a Python loop over array elements to aggregate is the
Chapter 96 anti-pattern in reduction form. Combined with §101.2's `keepdims` broadcasting, this covers the vast
majority of data-processing aggregation, per-column statistics, per-row norms, group summaries (via
`np.add.reduceat` or grouping), all as vectorized reductions. The 381x here compounds across a real pipeline, and
it is why numeric aggregation in Python is done with array reductions, never element loops. Get the `axis`
right (the axis that vanishes), reach for `keepdims` to broadcast back, and let NumPy run the reduction in C.

---

## 101.4 Edges and failure modes

**Confusing `axis=0` and `axis=1`.** §101.1. `axis=k` *removes* axis `k` (axis=0 -> per-column, axis=1 ->
per-row). A wrong axis gives a valid-but-wrong result, a silent bug. Predict the output shape (delete axis `k`)
to check.

**Broadcasting a reduction back without `keepdims`.** §101.2. The reduced shape may not align for the intended
broadcast. Use `keepdims=True` (or re-insert the axis with `[:, None]`) so it broadcasts cleanly.

**Overflow in integer reductions.** `int8`/`int16` array `sum` can overflow (Chapter 98); NumPy sums integers in
the array's dtype by default. Pass `dtype=` to accumulate in a wider type (`arr.sum(dtype=np.int64)`).

**`nan` poisoning a reduction.** `sum`/`mean`/`max` propagate `NaN` (any `NaN` makes the result `NaN`). Use the
`nan`-aware variants (`np.nansum`, `np.nanmean`) to skip `NaN`s, or mask them first.

**`argmax`/`argmin` return indices, not values.** They give the *position* of the extreme along the axis, not the
value; and they return a *flat* index for the whole array without an axis. Use the index to gather the value
(`arr[arr.argmax()]`), and pass `axis` for per-axis positions.

**Float summation order and precision.** A large float reduction accumulates rounding error (Chapter 35); NumPy
uses *pairwise* summation for better accuracy than a naive left fold, but for extreme precision needs use
`math.fsum` (Chapter 35) or `np.add.reduce` with a wider dtype. Know the reduction is not exact.

---

## 101.5 Connections

**Backward.** Reductions are the collapse half of vectorization (Chapter 96). The `keepdims` broadcast-back is
Chapter 97 (broadcasting) and the `[:, None]` axis trick. Integer overflow and float precision in reductions are
Chapters 98, 35. The C-loop speed vs Python is Chapter 96.

**Forward.** Grouped reductions (`np.add.reduceat`, `np.bincount`, and pandas `groupby`), `einsum` (reductions as
contractions), and cumulative operations (`cumsum`, `cumprod`) are Deep T. GPU reductions and their parallel-
tree algorithms are a Deep T topic.

**Across books.** Axis reductions are how Book II computes the statistics **Book III** runs on. A **Book III**
pipeline normalizes features (subtract per-feature mean with `axis=0, keepdims`, divide by per-feature std),
pools activations (mean/max over spatial axes), and computes per-example losses (reduce over the feature axis),
all as vectorized axis reductions. The §101.1 axis confusion is exactly the silent shape bug that produces
plausible-but-wrong statistics, which careful axis reasoning (predict the output shape) prevents, and **Deep T**
and **Deep U** rely on for correct aggregation at scale.

---

## 101.6 Exercises

**1. Predict by shape.** For a `(4, 5, 6)` array, predict the shape of `sum(axis=0)`, `sum(axis=1)`,
`sum(axis=2)`, and `sum(axis=(0, 2))`, then check. Explain the "delete axis k" rule.

**2. Column vs row.** Show `sum(axis=0)` gives column sums and `sum(axis=1)` row sums on a small matrix, and
construct a case where swapping them gives a wrong-but-valid result. Explain the confusion.

**3. Normalize with keepdims.** Center each column of a matrix (subtract per-column mean) using
`axis=0, keepdims=True`, and confirm the broadcast. Show it fails or misaligns without `keepdims`.

**4. Measure the reduction.** Run §101.3's benchmark and confirm the vectorized reduction is far faster than the
loop. Explain the C pass vs per-element Python.

**5. The design question.** NumPy's `axis` names the dimension that is *removed*. Argue why this is the right (if
initially confusing) convention, and how `keepdims` completes the aggregation-then-broadcast pattern. Your answer
must use the §101.3 measurement and the shape-prediction rule.

---

## 101.7 Summary and cross-references

- A **reduction** (`sum`, `mean`, `max`, `std`, ...) with no axis collapses to a scalar; with **`axis=k`** it
  removes axis `k` from the shape, `axis=0` -> **per-column**, `axis=1` -> **per-row**. Predict the result by
  *deleting axis `k`* from the shape.
- **`keepdims=True`** keeps the reduced axis as size 1 so the reduction **broadcasts back** against the original,
  the standard per-axis normalize-then-combine pattern.
- **Measured:** column sums of a 1000x1000 matrix are **381x** faster with `sum(axis=0)` than a Python nested
  loop (141 us vs 53.5 ms). Express aggregations as axis reductions, not loops.
- **Edges:** integer reductions can overflow (widen with `dtype=`); `NaN` poisons reductions (use `nan`-aware
  variants); `argmax`/`argmin` return indices; float reductions are not exact.

**Cross-references.** Vectorization → Chapter 96; broadcasting/`keepdims` → Chapter 97; dtype overflow → Chapter
98; float precision → Chapter 35. Grouped reductions, `einsum`, cumulatives → the rest of Deep T. The aggregation
seam → Deep U.
