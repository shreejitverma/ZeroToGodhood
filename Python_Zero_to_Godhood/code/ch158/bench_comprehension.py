"""Benchmark 158.1 - what the inlined frame is worth, at the fixed cost and per element.

Both verification interpreters are post-PEP-709, so this cannot measure the 3.11-to-3.12
change directly. What it can measure is the thing PEP 709 removed, by comparing against
the construct that still has it: a generator expression, which cannot be inlined because
a generator must own a frame in order to be suspended.

Two effects, deliberately separated:

  FIXED cost   - a comprehension over an EMPTY iterable. No body runs, so what is left
                 is the setup: for the inlined comprehension, almost nothing; for the
                 generator, building a function object, a generator object, and a frame.
  PER-ELEMENT  - the same construct over 1,000 elements, where the generator additionally
                 pays a resume per element.

The explicit for-loop-with-append is included as the form that never had a hidden frame
to begin with, which is why the comprehension does not beat it by much.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

N = 1_000

# Every case is wrapped in a function of the same shape, so that the one Python call
# per measurement is common to all rows and cancels out of the ratios. Timing a bare
# expression against a function call would charge one row for a frame the others avoid.
SETUP = f"""
empty = []
xs = list(range({N}))


def comp_list(src):
    return [x for x in src]


def comp_set(src):
    return {{x for x in src}}


def comp_dict(src):
    return {{x: x for x in src}}


def gen_list(src):
    return list(x for x in src)


def loop_append(src):
    out = []
    for x in src:
        out.append(x)
    return out


def c_copy(src):
    return list(src)
"""


def main():
    fixed = [
        measure("list comprehension", "comp_list(empty)", SETUP, number=200_000),
        measure("set comprehension", "comp_set(empty)", SETUP, number=200_000),
        measure("dict comprehension", "comp_dict(empty)", SETUP, number=200_000),
        measure("list(genexpr)", "gen_list(empty)", SETUP, number=200_000),
        measure("for-loop + append", "loop_append(empty)", SETUP, number=200_000),
    ]
    report("158.1a  fixed cost: the same construct over an EMPTY iterable",
           fixed, baseline="list comprehension")

    print()
    bulk = [
        measure("list comprehension", "comp_list(xs)", SETUP, repeat=9, number=2_000),
        measure("list(genexpr)", "gen_list(xs)", SETUP, repeat=9, number=2_000),
        measure("for-loop + append", "loop_append(xs)", SETUP, repeat=9, number=2_000),
        measure("list(xs)  [C copy]", "c_copy(xs)", SETUP, repeat=9, number=2_000),
    ]
    report(f"158.1b  the same construct over {N:,} elements",
           bulk, baseline="list comprehension")

    print()
    print("Reading this. The fixed-cost table is where PEP 709 shows: an inlined")
    print("comprehension over an empty iterable costs about as much as the empty loop")
    print("that surrounds it, because there is no function object to build and no frame")
    print("to push. The generator expression still pays all of that, which is why its")
    print("fixed cost is several times higher - and why the advice 'use a genexpr, it is")
    print("lazy' is wrong for a small collection you are going to materialize anyway.")
    print("The bulk table adds the per-element resume: the generator has to suspend and")
    print("resume its frame once per element, and that, not the setup, is what dominates")
    print("at 1,000 elements. list(xs) is the floor: a C-level copy with no Python at all.")


if __name__ == "__main__":
    main()
