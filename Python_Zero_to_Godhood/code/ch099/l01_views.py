"""Listing 99.1 - views vs copies: a slice shares memory; fancy indexing copies.

A basic SLICE of a NumPy array (arr[1:9], arr[::2], arr.T) is a zero-copy VIEW: it
shares the parent's memory, recording only an offset and per-axis STRIDES, so it
costs O(1) memory and WRITING to it changes the parent. FANCY indexing (a boolean
mask arr[mask], or an index list arr[[0,2,4]]) cannot be expressed with strides, so
it returns a COPY (O(n) memory, independent of the parent). Knowing which you have
matters for memory (the benchmark: a view is bytes, a copy is the whole slice) and
for correctness (mutating a view is a spooky action on the original). This listing
shows the distinction on small deterministic arrays.
"""

import numpy as np


def main() -> None:
    arr = np.arange(10)

    print("--- a slice is a VIEW (shares memory) ---")
    sl = arr[2:7]
    print(f"  arr[2:7]           : {sl.tolist()}")
    print(f"  shares arr's data  : {sl.base is arr}")
    print(f"  owns its data      : {sl.flags.owndata}  (False = a view)")

    print("--- writing to a view CHANGES the parent (spooky action) ---")
    sl[0] = 999                       # writes into arr's memory
    print(f"  after sl[0] = 999, arr : {arr.tolist()}  (arr[2] changed!)")
    arr[2] = 2                        # restore

    print("--- fancy/boolean indexing is a COPY (independent) ---")
    evens = arr[arr % 2 == 0]         # boolean mask -> copy
    print(f"  arr[arr % 2 == 0]  : {evens.tolist()}")
    print(f"  owns its data      : {evens.flags.owndata}  (True = a copy)")
    evens[0] = -100                   # does NOT affect arr
    print(f"  after evens[0]=-100, arr[0] : {arr[0]}  (unchanged)")

    print("--- strides make views work (even non-contiguous ones) ---")
    step = arr[::2]                   # every other element: a view
    print(f"  arr[::2]           : {step.tolist()}  (view, owndata={step.flags.owndata})")
    print(f"  arr itemsize {arr.itemsize}, arr[::2] stride {step.strides[0]} (skips one element)")
    m = np.arange(6).reshape(2, 3)
    print(f"  m.T is a view (transpose, no copy) : {not m.T.flags.owndata}")

    print("--- the rule ---")
    print(f"  slice -> view (shared memory, O(1), writes through); .copy() to detach")
    print(f"  fancy/boolean index -> copy (independent, O(n))")


if __name__ == "__main__":
    main()
