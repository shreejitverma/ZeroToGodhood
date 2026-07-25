"""Benchmark 98.1 - float32 is faster than float64 (half the bytes to move).

The same vectorized computation over float32 vs float64 arrays. float32 elements
are half the size, so a float32 array is half the memory and the CPU moves half the
bytes, fits more elements in cache, and processes more per SIMD instruction, so
the operation is faster (typically up to ~2x for memory-bound work). This measures
a sum of squares over both, and reports the memory each uses.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from _harness.bench import provenance  # noqa: E402

N = 5_000_000


def best(x, reps=30):
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        float((x * x).sum())
        times.append(time.perf_counter() - t0)
    return min(times)


def main():
    print("=== 98.1  (x*x).sum() over 5,000,000 elements: float32 vs float64 ===")
    print(provenance())
    print()

    a64 = np.arange(N, dtype=np.float64)
    a32 = np.arange(N, dtype=np.float32)
    mb = 1024 * 1024

    t64 = best(a64)
    t32 = best(a32)

    print(f"  float64 : {t64 * 1000:6.2f} ms   memory {a64.nbytes / mb:5.1f} MB   1.0x")
    print(f"  float32 : {t32 * 1000:6.2f} ms   memory {a32.nbytes / mb:5.1f} MB   {t64 / t32:.1f}x faster, half the memory")

    print()
    print("Reading this. float32 is faster because the array is half the size: the")
    print("CPU moves half the bytes, fits twice as many elements in cache, and")
    print("processes more per SIMD instruction. For memory-bound array work the")
    print("speedup approaches 2x, and the memory saving is exactly 2x. The cost is")
    print("precision (~7 vs ~15 significant digits). Use float32 for large")
    print("approximate data (ML tensors, images, embeddings), where half the memory")
    print("and near-double the speed matter and the precision is enough; use float64")
    print("when accumulation error or ill-conditioning demands the extra digits.")


if __name__ == "__main__":
    main()
