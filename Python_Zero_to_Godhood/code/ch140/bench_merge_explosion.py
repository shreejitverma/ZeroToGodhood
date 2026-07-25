"""Benchmark 140.1 - the merge row explosion: duplicate keys multiply rows.

The most dangerous merge bug is not slowness, it is a silent row EXPLOSION. When a key
value appears m times on the left and n times on the right, the merge emits m*n rows for
that key. So a merge of two small frames that share a repeated key can produce a
combinatorially larger result. This measures it: merging a frame of 2,000 rows (one
repeated key) with another of 2,000 rows (same key) produces 2000*2000 = 4,000,000 rows,
from 4,000 input rows. It also shows validate= catching the duplicates before they explode.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from _harness.bench import provenance  # noqa: E402

M = 2000


def main():
    print(f"=== 140.1  merge row explosion: {M} x {M} rows on one shared key ===")
    print(provenance())
    print()

    left = pd.DataFrame({"k": ["x"] * M, "a": range(M)})      # key 'x' repeated M times
    right = pd.DataFrame({"k": ["x"] * M, "b": range(M)})     # key 'x' repeated M times

    t0 = time.perf_counter()
    merged = left.merge(right, on="k")
    t_merge = time.perf_counter() - t0

    print(f"  input rows (left + right) : {len(left) + len(right):,}")
    print(f"  merged output rows        : {len(merged):,}   (= {M} x {M})")
    print(f"  blow-up factor            : {len(merged) // (len(left) + len(right)):,}x the input")
    print(f"  time to build the explosion : {t_merge * 1e3:.0f} ms")

    caught = False
    try:
        left.merge(right, on="k", validate="one_to_one")
    except Exception:
        caught = True
    print(f"  validate='one_to_one' catches it first : {caught}")

    del merged

    print()
    print("Reading this. Four thousand input rows became four MILLION output rows,")
    print("because the shared key 'x' appears 2000 times on each side and the merge")
    print("emits every left-right pairing (2000 * 2000). This is the number-one merge")
    print("bug: an unintended duplicate key (a non-unique join column you assumed was")
    print("unique) silently multiplies your data, blowing up memory and corrupting")
    print("every downstream aggregate. It is not an error, it is a wrong (huge)")
    print("result. The defense: know the cardinality of your join (one-to-one,")
    print("one-to-many, many-to-many) and assert it with validate=, which raises")
    print("BEFORE the explosion if the keys are not what you expect. Always validate")
    print("a merge whose keys you believe are unique.")


if __name__ == "__main__":
    main()
