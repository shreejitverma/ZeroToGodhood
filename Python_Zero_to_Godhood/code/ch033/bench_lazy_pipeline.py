"""Benchmark 33.1 - a lazy itertools pipeline is O(1) memory; the eager
list-building version is O(n).

The value of composing with itertools (and generators) is that the intermediate
stages never materialize. This measures the memory of a filter-map-sum over a
large range, done lazily versus by building intermediate lists. Memory is via
tracemalloc, which is deterministic.

Within a single interpreter. See _harness/bench.py.
"""

import itertools as it
import sys
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 1_000_000


def peak_bytes(fn):
    tracemalloc.start()
    result = fn()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak, result


def lazy():
    # count -> islice -> filter -> map -> sum, nothing materialized
    return sum(x * x for x in it.islice(it.count(), N) if x % 2 == 0)


def eager():
    # build a list, filter into a list, map into a list, then sum
    nums = list(range(N))
    evens = [x for x in nums if x % 2 == 0]
    squares = [x * x for x in evens]
    return sum(squares)


def main():
    print("=== 33.1  lazy itertools pipeline vs eager list-building ===")
    print(provenance())
    print()

    lazy_mem, lazy_result = peak_bytes(lazy)
    eager_mem, eager_result = peak_bytes(eager)

    print(f"  results equal: {lazy_result == eager_result}")
    print(f"  lazy pipeline peak memory : {lazy_mem:>12,} bytes")
    print(f"  eager list-building peak  : {eager_mem:>12,} bytes")
    print(f"  ratio                     : {eager_mem / max(lazy_mem, 1):>12,.0f}x")

    print()
    print("Reading this. Both compute the same sum, but the lazy pipeline holds")
    print("only one value at a time (O(1) memory), while the eager version")
    print("materializes the full range, the filtered list, and the squared list")
    print("(O(n) memory, three large lists). For a pipeline you consume once, the")
    print("lazy form is strictly better; itertools is how you build it without")
    print("hand-writing generators, and each stage runs in C.")


if __name__ == "__main__":
    main()
