"""Benchmark 176.1 - the allocator scales; the collector stops the world.

The same allocation-heavy churn (build and discard a 200,000-tuple list, five
times per worker), in four shapes per build:

    4 workers sequential, gc enabled      the baseline
    4 workers on 4 threads, gc enabled    what a user gets by default
    4 workers sequential, gc disabled     the collector's serial overhead
    4 workers on 4 threads, gc disabled   what the ALLOCATOR alone can do

A methodology note that is itself a finding: this benchmark does NOT use the
harness's timeit-based `measure()`, because `timeit` silently DISABLES the
garbage collector around the timed statement. That default is right for
microbenchmarks and fatally wrong here - it would erase the very pauses this
chapter measures (an early draft did exactly that, and reported the collector
as free). Chapter 85's rule, know what your harness does to the machine,
applies to this book's own harness. Timing here is perf_counter around whole
runs, min/median/RSD over 5 runs, reported through the same house format.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import gc
import statistics
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import Result, provenance, table  # noqa: E402

N = 200_000
REPEAT = 5


def churn(n=N):
    for _ in range(5):
        data = [(i, i) for i in range(n)]
        del data


def sequential():
    for _ in range(4):
        churn()


def threaded():
    workers = [threading.Thread(target=churn) for _ in range(4)]
    for w in workers:
        w.start()
    for w in workers:
        w.join()


def timed(label, fn, *, collector_on):
    """min/median/RSD over REPEAT runs, with the collector state explicit."""
    runs = []
    for _ in range(REPEAT):
        if collector_on:
            gc.enable()
        else:
            gc.disable()
        try:
            t0 = time.perf_counter()
            fn()
            runs.append((time.perf_counter() - t0) * 1e9)
        finally:
            gc.enable()
    median = statistics.median(runs)
    rsd = (statistics.stdev(runs) / median * 100.0) if median else 0.0
    return Result(label, median, min(runs), rsd, REPEAT, 1)


def main():
    churn(1000)   # warm
    rows = [
        timed("sequential, gc on", sequential, collector_on=True),
        timed("4 threads, gc on", threaded, collector_on=True),
        timed("sequential, gc off", sequential, collector_on=False),
        timed("4 threads, gc off", threaded, collector_on=False),
    ]
    print("=== 176.1  allocation churn: the allocator against the collector ===")
    print(provenance())
    print(f"method      : perf_counter around whole runs, {REPEAT} runs per row;")
    print("              NOT timeit, which disables the collector (see docstring)")
    print()
    print(table(rows, baseline="sequential, gc on"))

    print()
    print("Reading this. On the GIL build the four rows tell one story: one")
    print("thread runs at a time, so neither threading nor the collector's")
    print("state moves the number much. On the free-threaded build the threaded")
    print("rows split: with the collector enabled, the young-generation")
    print("threshold (2,000 allocations) turns allocation-heavy parallel code")
    print("into a drumbeat of STOP-THE-WORLD pauses, each halting all four")
    print("threads; with it disabled, the per-thread heaps run independently")
    print("and scaling approaches the core count.")
    print()
    print("The engineering conclusion is not 'disable the GC'. It is that on")
    print("the free-threaded build a collection's cost is multiplied by the")
    print("threads it stops: raise the young-generation threshold for")
    print("allocation-heavy phases (gc.set_threshold), gc.freeze() long-lived")
    print("startup objects so they stop being rescanned, and treat collector")
    print("frequency as a parallel-scalability dial, not a memory dial only.")


if __name__ == "__main__":
    main()
