"""Benchmark 121.1 - disabling gc while building a large structure is much faster.

The cyclic collector runs periodically, triggered by allocation counts, and each
full (oldest-generation) collection SCANS all surviving tracked objects. While you
build a large, long-lived structure, that scan re-examines the ever-growing set of
objects again and again, O(live) work repeated many times, even though none of them
is garbage yet. Disabling gc during the bulk build skips those scans. This measures
building 2,000,000 dicts with gc on versus off.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import gc
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 2_000_000


def build():
    data = []
    for i in range(N):
        data.append({"i": i, "pair": (i, i)})   # tracked containers, all long-lived
    return data


def main():
    print(f"=== 121.1  building {N:,} dicts: gc enabled vs disabled ===")
    print(provenance())
    print()

    gc.enable()
    gc.collect()
    t0 = time.perf_counter()
    d1 = build()
    t_on = time.perf_counter() - t0
    del d1
    gc.collect()

    gc.disable()
    t0 = time.perf_counter()
    d2 = build()
    t_off = time.perf_counter() - t0
    gc.enable()
    del d2

    print(f"  gc enabled  : {t_on * 1000:6.0f} ms   {t_on / t_off:.1f}x")
    print(f"  gc disabled : {t_off * 1000:6.0f} ms   1.0x")

    print()
    print("Reading this. As the structure grows, the cyclic collector keeps firing")
    print("(allocation-count triggered) and each full collection rescans all the")
    print("surviving objects, none of which is garbage, so the work is wasted and")
    print("repeated, making the build several times slower. Disabling gc during a")
    print("known bulk build of long-lived data skips those scans. Re-enable it")
    print("afterward. This is a targeted optimization (famously used at scale for")
    print("load-time structure building), NOT a blanket 'disable gc': with it off,")
    print("any cycles you create leak (Chapter 31), so scope the disable tightly and")
    print("keep it on for normal operation.")


if __name__ == "__main__":
    main()
