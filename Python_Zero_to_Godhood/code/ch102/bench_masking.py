"""Benchmark 102.1 - np.where (vectorized conditional) vs a Python if/else loop.

Applying a ReLU (keep positives, else 0) to 1,000,000 values, two ways: np.where(x
> 0, x, 0) (one C pass, computing the condition and selecting in compiled code) and
a Python list comprehension with an if/else (per-element interpreter branch and
boxing). The vectorized form is far faster. This measures both.

Does its own timing, guarded by __main__. See _harness/bench.py.
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
    print("=== 102.1  ReLU over 1,000,000 values: np.where vs a Python loop ===")
    print(provenance())
    print()

    np.random.seed(0)
    arr = np.random.randn(N)
    lst = arr.tolist()

    def vectorized():
        return np.where(arr > 0, arr, 0.0)

    def python_loop():
        return [x if x > 0 else 0.0 for x in lst]

    t_vec = best(vectorized, 30)
    t_py = best(python_loop, 3)

    print(f"  np.where(arr > 0, arr, 0) : {t_vec * 1e6:8.0f} us   1.0x")
    print(f"  python if/else loop       : {t_py * 1e3:8.1f} ms   {t_py / t_vec:5.0f}x slower")

    print()
    print("Reading this. np.where evaluates the condition and selects between the")
    print("two branches for the whole array in one C pass; the Python comprehension")
    print("branches per element in the interpreter, boxing each result, tens to")
    print("hundreds of times slower. Express conditional array logic with boolean")
    print("masks and np.where, never a Python loop with if/else. Combine conditions")
    print("with & | ~ (not and/or/not, and parenthesize each comparison). Use")
    print("arr[mask] to select (a copy) and arr[mask] = value to update in place.")


if __name__ == "__main__":
    main()
