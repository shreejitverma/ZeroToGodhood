"""Benchmark 114.1 - cached_property computes once; property recomputes every read.

A property runs its getter on EVERY access (Chapter 32). functools.cached_property
runs the getter ONCE, stores the result in the instance __dict__, and, being a
NON-data descriptor, is thereafter shadowed by that stored value, so later reads are
plain attribute fetches. For an expensive getter accessed repeatedly, the difference
is dramatic. This measures repeated access to a getter that sums a 1,000-element list.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import functools
import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 1_000_000


class WithProperty:
    def __init__(self, data):
        self.data = data

    @property
    def total(self):
        return sum(self.data)            # recomputed on every read


class WithCached:
    def __init__(self, data):
        self.data = data

    @functools.cached_property
    def total(self):
        return sum(self.data)            # computed once, then stored


def main():
    print("=== 114.1  repeated read of an expensive getter: property vs cached_property ===")
    print(provenance())
    print()

    data = list(range(1000))
    p, c = WithProperty(data), WithCached(data)

    t_p = min(timeit.repeat(lambda: p.total, number=N, repeat=5)) / N
    t_c = min(timeit.repeat(lambda: c.total, number=N, repeat=5)) / N

    print(f"  property (recompute)   : {t_p * 1e9:8.0f} ns/read   1x")
    print(f"  cached_property (once) : {t_c * 1e9:8.0f} ns/read   {t_p / t_c:.0f}x faster")

    print()
    print("Reading this. property runs its getter on every access, so summing a")
    print("1,000-element list happens a million times. cached_property runs the")
    print("getter once, stores the result in the instance dict, and then (being a")
    print("non-data descriptor) is shadowed by that stored value, so subsequent reads")
    print("are plain attribute fetches, ~100x faster here. The size of the win scales")
    print("with the getter's cost. Use cached_property for an expensive, pure,")
    print("read-mostly computed attribute; use property when the value can change")
    print("(caching would go stale) or the getter is cheap. Note cached_property needs")
    print("an instance __dict__, so it does not work with __slots__ (Chapter 22).")


if __name__ == "__main__":
    main()
