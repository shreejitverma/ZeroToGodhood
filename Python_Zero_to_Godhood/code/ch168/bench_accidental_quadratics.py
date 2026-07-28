"""Benchmark 168.1 - the doubling method on a clock, and the quadratics it finds.

Listing 168.1 measured exponents by counting, which is exact. This does the same thing
with a timer, which is what you have when the primitive operation is inside C and cannot
be counted from Python. The method is identical: run at n and at 4n, and take
log4(time(4n) / time(n)). Using a 4x span rather than 2x gives the ratio room to clear
the measurement noise, at the cost of averaging over a wider range.

The cases are the accidental quadratics that Python code actually contains, each paired
with the linear alternative that fixes it:

  s += x in a loop            against  "".join(parts)
  the same, with a second reference held to the string being grown
  list.insert(0, x)           against  deque.appendleft(x)
  x in list, inside a loop    against  x in set
  sum(list_of_lists, [])      against  chain.from_iterable

The second case is there because the first one does NOT come out quadratic, and the
reason is worth measuring rather than asserting: CPython resizes a string in place when
it holds the only reference, which hides the quadratic behaviour of += until something
takes a second reference. Then it reappears.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import math
import sys
import time
from collections import deque
from itertools import chain
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

SMALL = 4_000
LARGE = SMALL * 4
REPEAT = 7


def concat(n):
    s = ""
    for _ in range(n):
        s += "x"
    return len(s)


def concat_with_witness(n):
    s = ""
    witness = []
    for _ in range(n):
        s += "x"
        witness.append(s)          # a second reference: no in-place resize possible
    return len(s)


def join(n):
    parts = []
    for _ in range(n):
        parts.append("x")
    return len("".join(parts))


def insert_front(n):
    out = []
    for i in range(n):
        out.insert(0, i)
    return len(out)


def append_front(n):
    out = deque()
    for i in range(n):
        out.appendleft(i)
    return len(out)


def membership_list(n):
    haystack = list(range(n))
    return sum(1 for i in range(n) if i in haystack)


def membership_set(n):
    haystack = set(range(n))
    return sum(1 for i in range(n) if i in haystack)


def flatten_with_sum(n):
    groups = [[i] for i in range(n)]
    return len(sum(groups, []))


def flatten_with_chain(n):
    groups = [[i] for i in range(n)]
    return len(list(chain.from_iterable(groups)))


CASES = (
    ("s += x", concat),
    ("s += x, second ref held", concat_with_witness),
    ('"".join(parts)', join),
    ("list.insert(0, x)", insert_front),
    ("deque.appendleft(x)", append_front),
    ("x in list, in a loop", membership_list),
    ("x in set, in a loop", membership_set),
    ("sum(list_of_lists, [])", flatten_with_sum),
    ("chain.from_iterable", flatten_with_chain),
)

# membership and flatten at SMALL are already O(n^2); keep them smaller so the
# benchmark finishes, and scale them by the same factor of 4.
SCALE_DOWN = {"x in list, in a loop", "x in set, in a loop"}


def best(fn, n, repeat=REPEAT):
    lowest = float("inf")
    for _ in range(repeat):
        start = time.perf_counter()
        fn(n)
        lowest = min(lowest, time.perf_counter() - start)
    return lowest


def classify(value):
    if value < 0.3:
        return "constant"
    if value < 1.25:
        return "linear"
    if value < 1.7:
        return "n log n"
    if value < 2.3:
        return "QUADRATIC"
    return "worse"


def main():
    print(f"=== 168.1  empirical exponent from timing, log4(t(4n)/t(n)) ===")
    print(provenance())
    print(f"method      : min of {REPEAT} runs at each size; exponent from a 4x span")
    print()
    print(f"  {'operation':<26} {'n':>7} {'t(n) ms':>9} {'t(4n) ms':>10} {'exp':>6}  class")
    print("  " + "-" * 72)
    for label, fn in CASES:
        small = SMALL // 8 if label in SCALE_DOWN else SMALL
        large = small * 4
        t1 = best(fn, small)
        t4 = best(fn, large)
        exponent = math.log(t4 / t1, 4)
        print(f"  {label:<26} {small:7,} {t1 * 1e3:9.2f} {t4 * 1e3:10.2f}"
              f" {exponent:6.2f}  {classify(exponent)}")

    print()
    print("Reading this. The method transfers from counting to timing unchanged, and the")
    print("classification column is the whole output: everything marked QUADRATIC will")
    print("get four times worse for every doubling of your input, and no constant-factor")
    print("work will save it.")
    print()
    print("The two string rows are the interesting pair. Plain += comes out linear,")
    print("because CPython resizes the string in place when nothing else refers to it.")
    print("Hold one extra reference - append the intermediate to a list, pass it to a")
    print("logger, close over it - and the same loop becomes quadratic. That is not a")
    print("bug to fix in CPython; it is a reason not to depend on an optimisation whose")
    print("precondition is invisible at the call site. Build with ''.join, which is")
    print("linear unconditionally.")


if __name__ == "__main__":
    main()
