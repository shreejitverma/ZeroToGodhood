"""Listing 140.1 - merge/join: combining DataFrames on keys, and the row-explosion trap.

merge combines two DataFrames by matching a KEY column, the relational join. The `how`
argument sets which rows survive:
  - inner (default): only keys present in BOTH frames.
  - left: all left rows, NaN where the right has no match.
  - right / outer: symmetric variants (outer keeps all keys from either side).
The critical hazard is DUPLICATE KEYS: if a key appears m times on the left and n times
on the right, the merge produces m*n rows for that key, a row EXPLOSION that silently
inflates your data. validate= catches unintended duplicates, and indicator= records
which side each row matched. This listing shows the join types and the explosion.
"""

import pandas as pd


def main() -> None:
    orders = pd.DataFrame({"symbol": ["AAA", "BBB", "AAA", "CCC"], "qty": [10, 20, 30, 40]})
    ref = pd.DataFrame({"symbol": ["AAA", "BBB", "CCC"], "sector": ["tech", "fin", "energy"]})

    print("--- inner merge (default): keep keys present in BOTH ---")
    inner = orders.merge(ref, on="symbol")
    print(f"  columns after merge : {list(inner.columns)}")
    print(f"  sectors aligned to each order : {inner['sector'].tolist()}")

    print("--- left merge: keep all LEFT rows, NaN where no match ---")
    partial = pd.DataFrame({"symbol": ["AAA", "BBB"], "sector": ["tech", "fin"]})
    left = orders.merge(partial, on="symbol", how="left")
    ccc_missing = bool(left[left["symbol"] == "CCC"]["sector"].isna().all())
    print(f"  all 4 left rows kept : {len(left) == 4}")
    print(f"  CCC has no match -> sector is NaN : {ccc_missing}")

    print("--- outer merge with indicator: which side each key came from ---")
    a = pd.DataFrame({"k": ["a", "b"], "x": [1, 2]})
    b = pd.DataFrame({"k": ["a", "c"], "y": [3, 4]})
    outer = a.merge(b, on="k", how="outer", indicator=True)
    print(f"  outer keeps all keys : {len(outer)} rows (a, b, c)")
    print(f"  match indicator values : {sorted(outer['_merge'].astype(str).tolist())}")

    print("--- the TRAP: duplicate keys multiply rows (m x n) ---")
    dup_left = pd.DataFrame({"k": ["x", "x"], "a": [1, 2]})       # key x appears twice
    dup_right = pd.DataFrame({"k": ["x", "x", "x"], "b": [1, 2, 3]})  # key x three times
    exploded = dup_left.merge(dup_right, on="k")
    print(f"  2 left x 3 right (same key) -> {len(exploded)} rows   (2 * 3 = 6, exploded)")

    print("--- validate= catches unintended duplicate keys ---")
    try:
        dup_left.merge(dup_right, on="k", validate="one_to_one")
    except Exception as e:
        print(f"  validate='one_to_one' raised {type(e).__name__} (caught the duplicates)")

    print("--- the rule ---")
    print(f"  merge joins on a key; pick how= (inner/left/outer); beware DUPLICATE")
    print(f"  keys (m*n row explosion), use validate= to assert the expected cardinality")


if __name__ == "__main__":
    main()
