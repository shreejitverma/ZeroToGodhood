"""Benchmark 131.1 - shared_memory beats pickling for large cross-process data.

Chapter 47's process pools pickle and COPY their arguments to each worker. For a large
array shared by several workers, that is one copy per worker. shared_memory shares the
SAME physical block, so workers attach by name with zero copy. This measures passing an
80 MB array to four workers two ways: as a pickled Pool.map argument versus via a shared
block. The shared version avoids the copies.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import time
from multiprocessing import Pool, shared_memory
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from _harness.bench import provenance  # noqa: E402

N = 10_000_000                 # 80 MB of int64


def sum_pickled(arr):
    return int(arr.sum())


def sum_shared(name):
    shm = shared_memory.SharedMemory(name=name)
    a = np.ndarray((N,), dtype=np.int64, buffer=shm.buf)
    total = int(a.sum())
    shm.close()
    return total


def main():
    print(f"=== 131.1  pass an 80 MB array to 4 workers: pickled vs shared_memory ===")
    print(provenance())
    print()

    data = np.arange(N, dtype=np.int64)

    t0 = time.perf_counter()
    with Pool(4) as pool:
        pool.map(sum_pickled, [data, data, data, data])   # array copied to each worker
    t_pickle = time.perf_counter() - t0

    shm = shared_memory.SharedMemory(create=True, size=data.nbytes)
    buf = np.ndarray((N,), dtype=np.int64, buffer=shm.buf)
    buf[:] = data
    try:
        t0 = time.perf_counter()
        with Pool(4) as pool:
            pool.map(sum_shared, [shm.name] * 4)           # workers attach, no copy
        t_shared = time.perf_counter() - t0
    finally:
        shm.close()
        shm.unlink()

    print(f"  pickled (copy to each worker) : {t_pickle * 1000:6.0f} ms   1.0x")
    print(f"  shared_memory (no copy)       : {t_shared * 1000:6.0f} ms   {t_pickle / t_shared:.1f}x faster")

    print()
    print("Reading this. Passing the array as a Pool argument pickles and copies its")
    print("80 MB to every worker (four copies here); shared_memory copies it zero")
    print("times, the workers map the same physical block by name. So the shared")
    print("version is faster, and the gap widens with more workers or larger data")
    print("(the pickling cost scales with both). This is the cross-process form of")
    print("Chapter 44's zero-copy buffer sharing, and the fix for Chapter 47's")
    print("pickling tax when data is large and read-mostly. The cost is manual")
    print("lifecycle (create/attach/close/unlink) and manual synchronization if")
    print("workers WRITE, use it for large shared data, not small arguments.")


if __name__ == "__main__":
    main()
