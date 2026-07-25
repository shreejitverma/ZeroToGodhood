"""Listing 143.1 - missing data: NaN, its handling, and the int-to-float promotion trap.

Real data has holes, and pandas represents a missing float as NaN (Not a Number). NaN
has surprising, must-know behaviour:
  - detect/remove/fill: isna(), dropna(), fillna(value), ffill() (forward-fill).
  - aggregations SKIP NaN by default (mean of [1, NaN, 3] is 2, over 2 values).
  - arithmetic PROPAGATES NaN (NaN + 1 is NaN).
  - NaN != NaN (it is not equal to itself), so you detect it with isna(), never == NaN.
  - a NaN in an INTEGER column PROMOTES the whole column to float64, because NaN is a
    float, and that can silently corrupt large integer IDs (the benchmark).
The modern fix is NULLABLE dtypes (Int64, with capital I): integers that allow missing
values (pd.NA) without promotion. This listing shows each, deterministically.
"""

import numpy as np
import pandas as pd


def main() -> None:
    s = pd.Series([1.0, np.nan, 3.0, np.nan, 5.0])

    print("--- detect, drop, fill ---")
    print(f"  isna().sum() (count missing) : {int(s.isna().sum())}")
    print(f"  dropna()                     : {s.dropna().tolist()}")
    print(f"  fillna(0)                    : {s.fillna(0).tolist()}")
    print(f"  ffill() (carry last forward) : {s.ffill().tolist()}")

    print("--- aggregations SKIP NaN; arithmetic PROPAGATES it ---")
    print(f"  mean() skips NaN : {float(s.mean())}   (mean of 1,3,5)")
    print(f"  sum() skips NaN  : {float(s.sum())}")
    print(f"  (s + 1) is NaN where s was NaN : {(s + 1).isna().tolist()}")

    print("--- NaN != NaN: detect with isna(), never == ---")
    print(f"  np.nan == np.nan : {np.nan == np.nan}   (False! use isna)")

    print("--- a NaN in an INT column promotes it to float64 ---")
    df = pd.DataFrame({"a": [1, 2, 3]}, dtype="int64")
    print(f"  original dtype : {df['a'].dtype}")
    df = df.astype("float64")
    df.loc[1, "a"] = np.nan
    print(f"  after a NaN    : {df['a'].dtype}   (int64 -> float64)")

    print("--- the fix: nullable Int64 allows missing WITHOUT float promotion ---")
    nn = pd.array([1, 2, None, 4], dtype="Int64")     # capital I: nullable integer
    print(f"  nullable Int64 values : {[None if v is pd.NA else int(v) for v in nn]}")
    print(f"  still an integer type : {str(nn.dtype) == 'Int64'}")
    print(f"  and tracks missing    : {pd.Series(nn).isna().tolist()}")

    print("--- the rule ---")
    print(f"  detect NaN with isna (never ==); dropna/fillna/ffill to handle it;")
    print(f"  aggregations skip it, arithmetic propagates it; use Int64 for nullable ints")


if __name__ == "__main__":
    main()
