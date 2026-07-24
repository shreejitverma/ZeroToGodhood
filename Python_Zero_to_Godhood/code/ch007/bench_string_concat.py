"""Benchmark 7.1 - the "str += is O(n squared)" folklore is right for the wrong
reason.

Every guide warns that building a string with += in a loop is quadratic because
each += builds a new immutable string. In modern CPython that is only true when
the string being extended has another reference. When it does not (the common
`s += x` accumulation), CPython resizes the string's buffer IN PLACE, making the
loop O(n), only a small constant slower than "".join.

This measures both: the unaliased case (optimization fires, O(n)) and an aliased
case (optimization cannot fire, true O(n squared)). We measure two sizes so the
asymptotic behavior is visible, not just a single ratio.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

# Unaliased: s has refcount 1, so += resizes in place -> O(n).
UNALIASED = """
s = ""
for _ in range(N):
    s += "x"
"""

# join: the recommended idiom, O(n), no reliance on the refcount optimization.
JOIN = 'r = "".join("x" for _ in range(N))'

# Aliased: a second reference each iteration defeats the in-place resize -> O(n squared).
ALIASED = """
s = ""
for _ in range(N):
    alias = s
    s = s + "x"
"""


def run(n: int):
    setup = f"N = {n}"
    return [
        measure(f"unaliased += (n={n})", UNALIASED, setup, number=200),
        measure(f"join         (n={n})", JOIN, setup, number=200),
        measure(f"aliased  s=s+x (n={n})", ALIASED, setup, number=200),
    ]


def main() -> None:
    small = run(10_000)
    report("7.1a  n = 10,000", small, baseline=f"join         (n={10_000})")
    print()
    large = run(40_000)
    report("7.1b  n = 40,000 (4x the work)", large, baseline=f"join         (n={40_000})")

    print()
    print("Reading the two sizes. From n=10k to n=40k the work quadruples. If a")
    print("case is O(n) its time roughly quadruples too; if O(n squared), it")
    print("grows ~16x. The unaliased += and join both scale linearly and stay")
    print("close (+= is a small constant slower). The aliased case grows far")
    print("faster: that is the real O(n squared), and it appears only because the")
    print("extra reference forbids the in-place resize. The lesson: use join not")
    print("because += is always quadratic (it usually is not), but because join")
    print("does not depend on a fragile refcount condition to stay linear.")


if __name__ == "__main__":
    main()
