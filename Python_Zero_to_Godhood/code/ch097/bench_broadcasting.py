"""Benchmark 97.1 - broadcasting avoids the temporary that explicit tiling allocates.

Adding a (N,) row to every row of a (M, N) matrix, two ways. Broadcasting (mat +
row) applies the row across all M rows without ever building the expanded row, so
it allocates only the (M, N) result. Explicit tiling (np.tile(row, (M, 1))) first
MATERIALIZES the row into a full (M, N) array (an O(M*N) temporary), then adds. So
tiling uses about twice the memory. This measures the peak memory of each with
tracemalloc (deterministic).

Memory via tracemalloc. See _harness/bench.py.
"""

import sys
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from _harness.bench import provenance  # noqa: E402

M = N = 2000


def peak(fn):
    tracemalloc.start()
    fn()
    _, pk = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return pk


def main():
    print("=== 97.1  (M, N) + (N,) row: broadcasting vs np.tile ===")
    print(provenance())
    print()

    mat = np.ones((M, N), dtype=np.float64)
    row = np.arange(N, dtype=np.float64)

    def broadcast():
        return mat + row                      # no expanded copy

    def tile():
        return mat + np.tile(row, (M, 1))     # materializes an (M, N) temporary

    mb = 1024 * 1024
    bcast = peak(broadcast)
    tiled = peak(tile)

    print(f"  array size (M x N x 8) : {M * N * 8 / mb:.0f} MB")
    print(f"  broadcasting peak      : {bcast / mb:5.1f} MB  (just the result)")
    print(f"  np.tile peak           : {tiled / mb:5.1f} MB  (result + tiled temporary)")
    print(f"  tile uses {tiled / bcast:.1f}x the memory")

    print()
    print("Reading this. Broadcasting applies the row across every row of the matrix")
    print("in C without ever building the M copies of it, so it allocates only the")
    print("result array. np.tile explicitly materializes the row into a full (M, N)")
    print("array first, an O(M*N) temporary equal in size to the result, so it uses")
    print("about twice the memory (and the time to build the copy). Rely on")
    print("broadcasting for operations across compatible shapes; reach for tile only")
    print("when you genuinely need the expanded array as data. Broadcasting is the")
    print("memory-efficient default.")


if __name__ == "__main__":
    main()
