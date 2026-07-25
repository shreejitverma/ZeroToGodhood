"""Benchmark 141.1 - Parquet vs CSV: smaller and much faster to read.

A columnar binary format (Parquet) versus text (CSV) for a 500,000-row typed table.
Parquet stores each column contiguously, typed and compressed; CSV stores text rows.
So Parquet is smaller on disk and far faster to read (no text parsing, columns loaded
directly). This measures both. (Reads are warmed up first, so the Parquet engine's
one-time initialization is not charged to the timing.)

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from _harness.bench import provenance  # noqa: E402

N = 500_000


def best(fn, reps=5):
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return min(times)


def main():
    print(f"=== 141.1  {N:,}-row table: CSV vs Parquet (size and read speed) ===")
    print(provenance())
    print()

    rng = np.random.default_rng(0)
    df = pd.DataFrame({
        "id": np.arange(N),
        "price": rng.random(N) * 100,
        "qty": rng.integers(1, 1000, N),
    })

    d = tempfile.mkdtemp()
    csv_path = os.path.join(d, "data.csv")
    parquet_path = os.path.join(d, "data.parquet")

    df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)

    csv_mb = os.path.getsize(csv_path) / 1024 / 1024
    parquet_mb = os.path.getsize(parquet_path) / 1024 / 1024

    pd.read_parquet(parquet_path)          # warm up the Parquet engine
    pd.read_csv(csv_path)

    t_csv = best(lambda: pd.read_csv(csv_path))
    t_parquet = best(lambda: pd.read_parquet(parquet_path))

    print(f"  CSV size     : {csv_mb:5.1f} MB     read : {t_csv * 1e3:5.0f} ms")
    print(f"  Parquet size : {parquet_mb:5.1f} MB     read : {t_parquet * 1e3:5.0f} ms")
    print(f"  Parquet is {csv_mb / parquet_mb:.1f}x smaller and {t_csv / t_parquet:.0f}x faster to read")

    os.remove(csv_path)
    os.remove(parquet_path)

    print()
    print("Reading this. Parquet is smaller on disk (columnar layout plus")
    print("compression) and reads many times faster (no text parsing: typed columns")
    print("load directly into NumPy arrays, Deep T). It also preserves dtypes (CSV")
    print("stores everything as text and re-infers types on read, sometimes wrongly)")
    print("and lets you read only the columns you need (columnar). So for data")
    print("pipelines, storing intermediate and final data as Parquet is the default:")
    print("faster, smaller, typed, and self-describing. Reserve CSV for human")
    print("inspection and interop with tools that require text. The gap grows with")
    print("data size, which is why every serious data platform is columnar (Parquet,")
    print("Arrow, ORC), the same columnar-is-fast principle as NumPy and pandas.")


if __name__ == "__main__":
    main()
