"""Benchmark 48.1 - multiprocessing wins only when compute >> data-shipping.

Two workloads on a 4-process Pool versus serial:
  A: heavy compute, tiny data     -> parallelism wins (the CPU work dominates).
  B: trivial compute, big data    -> the Pool is pure overhead, because every
     task's multi-megabyte payload must be pickled, piped to a worker, and
     unpickled, and that IPC cost dwarfs the (nonexistent) compute.

The lesson: a process Pool buys parallel CPU but charges serialization for every
argument and result. If you are not compute-bound, multiprocessing can be SLOWER
than serial.

Does its own timing (it manages a Pool), guarded by __main__. See _harness/bench.py.
"""

import multiprocessing as mp
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402


def heavy(n):
    total = 0
    for i in range(n):
        total += i * i
    return total % 1000


def touch(payload):
    return len(payload)      # trivial; payload was pickled+shipped to get here


def best(fn, repeat=5):
    times = []
    for _ in range(repeat):
        times.append(fn())
    return min(times)


def main():
    print("=== 48.1  multiprocessing: compute-bound vs data-bound ===")
    print(provenance())
    print()

    compute_tasks = [3_000_000] * 8
    big_payloads = [b"x" * 4_000_000 for _ in range(8)]

    def serial_A():
        t0 = time.perf_counter()
        [heavy(n) for n in compute_tasks]
        return time.perf_counter() - t0

    def pool_A():
        with mp.Pool(4) as pool:
            t0 = time.perf_counter()
            pool.map(heavy, compute_tasks)
            return time.perf_counter() - t0

    def serial_B():
        t0 = time.perf_counter()
        [touch(p) for p in big_payloads]
        return time.perf_counter() - t0

    def pool_B():
        with mp.Pool(4) as pool:
            t0 = time.perf_counter()
            pool.map(touch, big_payloads)
            return time.perf_counter() - t0

    sa, pa = best(serial_A), best(pool_A)
    sb, pb = best(serial_B), best(pool_B)

    print("  A  heavy compute, tiny data (8 x 3M-iteration loops):")
    print(f"       serial {sa * 1000:7.0f} ms   pool(4) {pa * 1000:7.0f} ms   speedup {sa / pa:5.2f}x")
    print("  B  trivial compute, big data (8 x 4 MB payloads):")
    print(f"       serial {sb * 1000:7.1f} ms   pool(4) {pb * 1000:7.0f} ms   (pool is all IPC overhead)")

    print()
    print("Reading this. In A the CPU work dominates, so four workers finish in")
    print("well under the serial time: real parallelism, GIL sidestepped. In B the")
    print("compute is nothing (len of a bytes) but each 4 MB payload must be")
    print("pickled, piped to a worker, and unpickled, so the Pool spends all its")
    print("time shipping data and is far SLOWER than doing the trivial work in")
    print("place. multiprocessing is not free parallelism: you pay serialization")
    print("for every argument and result. Use it when compute dominates the data")
    print("you must ship; otherwise the IPC erases the win (or use shared memory,")
    print("Chapter 44, to avoid copying).")


if __name__ == "__main__":
    main()
