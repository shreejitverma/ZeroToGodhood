"""Benchmark 139.1 - groupby aggregates in C, far faster than a Python accumulation loop.

groupby splits, aggregates, and combines in C over contiguous typed arrays. The manual
alternative, a Python loop accumulating into a dict, runs in the interpreter per row.
This computes a per-key sum over 500,000 rows both ways: pandas groupby versus a Python
dict-accumulation loop. groupby is much faster and much clearer.

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
    print(f"=== 139.1  per-key sum over {N:,} rows: groupby vs a Python dict loop ===")
    print(provenance())
    print()

    rng = np.random.default_rng(0)
    df = pd.DataFrame({"key": rng.integers(0, 100, N), "v": rng.random(N)})

    t0 = time.perf_counter()
    grouped = df.groupby("key")["v"].sum()               # split-apply-combine in C
    t_gb = time.perf_counter() - t0

    t0 = time.perf_counter()
    acc = {}
    for k, v in zip(df["key"].tolist(), df["v"].tolist()):   # accumulate in Python
        acc[k] = acc.get(k, 0.0) + v
    t_loop = time.perf_counter() - t0

    print(f"  groupby(key).sum() : {t_gb * 1e3:6.0f} ms   1x")
    print(f"  Python dict loop   : {t_loop * 1e3:6.0f} ms   {t_loop / t_gb:.0f}x slower")

    print()
    print("Reading this. groupby is several times faster than the hand-written dict")
    print("loop, and the loop is already the FAST way to do it in pure Python (a")
    print("simple dict.get accumulation, not iterrows). groupby wins because it")
    print("groups and sums in C over contiguous typed arrays, while the loop runs the")
    print("interpreter per row and boxes each value. And groupby is far clearer, one")
    print("expression versus a loop, and composes: multiple keys, multiple")
    print("aggregations, and further column operations all stay vectorized. This is")
    print("the split-apply-combine pattern, the workhorse of data aggregation: express")
    print("'per-group summary' as a groupby, never as a manual accumulation loop. The")
    print("gap widens with more groups and more complex aggregations.")


if __name__ == "__main__":
    main()
