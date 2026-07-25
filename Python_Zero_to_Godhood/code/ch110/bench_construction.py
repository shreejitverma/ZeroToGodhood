"""Benchmark 110.1 - a caching __new__ controls whether an object is created at all.

Constructing 1,000,000 objects that take only 8 distinct values, two ways: Fresh
always allocates a new object; Cached uses a __new__ that returns a shared instance
per value (the flyweight pattern). Fresh makes a million objects; Cached makes
eight. This measures the memory of each, showing that __new__'s control over
instance creation is a real tool, the same trick as CPython's small-integer cache.

Memory via tracemalloc. See _harness/bench.py.
"""

import sys
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 1_000_000
K = 8                      # distinct values


class Fresh:
    __slots__ = ("v",)

    def __init__(self, v):
        self.v = v


class Cached:
    __slots__ = ("v",)
    _cache = {}

    def __new__(cls, v):
        obj = cls._cache.get(v)
        if obj is None:
            obj = super().__new__(cls)
            obj.v = v
            cls._cache[v] = obj
        return obj

    def __init__(self, v):
        pass               # value already set in __new__


def main():
    print(f"=== 110.1  {N:,} constructions of {K} distinct values: fresh vs caching __new__ ===")
    print(provenance())
    print()

    mb = 1024 * 1024

    tracemalloc.start()
    fresh = [Fresh(i % K) for i in range(N)]
    m_fresh, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    tracemalloc.start()
    cached = [Cached(i % K) for i in range(N)]
    m_cached, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    n_fresh = len({id(o) for o in fresh})
    n_cached = len({id(o) for o in cached})

    print(f"  fresh  : {m_fresh / mb:6.1f} MB   {n_fresh:>9,} distinct objects")
    print(f"  cached : {m_cached / mb:6.1f} MB   {n_cached:>9,} distinct objects")
    print(f"  the caching __new__ uses ~{m_fresh / m_cached:.0f}x less memory")

    del fresh, cached

    print()
    print("Reading this. __new__ decides which object a construction returns, so it")
    print("can return a shared instance instead of a new one. Constructing a million")
    print("objects with only eight distinct values, the caching __new__ creates just")
    print("eight objects; the rest of the list is a million pointers to them. That is")
    print("the flyweight pattern, and it is exactly how CPython caches the small")
    print("integers (Chapter 19). __init__ cannot do this; it runs after the object")
    print("already exists. Use a caching __new__ for immutable value objects with")
    print("few distinct values; do not use it for mutable objects (shared state).")


if __name__ == "__main__":
    main()
