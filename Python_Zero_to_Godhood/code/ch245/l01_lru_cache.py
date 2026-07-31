"""Listing 245.1 - Python 3.2 (2011): functools.lru_cache, memoization as one line.

Caching a pure function's results - remembering that f(5) was 120 so you never
recompute it - is a classic optimization, and everyone re-wrote it: a module
dict, a membership check, a store. The hand-rolled cache was easy to get subtly
wrong (unhashable keys, unbounded growth, no thread safety) and cluttered the
function it wrapped. Python 3.2's functools.lru_cache made it a decorator: add
@lru_cache above a pure function and its results are cached automatically, with
a bounded Least-Recently-Used eviction policy so memory does not grow forever.
Deep K owns the cost model that says WHEN caching helps; this is the release
that made applying it a single line. Verified on current interpreters.
"""

from functools import lru_cache


# A counter of ACTUAL computations, to prove the cache prevents recomputation.
calls = {"fib": 0}


@lru_cache(maxsize=None)                          # unbounded cache
def fib(n):
    calls["fib"] += 1
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)


def main() -> None:
    print("--- @lru_cache turns exponential recursion into linear ---")
    result = fib(30)
    print(f"  fib(30) = {result}")
    print(f"  actual fib() bodies executed : {calls['fib']}  (once per distinct n)")
    print("  naive recursive fib(30) makes over 2.7 MILLION calls (each value")
    print("  recomputed exponentially). with @lru_cache each fib(n) runs ONCE")
    print("  and is reused, so 31 distinct computations cover the whole tree")

    print("--- the cache is observable via cache_info() ---")
    info = fib.cache_info()
    print(f"  fib.cache_info() : hits={info.hits}, misses={info.misses}, "
          f"currsize={info.currsize}")
    print("  misses are the real computations (one per distinct n); hits are")
    print("  the reuses. the decorator exposes the cache stats so you can SEE")
    print("  whether it is helping - measurement, not faith (Deep K)")

    print("--- a plain call is cached too, not just recursion ---")
    @lru_cache(maxsize=None)
    def slow_square(x):
        slow_square.computations += 1
        return x * x
    slow_square.computations = 0
    for _ in range(5):
        slow_square(7)                            # same arg five times
    print(f"  called slow_square(7) five times")
    print(f"  actual computations : {slow_square.computations}  (only the first)")
    print("  repeated calls with the same arguments return the stored result.")
    print("  the function runs once; the other four are cache hits")

    print("--- maxsize bounds memory: LRU eviction ---")
    @lru_cache(maxsize=2)                          # keep only 2 most-recent
    def ident(x):
        return x
    ident(1); ident(2); ident(3)                  # 3 distinct, cache holds 2
    before = ident.cache_info()
    print(f"  maxsize=2 after ident(1),(2),(3) : currsize={before.currsize}")
    ident(1)                                       # 1 was evicted -> a miss
    after = ident.cache_info()
    print(f"  ident(1) again -> misses rose to {after.misses} (1 was evicted)")
    print("  with maxsize=2 the cache holds only the 2 most-recently-used keys;")
    print("  the least-recently-used is evicted. that bound is what makes it")
    print("  safe on a hot path - memory cannot grow without limit (the L-R-U)")

    print("--- the requirement: arguments must be hashable, function pure ---")
    try:
        fib([1, 2])                               # a list is unhashable
    except TypeError as exc:
        print(f"  fib([1,2]) -> TypeError: {exc}")
    print("  the cache keys on the arguments, so they must be HASHABLE (Deep A)")
    print("  - a list fails. and the function must be PURE (same args -> same")
    print("  result, no side effects), or the cache returns stale answers")

    print("--- the constraint answered ---")
    print("  memoization was a hand-rolled dict-plus-guard, easy to get wrong")
    print("  and repeated everywhere. @lru_cache (3.2) made it one decorator")
    print("  with bounded LRU eviction and observable stats. Deep K tells you")
    print("  WHEN a cache helps; this release made SAYING so a single line")


if __name__ == "__main__":
    main()
