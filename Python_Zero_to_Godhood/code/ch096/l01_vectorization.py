"""Listing 96.1 - NumPy vectorization: array math in C, not a Python loop.

A NumPy ndarray is a block of contiguous, fixed-width numbers (like array.array,
Chapter 39) with math defined ON THE WHOLE ARRAY. arr * arr, arr.sum(), arr @ arr
run in compiled C over that block, one machine loop, no per-element Python object,
no bytecode per element. The equivalent Python for-loop pays interpreter overhead
and boxing for every element, so it is tens of times slower (the benchmark). This
listing shows the ndarray and its vectorized operations, producing the SAME result
as a loop but computed in C. Values are fixed so the output is deterministic.
"""

import numpy as np


def main() -> None:
    a = np.arange(1, 7, dtype=np.int64)     # [1 2 3 4 5 6]

    print("--- an ndarray: contiguous, fixed dtype, a shape ---")
    print(f"  array   : {a.tolist()}")
    print(f"  dtype   : {a.dtype}")
    print(f"  shape   : {a.shape}, contiguous: {a.flags['C_CONTIGUOUS']}")

    print("--- vectorized elementwise math (whole array at once, in C) ---")
    print(f"  a * 2       : {(a * 2).tolist()}")
    print(f"  a * a       : {(a * a).tolist()}")
    print(f"  a > 3       : {(a > 3).tolist()}")

    print("--- reductions run in C too ---")
    print(f"  a.sum()     : {int(a.sum())}")
    print(f"  a.mean()    : {float(a.mean())}")
    print(f"  (a * a).sum(): {int((a * a).sum())}   (sum of squares)")

    print("--- broadcasting: a scalar (or smaller array) applies across the array ---")
    m = np.arange(6).reshape(2, 3)
    print(f"  matrix      :\n{m}")
    print(f"  m + 10      :\n{m + 10}")
    print(f"  column sums : {m.sum(axis=0).tolist()}")

    print("--- same result as a Python loop, computed in C (benchmark: tens of x faster) ---")
    big = np.arange(1000, dtype=np.int64)
    loop_total = 0
    for x in big.tolist():
        loop_total += x * x
    print(f"  vectorized (big*big).sum() == python loop : {int((big * big).sum()) == loop_total}")


if __name__ == "__main__":
    main()
