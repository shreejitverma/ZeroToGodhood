"""Benchmark 100.1 - BLAS matrix multiply vs a naive Python triple loop.

A @ B dispatches to a BLAS library: cache-blocked, SIMD, multithreaded, decades-
optimized. A naive triple loop in Python computes the same thing element by element
in the interpreter. The gap is enormous, thousands of times, which is why no one
hand-writes matrix multiply. This measures both on a 128x128 multiply (small enough
that the naive loop finishes), and reports the BLAS throughput in GFLOPS on a larger
512x512.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from _harness.bench import provenance  # noqa: E402


def best(fn, reps):
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return min(times)


def naive_matmul(A, B):
    n = A.shape[0]
    C = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            s = 0.0
            for k in range(n):
                s += A[i, k] * B[k, j]
            C[i, j] = s
    return C


def main():
    print("=== 100.1  matrix multiply: BLAS @ vs naive Python triple loop ===")
    print(provenance())
    print()

    np.random.seed(0)
    n = 128
    A = np.random.rand(n, n)
    B = np.random.rand(n, n)

    print(f"  results match (BLAS vs naive) : {np.allclose(A @ B, naive_matmul(A, B))}")

    t_blas = best(lambda: A @ B, 50)
    t_naive = best(lambda: naive_matmul(A, B), 1)
    print(f"  BLAS  A @ B  ({n}x{n}) : {t_blas * 1e6:10.1f} us")
    print(f"  naive triple loop      : {t_naive * 1e3:10.1f} ms   ({t_naive / t_blas:,.0f}x slower)")

    big = 512
    Ab = np.random.rand(big, big)
    Bb = np.random.rand(big, big)
    t_big = best(lambda: Ab @ Bb, 20)
    gflops = 2 * big ** 3 / t_big / 1e9
    print(f"  BLAS {big}x{big} throughput  : {gflops:10.0f} GFLOPS")

    print()
    print("Reading this. The naive triple loop runs O(n^3) multiply-adds in the")
    print("Python interpreter, one boxed float operation at a time. A @ B dispatches")
    print("to a BLAS library that blocks the computation for cache, vectorizes it")
    print("with SIMD, and runs it across multiple threads, reaching hundreds of")
    print("GFLOPS, a large fraction of the CPU's peak. The result is thousands of")
    print("times faster. Never hand-write matrix multiply (or any dense linear")
    print("algebra); use @ / np.dot / np.linalg, which call BLAS/LAPACK. This is the")
    print("ultimate case of the book's rule: let compiled, vectorized code do the")
    print("numeric work, not the Python interpreter.")


if __name__ == "__main__":
    main()
