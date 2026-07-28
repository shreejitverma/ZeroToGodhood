"""Benchmark 157.1 - does the per-element instruction count predict the time?

Listing 157.1 counts bytecode instructions per element; this measures wall time for the
same operations over a 10,000-element list. The point of running both is that the
instruction count is a MODEL and the timing is the check on it: if pushing a loop into C
removes 6 instructions per element, the time should fall by roughly the interpreter's
per-instruction cost times 6, and where it does not, the model is missing something (a C
callback per element, an allocation, a wider element type).

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

N = 10_000

SETUP = f"""
N = {N}
xs = list(range(N))
strs = [str(i) for i in xs]


def double(x):
    return x * 2


def loop_sum():
    total = 0
    for x in xs:
        total += x
    return total


def loop_double():
    out = []
    for x in xs:
        out.append(double(x))
    return out


def loop_concat():
    s = ""
    for _ in xs:
        s += "x"
    return s


def loop_max():
    best = xs[0]
    for x in xs:
        if x > best:
            best = x
    return best
"""


def ratio(results, slow, fast):
    a = next(r for r in results if r.label == slow)
    b = next(r for r in results if r.label == fast)
    return a.min_ns / b.min_ns


def main():
    # Rows are only comparable when they do the SAME per-element work, so each table
    # below is a fair group and the ratios quoted are within-pair.
    reductions = [
        measure("for-loop sum", "loop_sum()", SETUP, repeat=9, number=200),
        measure("sum(xs)", "sum(xs)", SETUP, repeat=9, number=200),
        measure("for-loop max", "loop_max()", SETUP, repeat=9, number=200),
        measure("max(xs)", "max(xs)", SETUP, repeat=9, number=200),
    ]
    report(f"157.1a  reductions over {N:,} ints", reductions, baseline="for-loop sum")
    print(f"within-pair : sum {ratio(reductions, 'for-loop sum', 'sum(xs)'):.2f}x   "
          f"max {ratio(reductions, 'for-loop max', 'max(xs)'):.2f}x")

    print()
    py_callable = [
        measure("for-loop + append", "loop_double()", SETUP, repeat=9, number=200),
        measure("list comprehension", "[double(x) for x in xs]", SETUP, repeat=9, number=200),
        measure("list(map(fn, xs))", "list(map(double, xs))", SETUP, repeat=9, number=200),
    ]
    report(f"157.1b  transform over {N:,} ints, PYTHON callable",
           py_callable, baseline="list comprehension")

    print()
    c_callable = [
        measure("list comprehension", "[str(x) for x in xs]", SETUP, repeat=9, number=200),
        measure("list(map(str, xs))", "list(map(str, xs))", SETUP, repeat=9, number=200),
    ]
    report(f"157.1c  transform over {N:,} ints, C callable",
           c_callable, baseline="list(map(str, xs))")

    print()
    builds = [
        measure("s += 'x' in a loop", "loop_concat()", SETUP, repeat=9, number=200),
        measure("''.join(genexpr)", "''.join('x' for _ in xs)", SETUP, repeat=9, number=200),
        measure("''.join(list)", "''.join(strs)", SETUP, repeat=9, number=200),
    ]
    report(f"157.1d  building a {N:,}-piece string", builds, baseline="''.join(list)")

    print()
    print("Reading this. Where a builtin expresses the whole loop and the per-element")
    print("work is C - sum, max, ''.join over a materialized list - the Python-level")
    print("loop disappears entirely and the win is large. Where the per-element work is")
    print("a PYTHON callable, map buys only the loop scaffolding, not the body, and the")
    print("gap between map and a comprehension is small: both still enter a Python frame")
    print("per element. That is the boundary the instruction counts predict, and it is")
    print("the boundary that decides whether 'use a builtin' is worth anything: the")
    print("builtin removes bytecode only for the part of the work it performs in C.")


if __name__ == "__main__":
    main()
