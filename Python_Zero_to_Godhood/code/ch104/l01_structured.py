"""Listing 104.1 - structured arrays: named heterogeneous fields, columnar in C.

A structured dtype gives an ndarray NAMED FIELDS of different types, so one
contiguous typed block holds records (like rows of a table) instead of a Python
list of dicts/objects. Field access (a['age']) returns a VIEW of that column,
which you vectorize like any array (a['age'].mean()), and boolean masks work
ACROSS fields (a[a['age'] > 26]). It is columnar, typed, contiguous storage: the
memory and speed of arrays, with the shape of records. This listing shows the
dtype, field access, column vectorization, and cross-field masking.
"""

import numpy as np


def main() -> None:
    print("--- a structured dtype: named fields, each with its own type ---")
    dt = np.dtype([("name", "U10"), ("age", "i4"), ("score", "f8")])
    a = np.zeros(3, dtype=dt)
    a["name"] = ["ann", "bob", "cy"]
    a["age"] = [30, 25, 41]
    a["score"] = [9.5, 8.0, 7.5]
    print(f"  dtype       : {a.dtype}")
    print(f"  one record  : {tuple(a[0].tolist())}   (a[0] is a record)")

    print("--- field access returns a VIEW of that column (an ndarray) ---")
    print(f"  a['age']         : {a['age'].tolist()}")
    print(f"  a['age'].mean()  : {a['age'].mean()}   (vectorized column op)")
    print(f"  a['score'].max() : {a['score'].max()}")

    print("--- boolean masks work ACROSS fields ---")
    older = a[a["age"] > 26]                 # mask on one field, select whole records
    print(f"  a[a['age'] > 26]['name'] : {older['name'].tolist()}")

    print("--- it is ONE contiguous typed block (record itemsize) ---")
    print(f"  itemsize (bytes/record) : {a.itemsize}   (40 name + 4 age + 8 score)")
    print(f"  field names             : {a.dtype.names}")

    print("--- the rule ---")
    print(f"  a structured array is columnar typed records in one C block:")
    print(f"  field access is a view, columns vectorize, masks span fields")


if __name__ == "__main__":
    main()
