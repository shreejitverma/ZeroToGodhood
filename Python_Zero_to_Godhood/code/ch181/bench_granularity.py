# requires: 3.14+
"""Benchmark 181.1 - the capstone: the same work, four executors, three grains.

A fixed budget of CPU work (about 200 ms of pure-Python arithmetic) is split
into 4 tasks, then 40, then 4,000, and pushed through a thread pool, an
interpreter pool, and a process pool (executors pre-warmed, 4 workers each),
with the sequential loop as the baseline. Total work constant; only the grain
moves.

This is the volume's decision table generated live. Scaling comes from the
build and the primitive (Chapters 93, 98); the per-task cost comes from the
boundary each primitive makes you cross (Chapter 98's invoice, Chapter 84's
rule); and grain is the knob that trades one against the other. Coarse grain:
every parallel primitive that can scale, does. Fine grain: the crossings eat
the parallelism, in the exact order of each boundary's price.

Run under 3.14 and 3.14t, as in ch174 (skipped on 3.13: no PEP 734).
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

TOTAL_ITERS = 8_000_000          # ~200 ms of work on this machine


def work(n):
    total = 0
    for i in range(n):
        j = i & 4095                 # keep operands small so one iteration
        total += j * j               # costs the same at every grain
    return total


def main():
    from concurrent.futures import (InterpreterPoolExecutor,
                                    ProcessPoolExecutor, ThreadPoolExecutor)

    pools = {
        "thread pool": ThreadPoolExecutor(4),
        "interpreter pool": InterpreterPoolExecutor(4),
        "process pool": ProcessPoolExecutor(4),
    }
    for pool in pools.values():
        list(pool.map(work, [1000] * 8))         # warm workers and imports

    grains = (4, 40, 4_000)

    def timed(fn, repeat=3):
        best = None
        for _ in range(repeat):
            t0 = time.perf_counter()
            fn()
            dt = time.perf_counter() - t0
            best = dt if best is None or dt < best else best
        return best * 1000

    print("=== 181.1  ~200 ms of CPU work, by executor and grain ===")
    print(provenance())
    print("method      : fixed total work; min of 3; pools pre-warmed (4 workers)")
    print()
    header = f"  {'executor':<18}" + "".join(f"{n:>5} tasks" for n in grains)
    print(header)
    print("  " + "-" * (len(header) - 2))

    row = f"  {'sequential':<18}"
    for n_tasks in grains:
        per = TOTAL_ITERS // n_tasks
        row += f"{timed(lambda: [work(per) for _ in range(n_tasks)]):9.0f} ms"
    print(row)

    for label, pool in pools.items():
        row = f"  {label:<18}"
        for n_tasks in grains:
            per = TOTAL_ITERS // n_tasks
            row += (f"{timed(lambda: list(pool.map(work, [per] * n_tasks))):9.0f}"
                    " ms")
        print(row)

    for pool in pools.values():
        pool.shutdown()

    print()
    print("Reading this. Down a column: who can scale at this grain. Across a")
    print("row: what this primitive's boundary costs per task. At 4 tasks of")
    print("~50 ms, every primitive that can parallelise on this build does,")
    print("and the differences are noise against the work. At 4,000 tasks of")
    print("~50 us, the ordering of the columns is the ordering of the boundary")
    print("prices measured in Chapter 98: a thread's crossing is a queue hop,")
    print("an interpreter's adds marshalling, a process's adds IPC and pickle")
    print("both ways, and the primitives fall out of contention in exactly")
    print("that order. The grain is YOURS to choose: batch fine work into")
    print("coarse tasks (Chapter 84's rule at architecture scale) and the")
    print("expensive isolation becomes affordable; leave it fine and only the")
    print("cheapest boundary survives.")


if __name__ == "__main__":
    main()
