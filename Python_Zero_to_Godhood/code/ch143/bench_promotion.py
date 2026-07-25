"""Benchmark 143.1 - the int-to-float NaN promotion silently corrupts large integer IDs.

This is a CORRECTNESS measurement, not a timing one. A single NaN in an int64 column
promotes it to float64. float64 represents integers exactly only up to 2**53; above
that, distinct integers ROUND to the same float, so an ID column of large integers
COLLIDES after promotion, distinct records silently merge. This counts the collisions
for 1000 consecutive integer IDs starting at 2**53, and shows nullable Int64 avoids them.

Does its own measuring, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from _harness.bench import provenance  # noqa: E402

BASE = 2 ** 53
COUNT = 1000


def main():
    print(f"=== 143.1  int64 -> float64 promotion: ID collisions above 2**53 ===")
    print(provenance())
    print()

    ids = pd.Series(range(BASE, BASE + COUNT), dtype="int64")
    distinct_int = ids.nunique()

    promoted = ids.astype("float64")             # what a single NaN would force
    distinct_float = promoted.nunique()

    nullable = pd.Series(pd.array(range(BASE, BASE + COUNT), dtype="Int64"))
    distinct_nullable = nullable.nunique()

    print(f"  distinct int64 IDs                 : {distinct_int:,}   (all unique)")
    print(f"  distinct after float64 promotion   : {distinct_float:,}   (collisions!)")
    print(f"  IDs silently merged (collisions)   : {distinct_int - distinct_float:,}")
    print(f"  distinct with nullable Int64        : {distinct_nullable:,}   (unaffected)")

    print()
    print("Reading this. A single missing value in an integer ID column promotes the")
    print("whole column to float64 (because NaN is a float), and float64 cannot")
    print("represent integers above 2**53 exactly, so distinct large IDs round to the")
    print("same float and COLLIDE: here 1000 unique IDs become ~500, silently merging")
    print("distinct records. This is a real, dangerous data-corruption bug, no error,")
    print("just wrong (merged) data, that surfaces as duplicate-looking rows, wrong")
    print("join results, and lost records. The fix is nullable dtypes: pandas Int64")
    print("(capital I) is an integer type that allows missing values (pd.NA) WITHOUT")
    print("promoting to float, so the IDs stay exact. For integer keys/IDs that may")
    print("have missing values, use Int64, never let a NaN turn them into float64.")


if __name__ == "__main__":
    main()
