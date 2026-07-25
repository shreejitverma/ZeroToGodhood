"""Listing 144.1 - reshaping: pivot (long to wide), melt (wide to long), pivot_table.

Tabular data comes in two shapes. LONG (tidy) format has one row per observation, with
a column identifying the variable: (date, metric, value). WIDE format spreads a variable
across columns: date as the index, each metric its own column. Analysis and storage
favor different shapes, and reshaping converts between them:
  - pivot: long -> wide (a column's values become new columns).
  - melt: wide -> long (columns become rows under a variable column).
  - pivot_table: pivot WITH aggregation, so it handles duplicate index/column pairs
    (a spreadsheet pivot table).
Long/tidy is the canonical analysis form; wide is compact for dense data (the benchmark).
This listing shows each, deterministically.
"""

import pandas as pd


def main() -> None:
    print("--- LONG (tidy) format: one row per (date, metric) observation ---")
    long = pd.DataFrame({
        "date": ["d1", "d1", "d2", "d2"],
        "metric": ["a", "b", "a", "b"],
        "value": [1, 2, 3, 4],
    })
    print(f"  long shape (rows, cols) : {long.shape}")

    print("--- pivot: long -> WIDE (metric values become columns) ---")
    wide = long.pivot(index="date", columns="metric", values="value")
    print(f"  wide columns (the metrics) : {list(wide.columns)}")
    print(f"  wide 'a' column by date    : {wide['a'].tolist()}   (d1=1, d2=3)")
    print(f"  wide shape                 : {wide.shape}")

    print("--- melt: WIDE -> long (columns become rows) ---")
    flat = wide.reset_index()
    melted = flat.melt(id_vars="date", var_name="metric", value_name="value")
    print(f"  melted back to rows : {len(melted)}")
    print(f"  metric column values : {sorted(melted['metric'].tolist())}")

    print("--- pivot_table: pivot WITH aggregation (handles duplicates) ---")
    dup = pd.DataFrame({"group": ["x", "x", "y"], "value": [10, 20, 30]})
    pt = dup.pivot_table(index="group", values="value", aggfunc="sum")
    print(f"  pivot_table sum per group : {pt['value'].to_dict()}   (x: 10+20, y: 30)")

    print("--- the rule ---")
    print(f"  pivot (long->wide), melt (wide->long), pivot_table (pivot + aggregate);")
    print(f"  keep data tidy (long) for analysis, reshape to wide for display/compactness")


if __name__ == "__main__":
    main()
