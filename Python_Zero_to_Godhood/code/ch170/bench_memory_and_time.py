"""Benchmark 170.1 - memory measured properly, and what it buys in time.

Two things this benchmark does that a timing-only chapter cannot.

  170.1a  measures ALLOCATION rather than size, with tracemalloc, which counts what was
          actually allocated including everything sys.getsizeof cannot see. Three
          representations of the same million numbers, then three representations of
          the same hundred thousand coordinate pairs.

  170.1b  measures the TIME consequence, because a smaller representation is not
          automatically faster: array.array and bytes have to build a Python object on
          every element read, so they win on memory and can lose on element-by-element
          access. The trade is real and this table is what it looks like.

The pairing is the chapter's argument. Memory work is not a separate discipline from
time work, it is the same discipline applied to a resource whose cost is invisible in a
profile.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import array
import sys
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, provenance, report  # noqa: E402

N = 1_000_000
BASE = 10 ** 18


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class SlottedPoint:
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x = x
        self.y = y


def allocated(build):
    """Peak bytes allocated while building, measured by tracemalloc."""
    tracemalloc.start()
    tracemalloc.reset_peak()
    holder = build()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del holder
    return peak


def main():
    print(f"=== 170.1a  {N:,} numbers, three representations, measured by tracemalloc ===")
    print(provenance())
    print()

    cases = (
        ("list of int objects", lambda: [BASE + i for i in range(N)]),
        ("tuple of int objects", lambda: tuple(BASE + i for i in range(N))),
        ("array.array('q')", lambda: array.array("q", range(BASE, BASE + N))),
    )
    baseline = None
    print(f"  {'representation':<24} {'peak bytes':>14} {'bytes/number':>13} {'vs array':>9}")
    print("  " + "-" * 64)
    results = []
    for label, build in cases:
        peak = allocated(build)
        results.append((label, peak))
        if label == "array.array('q')":
            baseline = peak
    for label, peak in results:
        print(f"  {label:<24} {peak:14,} {peak / N:13.1f} {peak / baseline:8.1f}x")

    print()
    objects = (
        ("100,000 Point instances", lambda: [Point(i, i) for i in range(100_000)]),
        ("100,000 SlottedPoint", lambda: [SlottedPoint(i, i) for i in range(100_000)]),
        ("100,000 (x, y) tuples", lambda: [(i, i) for i in range(100_000)]),
    )
    print("=== 170.1a (continued)  the same 100,000 pairs, three ways ===")
    print(f"  {'representation':<24} {'peak bytes':>14} {'bytes/pair':>12}")
    print("  " + "-" * 52)
    for label, build in objects:
        peak = allocated(build)
        print(f"  {label:<24} {peak:14,} {peak / 100_000:12.1f}")

    print()
    ACCESS_SETUP = f"""
import array
N = 100_000
BASE = {BASE}
as_list = [BASE + i for i in range(N)]
as_array = array.array('q', as_list)
as_bytes = as_array.tobytes()
view = memoryview(as_bytes).cast('q')
"""
    access = [
        measure("sum(list)", "sum(as_list)", ACCESS_SETUP, repeat=7, number=20),
        measure("sum(array.array)", "sum(as_array)", ACCESS_SETUP, repeat=7, number=20),
        measure("sum(memoryview cast)", "sum(view)", ACCESS_SETUP, repeat=7, number=20),
    ]
    report("170.1b  summing 100,000 numbers out of each representation",
           access, baseline="sum(list)")

    print()
    print("Reading this. The memory table says what everyone expects and by a larger")
    print("factor than most people guess: a list of a million integers costs several")
    print("times what the same integers cost packed, because each one is a separate")
    print("heap object with a header and each list slot is a pointer to it. The object")
    print("table says the same thing about attributes: __slots__ removes the")
    print("per-instance dict and comes out below both the ordinary instance and the")
    print("plain tuple, which is worth noting because the tuple is usually assumed to")
    print("be the cheapest option available.")
    print()
    print("The access table is the part that is usually left out. A packed")
    print("representation stores raw machine values, so every element READ has to build")
    print("a Python int, and that cost is paid per element on every pass. Packed data")
    print("wins decisively when it is handed to something that consumes buffers - a C")
    print("routine, NumPy, a socket, a hash (Chapters 79 and 84) - and can lose when it")
    print("is walked element by element in Python. Choose the representation from what")
    print("CONSUMES the data, not from the size table alone.")


if __name__ == "__main__":
    main()
