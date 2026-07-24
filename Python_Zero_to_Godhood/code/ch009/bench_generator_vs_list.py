"""Benchmark 9.1 - generators trade memory for laziness, and the trade is not
free in either direction.

Section 9.5 says a generator over N items is O(1) memory versus O(N) for the
equivalent list, but that a list comprehension can be faster for small, fully-
materialized data. This measures both sides: the memory gap (dramatic and
deterministic, via tracemalloc) and the speed of building versus fully consuming
each form.

Within a single interpreter; min is the headline for the speed rows. See
_harness/bench.py.
"""

import sys
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report, provenance  # noqa: E402

N = 1_000_000


def peak_bytes(build):
    tracemalloc.start()
    obj = build()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del obj
    return peak


def main() -> None:
    print("=== 9.1  generator vs list ===")
    print(provenance())
    print()

    list_mem = peak_bytes(lambda: [i * i for i in range(N)])
    gen_mem = peak_bytes(lambda: (i * i for i in range(N)))
    print(f"memory for {N:,} squares (tracemalloc, deterministic):")
    print(f"  list comprehension : {list_mem / 1024 / 1024:8.1f} MB")
    print(f"  generator          : {gen_mem:8d} bytes  (O(1): one frame)")
    print(f"  ratio              : {list_mem / max(gen_mem, 1):,.0f}x")

    print()
    # Speed: building a list vs building+fully consuming a generator, at a size
    # small enough that the list fits comfortably.
    SETUP = "M = 10000"
    speed = [
        measure("list comprehension  ", "s = sum([i*i for i in range(M)])", SETUP, number=2000),
        measure("generator expression", "s = sum(i*i for i in range(M))", SETUP, number=2000),
    ]
    report("9.1b  build-and-consume speed, M = 10,000", speed,
           baseline="list comprehension  ")

    print()
    print("Reading both. The memory gap is enormous and one-directional: a")
    print("generator is a single frame no matter how many items it will yield,")
    print("so for large or streamed data it is the only affordable option. But")
    print("when the data is small and you consume all of it once, the list")
    print("comprehension is competitive or faster, because it does its work in a")
    print("tight C loop while the generator pays a Python-level resume per item.")
    print("Generators are for size and laziness, not for speed on small data.")


if __name__ == "__main__":
    main()
