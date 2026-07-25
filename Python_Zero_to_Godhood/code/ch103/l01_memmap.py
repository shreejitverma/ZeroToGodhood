"""Listing 103.1 - np.memmap: an array on disk, larger than RAM, paged in on demand.

np.memmap maps an array file into the address space (like mmap, Chapter 44) instead
of loading it. So OPENING a multi-gigabyte array file costs almost nothing (the
benchmark: a few hundred bytes), and you index, slice, and compute on it as a normal
ndarray, the OS pages in only the parts you actually touch. This lets you work with
arrays LARGER THAN RAM: process a 100 GB dataset a slice at a time, with only the
touched pages resident. A writable memmap (mode='r+'/'w+') writes changes back to the
file. This listing shows creating, reading, and updating a memmap deterministically.
"""

import os
import tempfile

import numpy as np


def main() -> None:
    d = tempfile.mkdtemp()
    path = os.path.join(d, "array.dat")

    print("--- create an array file on disk (mode='w+') and fill it ---")
    a = np.memmap(path, dtype=np.int64, mode="w+", shape=(1000,))
    a[:] = np.arange(1000)              # write values through to the file
    a.flush()                          # ensure it reaches disk
    del a                              # close the mapping

    print("--- open it read-only: no load, it IS the file's bytes ---")
    m = np.memmap(path, dtype=np.int64, mode="r", shape=(1000,))
    print(f"  is an ndarray        : {isinstance(m, np.ndarray)}")
    print(f"  m[0], m[-1]          : {m[0]}, {m[-1]}   (read from disk on access)")
    print(f"  m[100:105]           : {m[100:105].tolist()}")
    print(f"  m[:10].sum()         : {int(m[:10].sum())}   (only these pages paged in)")

    print("--- compute on a slice (only the touched region loads) ---")
    print(f"  m[500:600].mean()    : {float(m[500:600].mean())}")
    del m

    print("--- open writable (mode='r+') and update in place; changes hit the file ---")
    w = np.memmap(path, dtype=np.int64, mode="r+", shape=(1000,))
    w[0] = 999
    w.flush()
    del w
    check = np.memmap(path, dtype=np.int64, mode="r", shape=(1000,))
    print(f"  after w[0]=999, reopened m[0] : {check[0]}   (persisted to disk)")
    del check
    os.remove(path)

    print("--- the rule ---")
    print(f"  np.memmap: work with an array on disk, larger than RAM, paged in on")
    print(f"  demand; only touched pages are resident. np.load/fromfile loads it all.")


if __name__ == "__main__":
    main()
