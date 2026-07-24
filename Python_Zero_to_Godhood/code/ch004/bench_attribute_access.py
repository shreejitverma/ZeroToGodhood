"""Benchmark 4.1 - the real cost of the three ways to hold an attribute.

Section 4.3 says instance attributes are cheap (they live in the instance dict
and skip the MRO walk) while properties pay for a descriptor call. This measures
all three common storage kinds, and corrects a widespread belief about
__slots__ along the way.

Two measurements: access speed (this file's benchmark) and memory footprint
(printed separately, via tracemalloc, which is deterministic).

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
class Plain:
    def __init__(self): self.x = 1
class Slotted:
    __slots__ = ('x',)
    def __init__(self): self.x = 1
class Propertied:
    def __init__(self): self._x = 1
    @property
    def x(self): return self._x
p = Plain(); s = Slotted(); q = Propertied()
"""


class Plain:
    def __init__(self):
        self.x = 1


class Slotted:
    __slots__ = ("x",)

    def __init__(self):
        self.x = 1


def mem_per_instance(cls, n=100_000):
    tracemalloc.start()
    objs = [cls() for _ in range(n)]
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del objs
    return peak / n


def main() -> None:
    results = [
        measure("instance dict (p.x)", "for _ in range(1000): p.x", SETUP, number=2000),
        measure("__slots__     (s.x)", "for _ in range(1000): s.x", SETUP, number=2000),
        measure("property      (q.x)", "for _ in range(1000): q.x", SETUP, number=2000),
    ]
    report("4.1  attribute-access cost, 1000 reads per loop",
           results, baseline="instance dict (p.x)")

    print()
    print("memory footprint (tracemalloc, deterministic):")
    print(f"  instance dict : {mem_per_instance(Plain):.0f} bytes/instance")
    print(f"  __slots__     : {mem_per_instance(Slotted):.0f} bytes/instance")

    print()
    print("The correction. __slots__ is barely faster than a plain instance dict")
    print("for ACCESS, because the specializing interpreter turns both into an")
    print("inline-cached direct read (LOAD_ATTR_INSTANCE_VALUE vs LOAD_ATTR_SLOT,")
    print("Chapter 17). Its real payoff is MEMORY: no per-instance __dict__. The")
    print("property is the one that costs, roughly 2x, because every read calls a")
    print("Python function that cannot be specialized to a direct load.")


if __name__ == "__main__":
    main()
