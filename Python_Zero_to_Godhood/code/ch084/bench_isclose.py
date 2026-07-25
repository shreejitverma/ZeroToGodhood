"""Benchmark 84.1 - relative float comparison costs a little; correctness is free enough.

math.isclose does a bit more work than == (it computes a relative tolerance), but
the overhead is small and does not depend on the values. Since == is simply WRONG
for computed floats, the tiny cost of isclose is the price of a correct comparison,
paid per assertion in a test (not in a hot loop). This measures == vs math.isclose
on a pair of nearly-equal floats.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import math
a = 0.1 + 0.2
b = 0.3
"""


def main() -> None:
    results = [
        measure("== (wrong for floats)", "a == b", SETUP, number=2000000),
        measure("math.isclose (correct)", "math.isclose(a, b)", SETUP, number=2000000),
    ]
    report("84.1  float comparison: == vs math.isclose",
           results, baseline="== (wrong for floats)")

    print()
    print("Reading this. math.isclose costs a little more than == because it")
    print("computes a relative tolerance, but the overhead is small and fixed, and")
    print("== is simply the WRONG answer for computed floats (it reports unequal for")
    print("values that are equal to within rounding). In a test this comparison runs")
    print("per assertion, not in a hot loop, so the cost is irrelevant and the")
    print("correctness is essential. Compare computed floats with math.isclose (or")
    print("pytest.approx / numpy.isclose); reserve == for exact-integer or")
    print("bit-identical values.")


if __name__ == "__main__":
    main()
