"""Benchmark 103.1 - opening a memmap is O(1) memory; a full load is O(n).

A 200 MB array file, opened two ways: np.memmap (maps it, loads nothing until
accessed) versus np.fromfile (reads the whole file into RAM). The memmap's open
cost is a few hundred bytes regardless of file size; the full load is the file's
size. This is what lets memmap handle arrays larger than RAM. This measures the
peak memory of each open with tracemalloc.

Memory via tracemalloc. See _harness/bench.py.
"""

import os
import sys
import tempfile
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from _harness.bench import provenance  # noqa: E402

N = 25_000_000        # 25M float64 = 200 MB


def main():
    print("=== 103.1  opening a 200 MB array file: memmap vs full load ===")
    print(provenance())
    print()

    d = tempfile.mkdtemp()
    path = os.path.join(d, "big.dat")
    a = np.memmap(path, dtype=np.float64, mode="w+", shape=(N,))
    a[:] = np.arange(N)
    a.flush()
    del a

    mb = 1024 * 1024

    tracemalloc.start()
    mm = np.memmap(path, dtype=np.float64, mode="r", shape=(N,))
    _ = mm[0]                       # touch one element
    mem_open, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    tracemalloc.start()
    full = np.fromfile(path, dtype=np.float64)
    mem_full, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"  file size                : {N * 8 / mb:.0f} MB")
    print(f"  np.memmap open peak      : {mem_open:>12,} bytes  (maps, loads nothing)")
    print(f"  np.fromfile (load) peak  : {mem_full / mb:>8.0f} MB  (whole file in RAM)")
    print(f"  memmap uses ~{mem_full // max(mem_open, 1):,}x less to open")

    del mm, full
    os.remove(path)

    print()
    print("Reading this. np.memmap maps the file and loads nothing until you touch")
    print("it, so opening a 200 MB (or 200 GB) array file costs a few hundred bytes;")
    print("the OS pages in only the regions you access. np.fromfile/np.load reads the")
    print("entire file into RAM. So memmap lets you work with arrays LARGER THAN RAM,")
    print("slicing and computing on portions with only the touched pages resident.")
    print("Use memmap for huge on-disk arrays you access partially; use a full load")
    print("when the array fits in memory and you touch most of it (then repeated")
    print("access is faster from RAM than paging).")


if __name__ == "__main__":
    main()
