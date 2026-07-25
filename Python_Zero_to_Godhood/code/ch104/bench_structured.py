"""Benchmark 104.1 - a structured array vs a list of dicts: memory for N records.

One million records of (x: float64, y: int64), held two ways: a NumPy structured
array (one contiguous 16-bytes-per-record block) versus a Python list of dicts
(each dict a hash table of boxed objects, plus per-object headers). The structured
array is far smaller. This measures the peak memory of building each.

Memory via tracemalloc. See _harness/bench.py.
"""

import sys
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from _harness.bench import provenance  # noqa: E402

N = 1_000_000


def main():
    print("=== 104.1  1,000,000 records (x: f8, y: i8): structured array vs list of dicts ===")
    print(provenance())
    print()

    mb = 1024 * 1024

    tracemalloc.start()
    sa = np.zeros(N, dtype=[("x", "f8"), ("y", "i8")])
    m_sa, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    tracemalloc.start()
    ld = [{"x": 0.0, "y": 0} for _ in range(N)]
    m_ld, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"  structured array   : {m_sa / mb:6.1f} MB   (16 bytes/record, one C block)")
    print(f"  list of dicts      : {m_ld / mb:6.1f} MB   (boxed objects + hash tables)")
    print(f"  list of dicts uses ~{m_ld / m_sa:.0f}x more memory")

    del sa, ld

    print()
    print("Reading this. A structured array packs N records into one contiguous")
    print("typed block: 16 bytes per record here, no per-element Python object. A")
    print("list of dicts stores, per record, a dict (a hash table) of boxed Python")
    print("floats and ints, each with an object header, many times larger. And a")
    print("structured array's columns are ndarray views you vectorize (col.mean()),")
    print("while the list needs a Python loop. Use a structured array (or a")
    print("DataFrame, built on this) for tabular numeric data; reach for a list of")
    print("dicts only for small, irregular, or heavily-mutated records.")


if __name__ == "__main__":
    main()
