"""Listing 138.1 - the pandas DataFrame: typed columns with an index and a rich API.

A DataFrame is the tabular structure at the center of data engineering: a set of NAMED,
TYPED COLUMNS (each a Series, backed by a NumPy array, Deep T) sharing a row INDEX. It
is the structured array of Chapter 104 grown up: heterogeneous typed columns, but with
labels, alignment, missing-data handling, and a large operation vocabulary. The golden
rule is the same as NumPy (Chapter 96): operate on whole COLUMNS (vectorized, in C),
never loop over rows. This listing builds a DataFrame and shows column access, vectorized
column arithmetic, and boolean filtering (Chapter 102's masks, at the table level), using
version-stable accessors so the output is identical across pandas versions.
"""

import pandas as pd


def main() -> None:
    print("--- a DataFrame is named, typed columns sharing a row index ---")
    df = pd.DataFrame({
        "symbol": ["AAA", "BBB", "CCC", "DDD"],
        "price": [10.0, 20.0, 30.0, 40.0],
        "qty": [5, 3, 8, 2],
    })
    print(f"  shape (rows, cols) : {df.shape}")
    print(f"  column names       : {list(df.columns)}")
    # numeric dtypes are stable across pandas versions; the string column's dtype
    # name changed (object -> str in pandas 3.0), so we report it structurally.
    print(f"  price dtype        : {df['price'].dtype}")
    print(f"  qty dtype          : {df['qty'].dtype}")
    print(f"  symbol is text     : {df['symbol'].dtype != df['qty'].dtype}")

    print("--- a column is a Series (a typed vector, backed by NumPy) ---")
    print(f"  df['qty'] as a list : {df['qty'].tolist()}")
    print(f"  df['qty'].sum()     : {int(df['qty'].sum())}")
    print(f"  df['price'].mean()  : {float(df['price'].mean())}")

    print("--- vectorized column arithmetic: a whole new column in one C pass ---")
    notional = df["price"] * df["qty"]              # elementwise, no loop
    print(f"  (price * qty).tolist()    : {notional.tolist()}")
    print(f"  total notional            : {float(notional.sum())}")

    print("--- boolean filtering: a mask over rows (Chapter 102, at table level) ---")
    big = df[df["qty"] > 3]                          # rows where qty > 3
    print(f"  rows with qty > 3 (symbols) : {big['symbol'].tolist()}")
    print(f"  how many                    : {len(big)}")

    print("--- add a computed column (assign back) ---")
    df["notional"] = notional
    print(f"  columns after adding 'notional' : {list(df.columns)}")

    print("--- the rule ---")
    print(f"  a DataFrame is typed columns + an index; operate on whole columns")
    print(f"  (vectorized, in C), filter with masks, never loop over rows")


if __name__ == "__main__":
    main()
