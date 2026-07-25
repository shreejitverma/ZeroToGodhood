"""Benchmark 34.1 - @cache turns exponential recursion into linear.

functools.cache (and lru_cache) memoize a function: a repeated call with the same
arguments returns the stored result. For naive recursive Fibonacci, this is not a
constant-factor speedup, it changes the ALGORITHMIC complexity, from O(2^n)
(recomputing the same subproblems exponentially many times) to O(n) (each fib(k)
computed once). This measures both, at a size small enough that the uncached
version still finishes.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import functools

def fib_uncached(n):
    return n if n < 2 else fib_uncached(n - 1) + fib_uncached(n - 2)

@functools.cache
def fib_cached(n):
    return n if n < 2 else fib_cached(n - 1) + fib_cached(n - 2)

fib_cached(30)   # warm the cache once
"""


def main() -> None:
    results = [
        measure("cached   fib(28)", "fib_cached(28)", SETUP, number=20000),
        measure("uncached fib(28)", "fib_uncached(28)", SETUP, number=20),
    ]
    report("34.1  fib(28): @cache vs naive recursion",
           results, baseline="cached   fib(28)")

    print()
    print("Reading this. The cached version, once warm, is a single dict lookup:")
    print("O(1) per call. The uncached version recomputes fib(29) and fib(28),")
    print("which each recompute their subproblems, all the way down, so fib(28)")
    print("makes over a million calls: O(2^n). @cache did not make the function a")
    print("bit faster; it changed its complexity class, from exponential to")
    print("linear (each fib(k) computed once, then cached). This is the difference")
    print("between a memoized dynamic-programming solution and the naive one, and")
    print("it is a one-line decorator. Use it for pure functions with a bounded,")
    print("repeated argument space; do not use it for functions with side effects")
    print("or unbounded distinct arguments (the cache grows without limit).")


if __name__ == "__main__":
    main()
