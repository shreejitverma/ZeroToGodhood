"""Benchmark 99.1 - a slice (view) is O(1) memory; fancy indexing copies O(n).

Taking roughly half of a 10,000,000-element array two ways: a basic slice (a view,
sharing the parent's memory, allocating only a small array object) versus a boolean
mask (fancy indexing, which copies the selected elements into a new array). The view
is a few bytes; the copy is the size of the selection. This measures the peak memory
of each with tracemalloc (deterministic).

Memory via tracemalloc. See _harness/bench.py.
"""

import sys
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from _harness.bench import provenance  # noqa: E402

N = 10_000_000


def peak(fn):
    tracemalloc.start()
    result = fn()
    _, pk = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return pk, result


def main():
    print("=== 99.1  selecting ~half of 10,000,000 ints: view vs copy ===")
    print(provenance())
    print()

    arr = np.arange(N, dtype=np.int64)
    mb = 1024 * 1024

    view_mem, view = peak(lambda: arr[: N // 2])            # a slice: a view
    copy_mem, copy = peak(lambda: arr[arr < N // 2])         # boolean mask: a copy

    print(f"  same values selected     : {np.array_equal(view, copy)}")
    print(f"  slice (view) peak memory : {view_mem:>12,} bytes")
    print(f"  boolean-index (copy) peak: {copy_mem / mb:>8.1f} MB")
    print(f"  the view shares memory; the copy allocates the whole selection")

    print()
    print("Reading this. The slice is a VIEW: it records an offset and strides into")
    print("the parent's buffer, so it allocates only a small array object, a few")
    print("dozen bytes, regardless of how many elements it spans. The boolean index")
    print("is a COPY: it cannot be expressed as strides, so it allocates a new array")
    print("holding the selected elements (here ~40 MB). So slice freely for O(1)")
    print("windows; know that fancy/boolean indexing copies, and that mutating a")
    print("view writes through to the parent. Use .copy() when you need an")
    print("independent array, and a mask/index list when you want a copy anyway.")


if __name__ == "__main__":
    main()
