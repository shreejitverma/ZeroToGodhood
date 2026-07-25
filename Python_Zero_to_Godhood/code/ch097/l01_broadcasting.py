"""Listing 97.1 - broadcasting: operate across shapes without materializing copies.

Broadcasting lets NumPy apply an operation to arrays of DIFFERENT but compatible
shapes as if the smaller were expanded to match, WITHOUT actually building the
expanded array. Compatible means: compare shapes from the right; dimensions match
if equal or one of them is 1 (which stretches). So a (M, N) matrix plus a (N,) row
adds the row to every row, and a (M, 1) column plus a (N,) row produces an (M, N)
grid, in both cases the small operand is NEVER copied M or N times; NumPy streams
it in C. This saves the O(M*N) temporary that explicit tiling (np.tile) allocates
(the benchmark measures 2x memory). This listing shows the shape rules
deterministically.
"""

import numpy as np


def main() -> None:
    print("--- a scalar broadcasts across the whole array ---")
    a = np.array([1, 2, 3, 4])
    print(f"  a * 10 : {(a * 10).tolist()}")

    print("--- a (N,) row broadcasts across each row of a (M, N) matrix ---")
    mat = np.zeros((3, 4), dtype=np.int64)
    row = np.array([1, 2, 3, 4])
    print(f"  matrix + row :\n{mat + row}")

    print("--- a (M, 1) column + a (N,) row -> (M, N) grid (both stretch) ---")
    col = np.array([[0], [10], [20]])       # shape (3, 1)
    r = np.array([1, 2, 3])                 # shape (3,)
    grid = col + r                          # -> (3, 3)
    print(f"  col.shape {col.shape} + row.shape {r.shape} -> {grid.shape}:\n{grid}")

    print("--- the rule for compatibility (align shapes from the right) ---")
    print(f"  (3, 4) and (4,)   compatible : True  (4==4)")
    print(f"  (3, 1) and (3,)   compatible : True  (1 stretches to 3)")
    x = np.ones((3, 4))
    try:
        _ = x + np.ones(3)                  # (3,4) + (3,): 4 != 3, not compatible
        ok = True
    except ValueError:
        ok = False
    print(f"  (3, 4) and (3,)   compatible : {ok}  (4 != 3: ValueError)")

    print("--- no expanded copy is made (broadcasting streams the small operand) ---")
    print(f"  matrix + row gives the same result as tiling the row, but without")
    print(f"  allocating M copies of it (the benchmark shows the memory saved)")


if __name__ == "__main__":
    main()
