"""Benchmark 142.1 - resample (time groupby in C) vs a manual per-timestamp loop.

resample buckets rows by time interval and aggregates each bucket, vectorized in C over
the datetime index. The manual alternative, looping over every timestamp, flooring it to
the bucket, and accumulating, runs the interpreter (and a Python-level floor operation)
per row. This computes hourly sums from 500,000 per-second values both ways. resample is
orders of magnitude faster.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from _harness.bench import provenance  # noqa: E402

N = 500_000


def main():
    print(f"=== 142.1  hourly sums from {N:,} per-second values: resample vs a loop ===")
    print(provenance())
    print()

    rng = np.random.default_rng(0)
    ts = pd.date_range("2026-01-01", periods=N, freq="s")
    s = pd.Series(rng.random(N), index=ts)

    t0 = time.perf_counter()
    resampled = s.resample("h").sum()                    # time groupby in C
    t_resample = time.perf_counter() - t0

    t0 = time.perf_counter()
    acc = {}
    for t, v in zip(s.index, s.values):                  # per-timestamp Python loop
        key = t.floor("h")
        acc[key] = acc.get(key, 0.0) + v
    t_loop = time.perf_counter() - t0

    print(f"  resample('h').sum() : {t_resample * 1e3:7.0f} ms   1x")
    print(f"  per-timestamp loop  : {t_loop * 1e3:7.0f} ms   {t_loop / t_resample:.0f}x slower")
    print(f"  bucket count        : {len(resampled)}")

    print()
    print("Reading this. resample is hundreds of times faster than the manual loop,")
    print("because it buckets the datetime index and aggregates in C, while the loop")
    print("runs the interpreter per row and pays a Python-level floor() on every")
    print("timestamp. resample is a time-based groupby (Chapter 58): the same split-")
    print("apply-combine, with time intervals as the grouping key. So the rule is the")
    print("same as everywhere in Deep U, never loop over rows (or timestamps); express")
    print("time bucketing as resample, component extraction as the vectorized .dt")
    print("accessor, and time arithmetic as vectorized operations on the whole column.")
    print("A per-timestamp Python loop over a time series is the same anti-pattern as")
    print("iterrows (Chapter 57), and just as many-hundred-x slow.")


if __name__ == "__main__":
    main()
