"""Benchmark 37.1 - slicing bytes copies O(n); slicing a memoryview is zero-copy.

A bytes/bytearray slice allocates and copies the sliced region: O(n) time and
O(n) memory. A memoryview slice creates a new view object that references the
same underlying buffer with adjusted offsets: O(1), no copy. For large buffers
processed in windows (parsers, protocol framing, file readers), this is the
difference between copying the data repeatedly and never copying it at all.

Memory via tracemalloc (deterministic). See _harness/bench.py.
"""

import sys
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 16_000_000
LO, HI = 1_000_000, 15_000_000


def peak_bytes(fn):
    tracemalloc.start()
    result = fn()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak, result


def main():
    print("=== 37.1  bytes slice (copy) vs memoryview slice (zero-copy) ===")
    print(provenance())
    print()

    src = bytes(N)

    def bytes_slice():
        return src[LO:HI]                       # copies HI-LO bytes

    def view_slice():
        return memoryview(src)[LO:HI]           # no copy, just a window

    copy_mem, copy_res = peak_bytes(bytes_slice)
    view_mem, view_res = peak_bytes(view_slice)

    print(f"  slice length             : {HI - LO:>12,} bytes")
    print(f"  bytes slice peak memory  : {copy_mem:>12,} bytes")
    print(f"  memoryview slice peak    : {view_mem:>12,} bytes")
    print(f"  ratio                    : {copy_mem / max(view_mem, 1):>12,.0f}x")
    print(f"  same bytes?              : {bytes(view_res) == copy_res}")

    print()
    print("Reading this. The bytes slice allocates and copies ~14 MB; the")
    print("memoryview slice allocates a small view object and copies nothing,")
    print("it references the same buffer with adjusted bounds. For a large")
    print("buffer processed in overlapping windows, memoryview turns O(n) copies")
    print("into O(1) views. Reach for it when you parse or frame large binary")
    print("data; reach for bytes when you need an independent, immutable copy.")


if __name__ == "__main__":
    main()
