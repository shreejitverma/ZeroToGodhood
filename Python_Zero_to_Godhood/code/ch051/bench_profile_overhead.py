"""Benchmark 51.1 - cProfile's per-call hook adds large overhead.

Running the same call-heavy workload with and without cProfile enabled. cProfile
hooks every function call and return, so for code that makes many calls the
instrumentation dominates: the profiled run is several times slower than the
plain run. This is WHY cProfile's absolute times are not the code's real speed,
and why you measure a hotspot with a benchmark AFTER cProfile has located it.

Does its own timing (it toggles the profiler), guarded by __main__. See
_harness/bench.py.
"""

import cProfile
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402


def leaf(n):
    return sum(i * i for i in range(n))


def work():
    total = 0
    for _ in range(20000):
        total += leaf(50)
    return total


def best(fn, repeat=7):
    return min(fn() for _ in range(repeat))


def main():
    print("=== 51.1  cProfile overhead on a call-heavy workload ===")
    print(provenance())
    print()

    def plain():
        t0 = time.perf_counter()
        work()
        return time.perf_counter() - t0

    def profiled():
        pr = cProfile.Profile()
        t0 = time.perf_counter()
        pr.enable()
        work()
        pr.disable()
        return time.perf_counter() - t0

    tp = best(plain)
    tf = best(profiled)
    print(f"  unprofiled : {tp * 1000:7.1f} ms")
    print(f"  profiled   : {tf * 1000:7.1f} ms")
    print(f"  overhead   : {tf / tp:7.1f}x")

    print()
    print("Reading this. cProfile hooks every call and return, so a workload that")
    print("makes many small calls runs several times slower under it. The profiled")
    print("time is therefore NOT the code's real speed, and cProfile over-weights")
    print("call-heavy functions relative to compute-heavy ones. Use cProfile to")
    print("RANK functions and find the hotspot; then measure that hotspot with a")
    print("focused benchmark (timeit / this harness) whose timing is not distorted")
    print("by the per-call hook. For low-overhead attribution, a statistical")
    print("profiler (sampling) or sys.monitoring (Chapter 22) is the alternative.")


if __name__ == "__main__":
    main()
