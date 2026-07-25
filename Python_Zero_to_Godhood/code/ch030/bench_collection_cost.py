"""Benchmark 30.1 - a collection's cost scales with the number of tracked
objects.

The collector's copy-and-subtract pass visits every tracked object in the
scanned generation. So the cost of a full collection is proportional to how many
tracked (container) objects are alive, not to how much garbage there is. This
measures gc.collect() over heaps of increasing size, and shows the linear scaling
that makes a large live heap expensive to scan (and why gc.freeze helps).

Coarse-grained timing done directly; provenance header reused from the harness.
"""

import gc
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402


def build_heap(n):
    # n tracked container objects, all live (each a small dict).
    return [{"i": i} for i in range(n)]


def best_collect(heap, repeat=5):
    times = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        gc.collect()
        times.append(time.perf_counter() - t0)
    return min(times)


def main():
    print("=== 30.1  full-collection cost vs live tracked-object count ===")
    print(provenance())
    print("method      : gc.collect() over a live heap, min of 5 runs")
    print()

    for n in (50_000, 200_000, 800_000):
        heap = build_heap(n)
        t = best_collect(heap)
        print(f"  {n:>8,} tracked objects: {t * 1e3:7.2f} ms")
        del heap
        gc.collect()

    print()
    print("Reading this. The collection time grows roughly linearly with the")
    print("number of live tracked objects, because copy-and-subtract visits every")
    print("one of them. Garbage is cheap to reclaim; LIVE objects are what a")
    print("collection pays for, since it must prove they are reachable. This is")
    print("why a process with a large long-lived heap benefits from gc.freeze()")
    print("(Chapter 3): freezing moves the permanent heap out of every future")
    print("scan, so the collector only pays for the young, churning generation.")


if __name__ == "__main__":
    main()
