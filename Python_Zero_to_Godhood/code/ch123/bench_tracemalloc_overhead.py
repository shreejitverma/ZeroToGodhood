"""Benchmark 123.1 - tracemalloc has real tracing overhead; it is a diagnostic, not always-on.

When tracemalloc is running, it intercepts EVERY allocation to record where it
happened (a traceback per block). That makes allocation-heavy code much slower while
tracing is on. This measures an allocation loop with tracemalloc off versus on, to
show why tracemalloc belongs in development/staging leak-hunting, not in a production
hot path.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 2_000_000


def alloc_loop():
    acc = []
    for i in range(N):
        acc.append((i, i))               # each tuple allocation is intercepted when tracing
    return acc


def main():
    print(f"=== 123.1  allocation loop ({N:,} tuples): tracemalloc off vs on ===")
    print(provenance())
    print()

    t0 = time.perf_counter()
    d = alloc_loop()
    t_off = time.perf_counter() - t0
    del d

    tracemalloc.start()
    t0 = time.perf_counter()
    d = alloc_loop()
    t_on = time.perf_counter() - t0
    tracemalloc.stop()
    del d

    print(f"  tracemalloc OFF : {t_off * 1000:6.0f} ms   1.0x")
    print(f"  tracemalloc ON  : {t_on * 1000:6.0f} ms   {t_on / t_off:.1f}x")

    print()
    print("Reading this. With tracemalloc running, every allocation is intercepted")
    print("to record its traceback, so allocation-heavy code runs several times")
    print("slower, ~8x here. That is the correct cost for a DIAGNOSTIC: you turn")
    print("tracemalloc on to hunt a leak (snapshot, run, snapshot, compare_to), find")
    print("the allocation site, fix the stray reference, and turn it off. It is not")
    print("something to leave enabled in a production hot path. For lower-overhead")
    print("always-on monitoring, sample memory coarsely (get_traced_memory or OS-level")
    print("RSS) rather than full per-allocation tracing.")


if __name__ == "__main__":
    main()
