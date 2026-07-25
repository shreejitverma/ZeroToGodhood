"""Listing 128.1 - multiprocessing: separate processes, separate GILs, separate memory.

Threads (Chapter 46) share memory but share the one GIL, so they cannot parallelize
CPU-bound Python. multiprocessing sidesteps the GIL by using separate PROCESSES, each
a full Python interpreter with its OWN GIL, so they run truly in parallel on multiple
cores. The trade is the mirror image of threads:
  - Processes do NOT share memory: each has its own address space, so a global changed
    in a worker does NOT affect the parent (unlike a thread).
  - Data passed between processes is PICKLED (serialized) and copied, which costs time
    and requires the data (and worker functions) to be picklable.
Pool.map distributes a function over inputs across worker processes and collects the
(ordered) results. This listing shows the separate memory and Pool.map, deterministically.
"""

import multiprocessing as mp
import os

_counter = 0                             # a module global


def bump_and_report(_):
    global _counter
    _counter += 100                      # changes THIS process's copy only
    return _counter                      # each worker starts from 0 (separate memory)


def square(x):
    return x * x


def main() -> None:
    print("--- separate memory: a worker's change does not reach the parent ---")
    with mp.Pool(2) as pool:
        worker_values = pool.map(bump_and_report, [None, None])
    # exact per-worker values depend on scheduling; the stable facts are that a
    # worker DID modify its own copy, and the parent's copy is untouched.
    print(f"  a worker incremented its own _counter : {max(worker_values) >= 100}")
    print(f"  the PARENT's _counter is untouched     : {_counter == 0}   (separate address space)")

    print("--- Pool.map distributes work and returns ORDERED results ---")
    results = None
    with mp.Pool(4) as pool:
        results = pool.map(square, [1, 2, 3, 4, 5])
    print(f"  Pool.map(square, [1..5]) : {results}")

    print("--- workers are separate PROCESSES (own PID, own interpreter, own GIL) ---")
    with mp.Pool(2) as pool:
        pids = pool.map(_getpid, range(4))
    parent = os.getpid()
    print(f"  every worker PID differs from the parent : {all(p != parent for p in pids)}")
    print(f"  the parent is one process                : {parent == os.getpid()}")

    print("--- the rule ---")
    print(f"  multiprocessing = separate processes, own GIL each (real CPU")
    print(f"  parallelism), separate memory, data copied by pickling")


def _getpid(_):
    return os.getpid()


if __name__ == "__main__":
    main()
