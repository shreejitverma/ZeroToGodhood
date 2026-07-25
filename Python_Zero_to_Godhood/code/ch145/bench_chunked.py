"""Benchmark 145.1 - chunked processing scales memory with the chunk, not the dataset.

Loading a whole file peaks at the file's in-memory size; processing it in chunks peaks
at one chunk's size. This aggregates a 1,000,000-row CSV two ways, whole-file versus in
100,000-row chunks, and compares peak memory. The chunked version uses far less, and
produces the same result, which is how data larger than RAM is processed on one machine.

Memory via tracemalloc. See _harness/bench.py.
"""

import os
import sys
import tempfile
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from _harness.bench import provenance  # noqa: E402

N = 1_000_000
CHUNK = 100_000


def main():
    print(f"=== 145.1  aggregate {N:,} rows: whole-file vs {CHUNK:,}-row chunks ===")
    print(provenance())
    print()

    rng = np.random.default_rng(0)
    d = tempfile.mkdtemp()
    path = os.path.join(d, "data.csv")
    pd.DataFrame({"key": rng.integers(0, 10, N), "v": rng.random(N)}).to_csv(path, index=False)

    mb = 1024 * 1024

    tracemalloc.start()
    whole = pd.read_csv(path)
    whole_result = whole.groupby("key")["v"].sum()
    peak_whole = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    del whole

    tracemalloc.start()
    partial = None
    for chunk in pd.read_csv(path, chunksize=CHUNK):
        s = chunk.groupby("key")["v"].sum()
        partial = s if partial is None else partial.add(s, fill_value=0)
    peak_chunk = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()

    match = bool(np.allclose(whole_result.sort_index().values, partial.sort_index().values))

    print(f"  whole-file peak memory : {peak_whole / mb:5.0f} MB")
    print(f"  chunked peak memory    : {peak_chunk / mb:5.0f} MB   ({peak_whole / peak_chunk:.0f}x less)")
    print(f"  same result            : {match}")

    os.remove(path)

    print()
    print("Reading this. Loading the whole file peaks at its full in-memory size;")
    print("chunked processing peaks at one chunk, about 10x less here, and produces")
    print("the identical aggregate. This is how you process data LARGER THAN RAM on a")
    print("single machine: stream it in chunks, aggregate each, and combine the")
    print("partial results (a sum is associative; groupby sums add; count adds; mean")
    print("needs sum and count). The chunk size trades memory against per-chunk")
    print("overhead. This is also the ESSENCE of distributed processing, Dask and")
    print("Spark do exactly this split-aggregate-combine, but across many MACHINES")
    print("instead of chunks on one, and even Parquet's row groups (Chapter 60)")
    print("enable reading and processing a file piece by piece. When data outgrows")
    print("RAM: chunk on one machine, then distribute across many, same pattern.")


if __name__ == "__main__":
    main()
