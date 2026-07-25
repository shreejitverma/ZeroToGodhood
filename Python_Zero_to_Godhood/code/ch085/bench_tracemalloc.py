"""Benchmark 85.1 - tracemalloc hooks every allocation, so it is heavy.

tracemalloc records the allocation site of EVERY allocation, so allocation-heavy
code runs much slower while it is enabled. This measures an allocation-heavy loop
with tracemalloc off and on, so the overhead is visible. Like a deterministic
profiler (Chapter 51), tracemalloc is a diagnose-then-disable tool: enable it to
find where memory goes, read the snapshot, then turn it off, never leave it on in
production.

Does its own timing (it toggles tracemalloc), guarded by __main__. See
_harness/bench.py.
"""

import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402


def alloc_heavy():
    data = []
    for i in range(10000):
        data.append([i] * 10)
    return len(data)


def best(reps=7):
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        alloc_heavy()
        times.append(time.perf_counter() - t0)
    return min(times)


def main():
    print("=== 85.1  allocation-heavy code: tracemalloc off vs on ===")
    print(provenance())
    print()

    off = best()
    tracemalloc.start()
    on = best()
    tracemalloc.stop()

    print(f"  tracemalloc OFF : {off * 1e6:8.0f} us")
    print(f"  tracemalloc ON  : {on * 1e6:8.0f} us")
    print(f"  overhead        : {on / off:8.1f}x")

    print()
    print("Reading this. With tracemalloc enabled, every allocation is recorded")
    print("with its traceback, so allocation-heavy code runs several times slower.")
    print("That is the price of knowing WHERE memory is allocated, invaluable when")
    print("chasing a leak or a fat resident set, but far too expensive to leave on")
    print("in production. Use tracemalloc like a profiler (Chapter 51): enable it,")
    print("reproduce the memory problem, read the top allocation sites (or diff two")
    print("snapshots to see what grew), fix it, and disable it. Do not ship with")
    print("tracemalloc running.")


if __name__ == "__main__":
    main()
