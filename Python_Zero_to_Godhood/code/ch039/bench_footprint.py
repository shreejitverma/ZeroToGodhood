"""Benchmark 39.1 - array holds raw values; a list holds pointers to int objects.

A list of a million ints is a million-slot pointer array (8 bytes each) PLUS a
million separate int objects (~32 bytes each at these magnitudes). An
array.array('q') is a single block of a million 8-byte fields, no per-element
object. This measures the held memory of each, so the structural difference is
visible as bytes per element.

Memory via tracemalloc (deterministic). See _harness/bench.py.
"""

import array
import sys
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 1_000_000


def held_bytes(build):
    tracemalloc.start()
    obj = build()
    current, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del obj
    return current


def main():
    print("=== 39.1  array('q') vs list of a million 64-bit ints ===")
    print(provenance())
    print()

    list_mem = held_bytes(lambda: list(range(N)))
    arr_mem = held_bytes(lambda: array.array("q", range(N)))

    print(f"  elements                 : {N:>12,}")
    print(f"  list  held memory        : {list_mem:>12,} bytes ({list_mem / N:.1f}/elem)")
    print(f"  array held memory        : {arr_mem:>12,} bytes ({arr_mem / N:.1f}/elem)")
    print(f"  ratio                    : {list_mem / arr_mem:>12,.1f}x")

    print()
    print("Reading this. The list spends 8 bytes per slot on a pointer AND ~32")
    print("bytes per distinct int object, so it holds ~40 bytes per element. The")
    print("array stores raw 8-byte values inline, no per-element object, so it")
    print("holds ~8 bytes per element. For a large homogeneous numeric sequence,")
    print("array is several times smaller and exports its memory zero-copy via the")
    print("buffer protocol. Reach for a list when you need mixed types or per-")
    print("element objects; reach for array (or NumPy, Deep T) for bulk numbers.")


if __name__ == "__main__":
    main()
