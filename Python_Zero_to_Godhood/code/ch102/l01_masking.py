"""Listing 102.1 - boolean masks and np.where: vectorized conditionals, no loop.

Conditional logic over an array does NOT need a Python loop. A comparison produces
a BOOLEAN array; from there you can:
  - SELECT elements: arr[mask] (a copy, Chapter 99)
  - UPDATE in place: arr[mask] = value (fancy assignment writes through)
  - BRANCH elementwise: np.where(cond, x, y) (pick x where cond else y)
  - AGGREGATE: mask.sum() (count), mask.any(), mask.all()
All run in C, tens to hundreds of times faster than a Python if/else loop (the
benchmark). This listing shows each on a small deterministic array.
"""

import numpy as np


def main() -> None:
    a = np.array([-2, -1, 0, 1, 2, 3])
    print(f"  a : {a.tolist()}")

    print("--- a comparison makes a boolean array ---")
    print(f"  a > 0 : {(a > 0).tolist()}")

    print("--- SELECT with a mask (a copy of the matching elements) ---")
    print(f"  a[a > 0] : {a[a > 0].tolist()}   (the positives)")

    print("--- BRANCH elementwise with np.where(cond, x, y) ---")
    print(f"  np.where(a > 0, a, 0) : {np.where(a > 0, a, 0).tolist()}   (a ReLU: keep positives, else 0)")

    print("--- UPDATE in place with mask assignment (writes through) ---")
    b = a.copy()
    b[b < 0] = 0                     # clamp negatives to zero, in place
    print(f"  b[b < 0] = 0 -> {b.tolist()}")

    print("--- AGGREGATE a mask: count / any / all ---")
    print(f"  (a > 0).sum() (count) : {(a > 0).sum()}")
    print(f"  (a < 0).any()         : {(a < 0).any()}")
    print(f"  (a >= -2).all()       : {(a >= -2).all()}")

    print("--- combine masks with & | ~ (parenthesize each comparison) ---")
    mask = (a > -2) & (a < 2)        # NOT 'and'; use & and parentheses
    print(f"  (a > -2) & (a < 2) selects : {a[mask].tolist()}")

    print("--- the rule ---")
    print(f"  express conditional array logic with masks / np.where, not a loop")
    print(f"  arr[mask] selects (copy); arr[mask]=v updates in place; & | ~ combine")


if __name__ == "__main__":
    main()
