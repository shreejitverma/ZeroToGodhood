"""Benchmark 128.1 - multiprocessing gives real CPU parallelism; threads do not.

Chapter 46 showed threads give ~1x on CPU-bound work (the GIL serializes them).
multiprocessing uses separate processes, each with its own GIL, so CPU-bound work
runs truly in parallel across cores. This measures four CPU-bound tasks done serially
versus on a Pool of four processes. The pool version is several times faster, the
parallelism threads could not deliver, at the cost of process startup and pickling.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import multiprocessing as mp
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

CPU_N = 8_000_000
TASKS = 4


def cpu_task(n):
    s = 0
    for i in range(n):
        s += i * i
    return s


def main():
    print(f"=== 128.1  {TASKS} CPU-bound tasks: serial vs a Pool of {TASKS} processes ===")
    print(provenance())
    print()

    work = [CPU_N] * TASKS

    t0 = time.perf_counter()
    serial = [cpu_task(n) for n in work]
    t_serial = time.perf_counter() - t0

    t0 = time.perf_counter()
    with mp.Pool(TASKS) as pool:
        parallel = pool.map(cpu_task, work)
    t_parallel = time.perf_counter() - t0

    print(f"  serial (one process)      : {t_serial * 1000:6.0f} ms   1.0x")
    print(f"  Pool of {TASKS} processes       : {t_parallel * 1000:6.0f} ms   {t_serial / t_parallel:.2f}x faster")
    print(f"  results identical         : {serial == parallel}")

    print()
    print("Reading this. Four CPU-bound tasks run several times faster across four")
    print("processes than serially, because each process has its OWN GIL and runs on")
    print("its own core, real parallelism, exactly what threads (Chapter 46) could")
    print("not give for CPU work. The cost is what threads avoid: each process starts")
    print("a fresh interpreter, and inputs/results are pickled and copied between")
    print("processes, so multiprocessing pays a startup and data-transfer tax. It")
    print("wins when each task does substantial CPU work that dwarfs that tax (the")
    print("same 'amortize the boundary' rule as the C FFI). For fine-grained tasks or")
    print("large data, the pickling cost can erase the parallelism, measure. For")
    print("CPU parallelism without the copying, the free-threaded build (Deep L) is")
    print("the emerging alternative.")


if __name__ == "__main__":
    main()
