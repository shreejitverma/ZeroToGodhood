"""Listing 101.1 - reductions and the axis parameter (axis = the axis that vanishes).

sum, mean, max, min, std, ... collapse an array to fewer dimensions. With no axis,
they reduce the WHOLE array to a scalar. With axis=k, they reduce ALONG axis k,
that is, axis k DISAPPEARS from the result. This is the classic confusion:
axis=0 removes the ROW dimension, leaving per-COLUMN results; axis=1 removes the
COLUMN dimension, leaving per-ROW results. Getting the axis wrong is a silent bug
(right shape sometimes, wrong numbers). keepdims=True keeps the reduced axis as
size 1 so the result broadcasts back against the original. Reductions run in C,
hundreds of times faster than a Python loop (the benchmark). Deterministic here.
"""

import numpy as np


def main() -> None:
    m = np.array([[1, 2, 3],
                  [4, 5, 6]])
    print(f"  matrix (shape {m.shape}):\n{m}")

    print("--- no axis: reduce the whole array to a scalar ---")
    print(f"  m.sum()  : {m.sum()}   m.max() : {m.max()}   m.mean() : {m.mean()}")

    print("--- axis=0 removes the ROW dimension -> a result PER COLUMN ---")
    print(f"  m.sum(axis=0) : {m.sum(axis=0).tolist()}   (col sums; shape {m.sum(axis=0).shape})")

    print("--- axis=1 removes the COLUMN dimension -> a result PER ROW ---")
    print(f"  m.sum(axis=1) : {m.sum(axis=1).tolist()}   (row sums; shape {m.sum(axis=1).shape})")

    print("--- the mental model: axis=k is the axis that DISAPPEARS ---")
    print(f"  (2, 3) with axis=0 -> {m.sum(axis=0).shape}   (2 removed)")
    print(f"  (2, 3) with axis=1 -> {m.sum(axis=1).shape}   (3 removed)")

    print("--- keepdims=True keeps the reduced axis as size 1 (for broadcasting back) ---")
    row_mean = m.mean(axis=1, keepdims=True)
    print(f"  m.mean(axis=1, keepdims=True) shape : {row_mean.shape}")
    print(f"  m - row_mean (broadcasts, centers each row):\n{m - row_mean}")

    print("--- the rule ---")
    print(f"  axis=k reduces ALONG (removes) axis k; axis=0 -> per-column, axis=1 -> per-row")
    print(f"  use keepdims=True to broadcast the reduction back against the original")


if __name__ == "__main__":
    main()
