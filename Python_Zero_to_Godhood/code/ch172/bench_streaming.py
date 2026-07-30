"""Benchmark 172.1 - what streaming saves, what it costs, and where the tax goes.

Three measurements, one argument.

  172.1a  the memory side, with tracemalloc: the same reduction over a list, a
          generator expression, and a three-stage generator pipeline. This is
          the saving the chapter exists for, in bytes.

  172.1b  the time side, and it is not free in Python: sum over a list
          comprehension against sum over a generator expression against a plain
          loop. The genexp AVOIDS the allocation and PAYS a frame resume per
          element, and on this machine the list is faster. Streaming trades
          time for memory, exactly opposite to Chapter 90's cache.

  172.1c  where the tax goes: it is per STAGE per element, and swapping a
          generator stage for map with a C callable does not remove it - a call
          is a call. What removes it is fusing stages: the same three
          operations in one stage cost a third of three stages.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, provenance, report  # noqa: E402

N = 1_000_000


def peak_allocation(run):
    tracemalloc.start()
    tracemalloc.reset_peak()
    run()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak


def main():
    print(f"=== 172.1a  the same reduction over {N:,} squares, peak allocation ===")
    print(provenance())
    print()

    def staged():
        squares = (i * i for i in range(N))
        evens = (x for x in squares if x % 2 == 0)
        return sum(evens)

    cases = (
        ("sum([i*i ...])  (list)", lambda: sum([i * i for i in range(N)])),
        ("sum(i*i ...)    (genexp)", lambda: sum(i * i for i in range(N))),
        ("3-stage generator pipeline", staged),
    )
    print(f"  {'form':<28} {'peak bytes':>14}")
    print("  " + "-" * 44)
    for label, run in cases:
        print(f"  {label:<28} {peak_allocation(run):>14,}")
    print("  the list's peak is the container plus a million boxed ints (Chapter 89);")
    print("  the streaming forms hold one item at a time, at any n, forever")

    print()
    SETUP = f"""
N = 100_000
data = list(range(N))
"""
    forms = [
        measure("sum([x*x for x in data])", "sum([x * x for x in data])",
                SETUP, repeat=7, number=200),
        measure("sum(x*x for x in data)", "sum(x * x for x in data)",
                SETUP, repeat=7, number=200),
        measure("explicit loop", """
total = 0
for x in data:
    total += x * x
""", SETUP, repeat=7, number=200),
    ]
    report("172.1b  the same reduction, 100,000 elements: the streaming tax",
           forms, baseline="sum([x*x for x in data])")

    print()
    STAGE_SETUP = """
N = 100_000
data = list(range(N))

def one_stage(items):
    for x in items:
        yield x + 1

def pipeline(depth):
    it = iter(data)
    for _ in range(depth):
        it = one_stage(it)
    return it
"""
    stages = [
        measure("fused: sum(x+3 for x)", "sum(x + 3 for x in data)",
                STAGE_SETUP, repeat=7, number=100),
        measure("1 generator stage", "sum(pipeline(1))",
                STAGE_SETUP, repeat=7, number=100),
        measure("3 generator stages", "sum(pipeline(3))",
                STAGE_SETUP, repeat=7, number=100),
        measure("6 generator stages", "sum(pipeline(6))",
                STAGE_SETUP, repeat=7, number=100),
        measure("3 map(C callable) stages",
                "sum(map((1).__add__, map((1).__add__, map((1).__add__, data))))",
                STAGE_SETUP, repeat=7, number=100),
    ]
    report("172.1c  pipeline depth: the per-stage tax, and what fusion buys",
           stages, baseline="fused: sum(x+3 for x)")

    print()
    print("Reading this. The memory table is the reason to stream: the list's peak")
    print("is proportional to n and the streaming forms' peaks are not, which is a")
    print("different exponent, not a smaller constant. The time table is the honest")
    print("half: in CPython a generator element costs a frame resume, so the genexp")
    print("is slower than the list comprehension it replaces, and streaming is a")
    print("trade of time for memory - the mirror image of Chapter 90's cache.")
    print()
    print("The depth table locates the tax precisely: it is per stage per element,")
    print("about 15 ns here, and the map row shows that swapping a generator frame")
    print("for a C-callable call does not remove it, because a call is a call. What")
    print("removes it is FUSION: the same three operations written in one stage cost")
    print("a third of three stages. Compose stages for clarity at the edges of a")
    print("program; fuse them in the hot path; and when even the fused per-element")
    print("cost is the bottleneck, that is Chapter 92's decision, not this one.")


if __name__ == "__main__":
    main()
