"""Listing 139.1 - groupby: split-apply-combine, the core aggregation pattern.

After "operate on columns" (Chapter 138), the second pillar of pandas is GROUPBY: the
split-apply-combine pattern. groupby(key) SPLITS the rows into groups by a key column,
APPLIES an aggregation to each group's values, and COMBINES the results into a new frame
indexed by the group key. "Total sales per region", "average latency per endpoint",
"count per category", all are one groupby. It runs in C (the grouping and aggregation
are vectorized), so it is far faster and far clearer than a manual per-group loop. This
listing shows sum/mean/count and multi-aggregation, deterministically.
"""

import pandas as pd


def main() -> None:
    df = pd.DataFrame({
        "region": ["east", "east", "west", "west", "east"],
        "sales": [10, 20, 40, 50, 30],
    })

    print("--- split-apply-combine: one aggregate per group ---")
    print(f"  sum per region  : {df.groupby('region')['sales'].sum().to_dict()}")
    print(f"  mean per region : {df.groupby('region')['sales'].mean().to_dict()}")
    print(f"  count per region: {df.groupby('region')['sales'].count().to_dict()}")
    print(f"  max per region  : {df.groupby('region')['sales'].max().to_dict()}")

    print("--- multiple aggregations at once with .agg([...]) ---")
    agg = df.groupby("region")["sales"].agg(["sum", "mean", "count"])
    print(f"  agg sum column   : {agg['sum'].to_dict()}")
    print(f"  agg mean column  : {agg['mean'].to_dict()}")

    print("--- group by MULTIPLE keys ---")
    df2 = pd.DataFrame({
        "region": ["east", "east", "west", "west"],
        "product": ["a", "b", "a", "a"],
        "sales": [10, 20, 30, 40],
    })
    by_two = df2.groupby(["region", "product"])["sales"].sum()
    print(f"  (region, product) -> sum : {by_two.to_dict()}")

    print("--- the result is indexed by the group key (a new frame/series) ---")
    result = df.groupby("region")["sales"].sum()
    print(f"  result index (the keys)  : {sorted(result.index.tolist())}")
    print(f"  look up one group        : east -> {int(result['east'])}")

    print("--- the rule ---")
    print(f"  groupby(key).agg splits rows by key, aggregates each group in C, and")
    print(f"  combines into a keyed result; use it instead of a per-group Python loop")


if __name__ == "__main__":
    main()
