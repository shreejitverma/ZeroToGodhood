"""Listing 267.1 - Python 3.8 (2019): functools.cached_property, compute once, then it's an attribute.

A property (Chapter 227) recomputes every time you read it - correct for cheap or
changing values, wasteful for an expensive result that never changes for the
life of the object (a parsed document, a summary over immutable data). The old
fix was a hand-written 'compute, stash in self._cache, return the stash' dance in
every such property. Python 3.8's functools.cached_property does it for you: the
first access computes the value and STORES it in the instance __dict__ under the
same name, so every later access is a plain attribute read - the descriptor never
runs again. Deep C owns the descriptor protocol that makes this work; this is the
release that turned the compute-once-and-cache pattern into a decorator. Verified
on current interpreters.
"""

from functools import cached_property


class Dataset:
    def __init__(self, numbers):
        self.numbers = numbers
        self.compute_count = 0                    # counts how often the work runs

    @cached_property
    def summary(self):
        """Expensive: pretend this is a big reduction over immutable data."""
        self.compute_count += 1
        return {"n": len(self.numbers), "total": sum(self.numbers),
                "max": max(self.numbers)}


def main() -> None:
    print("--- first access computes; later accesses are cached ---")
    d = Dataset([3, 1, 4, 1, 5])
    print(f"  compute_count before any access : {d.compute_count}")
    print(f"  d.summary (1st access) : {d.summary}")
    print(f"  d.summary (2nd access) : {d.summary}")
    print(f"  d.summary (3rd access) : {d.summary}")
    print(f"  compute_count after three reads : {d.compute_count}   (ran ONCE)")
    print("  the body ran a single time; the 2nd and 3rd reads returned the")
    print("  stored value. an expensive result computed once, then free forever")

    print("--- the cache lives in the instance __dict__ under the same name ---")
    print(f"  'summary' in d.__dict__ before? depends, after access : "
          f"{'summary' in d.__dict__}")
    print(f"  d.__dict__['summary'] is the cached value : "
          f"{d.__dict__['summary'] == d.summary}")
    print("  cached_property is a descriptor that, on first access, writes the")
    print("  result straight into the instance dict under 'summary'. after that,")
    print("  normal attribute lookup finds it FIRST and the descriptor is never")
    print("  consulted again - that is why later reads cost nothing (Deep C)")

    print("--- the cache is PER INSTANCE, not shared across objects ---")
    d2 = Dataset([10, 20])
    print(f"  d.summary  : {d.summary}")
    print(f"  d2.summary : {d2.summary}")
    print(f"  d2 computed its own : compute_count(d)={d.compute_count}, "
          f"compute_count(d2)={d2.compute_count}")
    print("  each instance caches independently, because the value lives in that")
    print("  instance's own __dict__. two datasets, two separate cached summaries")

    print("--- to recompute, delete the cached attribute ---")
    del d.__dict__["summary"]                     # evict the cache
    print(f"  after deleting the cache, 'summary' in d.__dict__ : "
          f"{'summary' in d.__dict__}")
    result = d.summary                            # recomputes now
    print(f"  next access recomputed : compute_count(d)={d.compute_count}")
    print("  deleting the stored attribute makes the next access recompute -")
    print("  the escape hatch when the underlying data DID change and you want")
    print("  a fresh value. (plain @property never caches, so use that if the")
    print("  value changes often)")

    print("--- cached_property vs property vs lru_cache ---")
    print("  @property       : recomputes every read (cheap/changing values)")
    print("  @cached_property: computes once per instance, then a stored attr")
    print("  @lru_cache      : caches by ARGUMENTS across calls (Chapter 245)")
    print("  cached_property is the right tool for an expensive, stable, no-arg")
    print("  result derived from an instance's (effectively immutable) data")

    print("--- the constraint answered ---")
    print("  a property recomputes every access - wasteful for an expensive")
    print("  value that never changes. the manual fix (compute, stash in")
    print("  self._x, return it) was boilerplate in every such property.")
    print("  cached_property (3.8) makes it a decorator: first access computes")
    print("  and stores in the instance dict, every later access is a free read")


if __name__ == "__main__":
    main()
