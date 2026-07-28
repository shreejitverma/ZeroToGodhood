"""Benchmark 159.1 - the interpreter's dispatch cost, and the floor it puts under a loop.

Times the five formulations from Listing 159.1 and then divides each row's time by the
number of bytecode instructions that row executes (its per-element slope, times n). If
the fetch-decode-dispatch model is right, that quotient - nanoseconds per instruction -
should come out roughly the same for every row that has per-element bytecode, because
they are all paying the same interpreter for the same unit of work. Where it does not,
the row is doing something the instruction count cannot see.

That quotient is the number this whole volume has been circling: the price of one trip
around the evaluation loop on this machine. Multiply it by a loop's per-element slope
and by n and you have the floor under that loop, before any of the work it actually
wants to do.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

N = 200_000

# Per-element bytecode slopes, measured by Listing 159.1 and identical on both
# verification interpreters. Hard-coding them here keeps the benchmark fast; run the
# listing to re-derive them.
SLOPE = {
    "explicit loop": 8,
    "sum([comprehension])": 6,
    "sum(genexpr)": 7,
    "sum(map(lambda))": 3,
    "closed form": 0,
}

SETUP = f"""
N = {N}


def explicit_loop(n):
    total = 0
    for i in range(n):
        total += i * i
    return total


def comprehension(n):
    return sum([i * i for i in range(n)])


def generator(n):
    return sum(i * i for i in range(n))


def mapped(n):
    return sum(map(lambda i: i * i, range(n)))


def closed_form(n):
    return (n - 1) * n * (2 * n - 1) // 6
"""


def main():
    results = [
        measure("explicit loop", "explicit_loop(N)", SETUP, repeat=7, number=5),
        measure("sum([comprehension])", "comprehension(N)", SETUP, repeat=7, number=5),
        measure("sum(genexpr)", "generator(N)", SETUP, repeat=7, number=5),
        measure("sum(map(lambda))", "mapped(N)", SETUP, repeat=7, number=5),
    ]
    report(f"159.1  sum of squares below {N:,}, four per-element formulations",
           results, baseline="explicit loop")

    # The closed form is five orders of magnitude faster, so five calls per batch is
    # below the timer's useful resolution. It gets its own batch size rather than a
    # row with a 60% relative standard deviation next to rows measured at 0.8%.
    closed = measure("closed form", "closed_form(N)", SETUP, repeat=15, number=100_000)
    print()
    print(f"  closed form           {closed.min_ns:>11.1f} ns"
          f"   ({results[0].min_ns / closed.min_ns:,.0f}x faster than the loop)")

    print()
    print("cost of one trip around the evaluation loop, derived per row:")
    print(f"  {'formulation':<22} {'instructions':>13} {'ns/instruction':>15}")
    for r in results:
        n_ins = SLOPE[r.label] * N
        if not n_ins:
            print(f"  {r.label:<22} {n_ins:>13,} {'n/a':>15}")
            continue
        print(f"  {r.label:<22} {n_ins:>13,} {r.min_ns / n_ins:>15.2f}")

    print()
    print("Reading this. The first three rows agree on roughly the same nanoseconds per")
    print("instruction, which is the model holding: they are different amounts of the")
    print("same work. The map row does not, and its disagreement is informative rather")
    print("than a failure - its 3 instructions per element are only the lambda's body,")
    print("and the C-level machinery that calls the lambda once per element is real work")
    print("the bytecode counter cannot see. The closed form has no per-element work at")
    print("all: it is not faster by a constant, it is faster by an exponent, and no")
    print("amount of interpreter engineering closes that gap. That is the ceiling: the")
    print("interpreter can make each trip cheaper, and only the algorithm, or leaving")
    print("the interpreter, can make the trips stop happening.")


if __name__ == "__main__":
    main()
