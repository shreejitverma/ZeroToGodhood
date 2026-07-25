"""Benchmark 101.1 - a vectorized axis reduction vs a Python nested loop.

Column sums of a 1000x1000 matrix, two ways: arr.sum(axis=0) (one C reduction over
contiguous memory) and a Python nested loop accumulating into a list. The reduction
is a single C pass; the loop pays per-element interpreter overhead across a million
elements. This measures both.

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


def main():
    print("=== 101.1  column sums of a 1000x1000 matrix: vectorized vs loop ===")
    print(provenance())
    print()

    np.random.seed(0)
    m = np.random.rand(1000, 1000)

    def vectorized():
        return m.sum(axis=0)

    def python_loop():
        res = [0.0] * m.shape[1]
        for row in m:
            for j, v in enumerate(row):
                res[j] += v
        return res

    t_vec = best(vectorized, 30)
    t_py = best(python_loop, 1)

    print(f"  numpy sum(axis=0) : {t_vec * 1e6:8.0f} us   1.0x")
    print(f"  python nested loop: {t_py * 1e3:8.1f} ms   {t_py / t_vec:5.0f}x slower")

    print()
    print("Reading this. The vectorized reduction runs one C pass over the")
    print("contiguous matrix, accumulating column sums with SIMD; the Python loop")
    print("walks a million elements in the interpreter, boxing and adding each. So")
    print("the reduction is hundreds of times faster. Express aggregations as")
    print("axis reductions (sum/mean/max/std with axis=), not loops, and remember")
    print("axis=k removes axis k (axis=0 -> per-column, axis=1 -> per-row); use")
    print("keepdims=True when you need to broadcast the reduced result back.")


if __name__ == "__main__":
    main()
