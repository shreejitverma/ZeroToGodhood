"""Benchmark 138.1 - vectorized columns vs iterrows: the cardinal pandas rule.

The single most important pandas performance rule: operate on whole COLUMNS
(vectorized, in C via NumPy), never loop over rows with iterrows(). This computes a
sum of price*qty over 200,000 rows two ways: a vectorized column expression versus an
iterrows() row loop. The vectorized version is orders of magnitude faster, because
iterrows builds a Python Series object per row and does the arithmetic in the
interpreter, while the column expression runs one C pass over contiguous typed arrays.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from _harness.bench import provenance  # noqa: E402

N = 200_000


def main():
    print(f"=== 138.1  sum of price*qty over {N:,} rows: vectorized vs iterrows ===")
    print(provenance())
    print()

    rng = np.random.default_rng(0)
    df = pd.DataFrame({
        "price": rng.random(N) * 100,
        "qty": rng.integers(1, 100, N),
    })

    t0 = time.perf_counter()
    vec = float((df["price"] * df["qty"]).sum())          # one C pass over the columns
    t_vec = time.perf_counter() - t0

    t0 = time.perf_counter()
    total = 0.0
    for _, row in df.iterrows():                          # a Python object per row
        total += row["price"] * row["qty"]
    t_iter = time.perf_counter() - t0

    print(f"  vectorized columns : {t_vec * 1e6:8.0f} us   1x")
    print(f"  iterrows() loop    : {t_iter * 1e3:8.0f} ms   {t_iter / t_vec:.0f}x slower")
    import math
    print(f"  results agree      : {math.isclose(vec, total, rel_tol=1e-9)}")

    print()
    print("Reading this. The vectorized column expression is orders of magnitude")
    print("faster (often 100x-600x) than the iterrows loop. iterrows constructs a")
    print("Python Series object for EVERY row and does the arithmetic in the")
    print("interpreter, boxing each value; the column expression runs a single C pass")
    print("over contiguous typed NumPy arrays (Deep T). This is the cardinal rule of")
    print("pandas performance, and it is Chapter 96's vectorization rule at the table")
    print("level: NEVER iterate rows (iterrows, itertuples, a for loop over the")
    print("frame). Express the computation as whole-column operations, boolean masks,")
    print("and groupby aggregations, and pandas does it in C. A row loop over a large")
    print("DataFrame is the number-one pandas performance mistake.")


if __name__ == "__main__":
    main()
