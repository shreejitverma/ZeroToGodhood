"""Benchmark 96.1 - vectorized NumPy vs a Python loop over a list.

Sum of squares over 1,000,000 integers, three ways: a NumPy vectorized expression
((arr*arr).sum(), all in C), a NumPy loop that indexes element by element (the
WRONG way to use NumPy), and a plain Python loop over a list. The vectorized form
runs one compiled C loop over contiguous memory; the element-by-element forms pay
Python-per-element overhead. The gap is the whole reason NumPy exists.

Does its own timing (asymmetric iteration counts), guarded by __main__. See
_harness/bench.py.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from _harness.bench import provenance  # noqa: E402

N = 1_000_000


def best(fn, reps):
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return min(times)


def main():
    print("=== 96.1  sum of squares over 1,000,000 ints: vectorized vs loops ===")
    print(provenance())
    print()

    arr = np.arange(N, dtype=np.int64)
    lst = list(range(N))

    def vectorized():
        return int((arr * arr).sum())

    def numpy_indexed():           # anti-pattern: Python loop over a NumPy array
        total = 0
        for i in range(N):
            total += int(arr[i]) * int(arr[i])
        return total

    def python_loop():
        total = 0
        for x in lst:
            total += x * x
        return total

    t_vec = best(vectorized, 20)
    t_np_loop = best(numpy_indexed, 2)
    t_py = best(python_loop, 3)

    print(f"  vectorized (arr*arr).sum() : {t_vec * 1000:8.2f} ms   1.0x")
    print(f"  python loop over a list    : {t_py * 1000:8.2f} ms   {t_py / t_vec:5.0f}x slower")
    print(f"  python loop over the array : {t_np_loop * 1000:8.2f} ms   {t_np_loop / t_vec:5.0f}x slower (anti-pattern)")

    print()
    print("Reading this. The vectorized expression runs one compiled C loop over a")
    print("contiguous block of int64s, with no Python object or bytecode per element.")
    print("The Python loop over a list pays interpreter overhead and boxing for every")
    print("element, tens of times slower. Worse is a Python loop that INDEXES a NumPy")
    print("array (arr[i]): it pays the Python-per-element cost AND unboxes a NumPy")
    print("scalar each step, the slowest of all and the classic NumPy mistake. The")
    print("rule: express computation as whole-array operations; never loop element by")
    print("element over a NumPy array in Python.")


if __name__ == "__main__":
    main()
