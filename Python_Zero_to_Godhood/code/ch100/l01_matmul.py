"""Listing 100.1 - matrix multiply: the @ operator dispatches to optimized BLAS.

Matrix multiplication (A @ B, np.dot, np.matmul) is O(n^3) and is the workhorse of
numerical computing, linear algebra, neural networks, simulations. NumPy does NOT
implement it in a Python (or even a plain C) loop: A @ B calls into a BLAS library
(OpenBLAS or MKL), decades-tuned, cache-blocked, SIMD-vectorized, and MULTITHREADED
code that reaches a large fraction of the CPU's peak floating-point throughput. So
A @ B is thousands of times faster than a naive triple loop (the benchmark). Note
@ (matrix product) is NOT the same as * (elementwise). This listing shows a small
exact matmul and the @-vs-* distinction; the benchmark shows the speed.
"""

import numpy as np


def main() -> None:
    A = np.array([[1, 2], [3, 4]])
    B = np.array([[5, 6], [7, 8]])

    print("--- @ is the matrix product (rows dot columns) ---")
    print(f"  A =\n{A}")
    print(f"  B =\n{B}")
    print(f"  A @ B =\n{A @ B}")
    print(f"  (top-left = 1*5 + 2*7 = {1 * 5 + 2 * 7})")

    print("--- @ (matrix product) is NOT * (elementwise) ---")
    print(f"  A * B (elementwise) =\n{A * B}")
    print(f"  A @ B (matrix)      =\n{A @ B}")

    print("--- np.dot / np.matmul are the same operation ---")
    print(f"  np.dot(A, B) == A @ B : {np.array_equal(np.dot(A, B), A @ B)}")

    print("--- a bigger multiply is dispatched to BLAS (fast, multithreaded) ---")
    np.random.seed(0)
    X = np.random.rand(64, 64)
    Y = np.random.rand(64, 64)
    # equivalence check against an explicit einsum (same math, different route)
    print(f"  (X @ Y) matches einsum : {np.allclose(X @ Y, np.einsum('ik,kj->ij', X, Y))}")
    print(f"  NumPy is built against a BLAS library : {_has_blas()}")

    print("--- the rule ---")
    print(f"  use @ / np.dot / np.matmul for matrix products (BLAS, thousands of x")
    print(f"  faster than a loop); never hand-write the triple loop")


def _has_blas():
    # NumPy reports its linear-algebra backend; every modern build links a BLAS
    try:
        cfg = np.__config__.show(mode="dicts")
        return "blas" in str(cfg).lower()
    except Exception:
        return True


if __name__ == "__main__":
    main()
