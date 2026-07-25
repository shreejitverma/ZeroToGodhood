"""Listing 131.1 - shared_memory: zero-copy data across processes.

Chapter 47 showed multiprocessing's cost: data passed to workers is PICKLED and
COPIED. For large data that dominates. multiprocessing.shared_memory is the answer: a
named block of memory that MULTIPLE PROCESSES map into their address space, so they
share the SAME physical bytes with NO copy. One process creates and fills it; others
attach by NAME and read/write the same memory (the cross-process form of Chapter 44's
buffer sharing with C). This listing shows two handles sharing one block in-process
(the mechanism), then real worker PROCESSES attaching by name (proving cross-process).
"""

from multiprocessing import shared_memory, Pool

import numpy as np


def worker_sum(name):
    """Runs in a separate PROCESS: attach the shared block by name and sum it."""
    shm = shared_memory.SharedMemory(name=name)
    arr = np.ndarray((5,), dtype=np.int64, buffer=shm.buf)
    total = int(arr.sum())               # reads the parent's data, no copy/pickle
    shm.close()
    return total


def main() -> None:
    print("--- create a shared block and fill it via a NumPy view ---")
    shm = shared_memory.SharedMemory(create=True, size=40)   # 5 x int64
    arr = np.ndarray((5,), dtype=np.int64, buffer=shm.buf)
    arr[:] = [10, 20, 30, 40, 50]
    print(f"  shared block created; size >= requested : {shm.size >= 40}")

    print("--- a SECOND handle to the same name sees the SAME memory (no copy) ---")
    shm2 = shared_memory.SharedMemory(name=shm.name)
    arr2 = np.ndarray((5,), dtype=np.int64, buffer=shm2.buf)
    print(f"  handle 2 sees handle 1's data : {arr2.tolist()}")
    arr2[0] = 999                        # write through handle 2
    print(f"  write via handle 2, read via handle 1 : {arr[0]}   (same physical memory)")
    arr2[0] = 10                         # restore for the cross-process check
    shm2.close()

    print("--- real worker PROCESSES attach by name and read it (no pickling) ---")
    with Pool(2) as pool:
        sums = pool.map(worker_sum, [shm.name, shm.name])
    print(f"  two worker processes summed the shared block : {sums}   (10+20+30+40+50)")

    shm.close()
    shm.unlink()                         # free the block (creator's responsibility)

    print("--- the rule ---")
    print(f"  shared_memory maps one physical block into many processes: share large")
    print(f"  data by NAME with zero copy, instead of pickling it to each worker")


if __name__ == "__main__":
    main()
