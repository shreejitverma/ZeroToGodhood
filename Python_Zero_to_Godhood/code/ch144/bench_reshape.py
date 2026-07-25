"""Benchmark 144.1 - long vs wide format memory for dense data.

Long (tidy) format repeats the key columns (date, metric) for EVERY value, while wide
format stores each key once (as an index and column headers). So for DENSE data (every
key combination present), wide is more compact. This measures a 10,000 x 20 dense grid
in both shapes. (For SPARSE or heterogeneous data the trade-off reverses; long avoids
storing absent combinations.)

Memory via memory_usage. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from _harness.bench import provenance  # noqa: E402

D, M = 10_000, 20


def main():
    print(f"=== 144.1  a {D:,} x {M} dense grid: long vs wide memory ===")
    print(provenance())
    print()

    rng = np.random.default_rng(0)
    long = pd.DataFrame({
        "date": np.repeat(np.arange(D), M),          # key repeated M times
        "metric": np.tile(np.arange(M), D),          # key repeated D times
        "value": rng.random(D * M),
    })
    wide = long.pivot(index="date", columns="metric", values="value")

    mb = 1024 * 1024
    long_mb = long.memory_usage(deep=True).sum() / mb
    wide_mb = wide.memory_usage(deep=True).sum() / mb

    print(f"  long format : {long_mb:5.1f} MB   ({len(long):,} rows, keys repeated)")
    print(f"  wide format : {wide_mb:5.1f} MB   ({wide.shape[0]:,} x {wide.shape[1]}, keys once)")
    print(f"  long uses {long_mb / wide_mb:.1f}x more (for this dense grid)")

    print()
    print("Reading this. Long format stores the key columns (date, metric) once PER")
    print("VALUE, so a dense grid repeats them M and D times respectively; wide format")
    print("stores each key once (row index and column headers) and just the value")
    print("matrix. So for dense data, wide is more compact. But the choice is not")
    print("mainly about memory: LONG (tidy) format, one row per observation with a")
    print("variable column, is the canonical shape for ANALYSIS, it groups, filters,")
    print("and plots uniformly regardless of how many variables there are, and it")
    print("handles sparse/heterogeneous data without storing absent combinations. Wide")
    print("format is for display (a human-readable table) and dense numeric matrices")
    print("(feeding a model). Keep data tidy/long for pipelines; reshape to wide at")
    print("the edges (display, matrix input). pivot/melt convert freely between them.")


if __name__ == "__main__":
    main()
