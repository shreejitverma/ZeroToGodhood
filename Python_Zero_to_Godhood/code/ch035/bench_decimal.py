"""Benchmark 35.1 - what exactness costs: Decimal and Fraction vs float.

float arithmetic runs on the hardware FPU; Decimal and Fraction run in software
(Decimal is C-accelerated via _decimal, Fraction is pure Python over int). This
measures a fixed arithmetic workload (a sum of products) under each type, so the
cost of exactness is visible next to float's speed.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
from decimal import Decimal
from fractions import Fraction

fvals = [i * 0.5 for i in range(1, 51)]
dvals = [Decimal(i) / 2 for i in range(1, 51)]
qvals = [Fraction(i, 2) for i in range(1, 51)]

def work(vals):
    total = vals[0] - vals[0]      # a typed zero
    for v in vals:
        total += v * v
    return total
"""


def main() -> None:
    results = [
        measure("float    sum of squares", "work(fvals)", SETUP, number=20000),
        measure("Decimal  sum of squares", "work(dvals)", SETUP, number=20000),
        measure("Fraction sum of squares", "work(qvals)", SETUP, number=2000),
    ]
    report("35.1  the cost of exact arithmetic (50-term sum of squares)",
           results, baseline="float    sum of squares")

    print()
    print("Reading this. float runs on the hardware FPU and is the fastest by a")
    print("wide margin. Decimal is exact decimal arithmetic in C (_decimal), and")
    print("pays a large constant factor for that exactness. Fraction is exact")
    print("rational arithmetic in pure Python over big integers, and is the")
    print("slowest because every operation normalizes a numerator/denominator")
    print("pair. The rule: use float for speed where representation error is")
    print("acceptable (science, graphics, ML), Decimal where decimal exactness is")
    print("required (money, tax, billing), and Fraction where you need exact")
    print("rationals and no rounding at all (symbolic ratios, exact probabilities).")


if __name__ == "__main__":
    main()
