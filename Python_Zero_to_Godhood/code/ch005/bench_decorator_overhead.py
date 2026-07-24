"""Benchmark 5.1 - a "transparent" decorator is not free.

Section 5.4 says each decoration adds a Python-level call per invocation. This
sizes it: a bare function, the same function behind one pass-through wrapper
that forwards *args/**kwargs, and lru_cache as the counter-case (a decorator
that removes net work).

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import functools

def bare(x):
    return x + 1

def passthrough(f):
    @functools.wraps(f)
    def w(*args, **kwargs):
        return f(*args, **kwargs)
    return w

wrapped = passthrough(bare)

@functools.lru_cache(maxsize=None)
def cached_fib(n):
    return n if n < 2 else cached_fib(n - 1) + cached_fib(n - 2)

cached_fib(30)   # warm the cache before timing
"""


def main() -> None:
    results = [
        measure("bare call            ", "for _ in range(1000): bare(1)", SETUP, number=2000),
        measure("one pass-through     ", "for _ in range(1000): wrapped(1)", SETUP, number=2000),
        measure("lru_cache hit        ", "for _ in range(1000): cached_fib(30)", SETUP, number=2000),
    ]
    report("5.1  per-call cost of a decorator layer",
           results, baseline="bare call            ")
    print()
    print("Reading this. A *args/**kwargs pass-through wrapper costs several")
    print("times the bare call: it is a second Python call that packs the")
    print("arguments into a tuple and dict and unpacks them again. 'Transparent'")
    print("describes the semantics, not the cost. lru_cache is the opposite case:")
    print("its per-hit cost is above a bare call, but it replaces the entire")
    print("computation it caches, so on real work it is a net removal. The rule")
    print("is the same as every other chapter here: a decorator on a hot path is")
    print("a measurement, not a habit.")


if __name__ == "__main__":
    main()
