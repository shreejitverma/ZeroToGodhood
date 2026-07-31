"""Listing 258.1 - Python 3.5 (2015): math.isclose, comparing floats the right way.

The first surprise every programmer meets with floats: 0.1 + 0.2 != 0.3. Binary
floating point cannot represent most decimals exactly, so equality (==) on
computed floats is almost always wrong. The usual fix was a hand-picked epsilon:
abs(x - y) < 0.0001 - but a fixed epsilon is wrong at scale (too coarse near
zero, too tight for large numbers). Python 3.5's PEP 485 added math.isclose,
which uses a RELATIVE tolerance by default (scaled to the magnitudes compared)
plus an optional absolute tolerance for values near zero. It encodes the correct
way to ask 'are these two floats close enough?'. Deep volumes own the float
representation; this is the release that put the right comparison in the standard
library. Verified on current interpreters.
"""

import math


def main() -> None:
    print("--- the classic trap: computed floats are not exactly equal ---")
    x = 0.1 + 0.2
    print(f"  0.1 + 0.2      : {x!r}")
    print(f"  0.1 + 0.2 == 0.3 : {x == 0.3}   (False - the famous surprise)")
    print(f"  math.isclose(0.1 + 0.2, 0.3) : {math.isclose(x, 0.3)}   (True)")
    print("  0.1, 0.2, 0.3 have no exact binary form, so the sum lands a tiny")
    print("  bit off 0.3 and == fails. isclose asks the RIGHT question: are they")
    print("  within a sensible tolerance of each other?")

    print("--- relative tolerance scales with the magnitude compared ---")
    print(f"  isclose(1000000.0, 1000000.1)     : "
          f"{math.isclose(1000000.0, 1000000.1)}")
    print(f"  isclose(1.0, 1.1)                 : {math.isclose(1.0, 1.1)}")
    print("  the DEFAULT tolerance is relative (rel_tol=1e-9): a 0.1 difference")
    print("  is negligible next to a million but huge next to 1. a fixed epsilon")
    print("  cannot do both; a relative tolerance is correct at every scale")

    print("--- tuning rel_tol: how many significant figures must agree ---")
    print(f"  isclose(1.0, 1.001, rel_tol=1e-2) : "
          f"{math.isclose(1.0, 1.001, rel_tol=1e-2)}   (1% - close enough)")
    print(f"  isclose(1.0, 1.001, rel_tol=1e-4) : "
          f"{math.isclose(1.0, 1.001, rel_tol=1e-4)}   (0.01% - too far)")
    print("  rel_tol is the maximum allowed difference as a FRACTION of the")
    print("  larger magnitude. raise it to be lenient, lower it to demand more")
    print("  agreeing significant figures")

    print("--- abs_tol: the fix for comparisons near zero ---")
    tiny = 1e-10
    print(f"  isclose(tiny, 0.0)                : {math.isclose(tiny, 0.0)}")
    print(f"  isclose(tiny, 0.0, abs_tol=1e-9)  : "
          f"{math.isclose(tiny, 0.0, abs_tol=1e-9)}")
    print("  relative tolerance breaks down at zero (any tolerance times 0 is 0),")
    print("  so isclose(x, 0.0) is almost always False. for near-zero values you")
    print("  supply an ABSOLUTE tolerance - the one case relative cannot cover")

    print("--- why a hand-rolled epsilon was the wrong habit ---")
    def naive_close(a, b, eps=1e-4):
        return abs(a - b) < eps
    big, big2 = 1e16, 1e16 + 2.0                 # agree to ~16 figures; differ by 2
    print(f"  naive_close(1e16, 1e16 + 2) with eps=1e-4 : {naive_close(big, big2)}")
    print(f"  isclose(1e16, 1e16 + 2)                   : {math.isclose(big, big2)}")
    print("  a fixed 1e-4 epsilon calls 1e16 and 1e16+2 FAR apart (abs diff 2),")
    print("  though they agree to ~16 significant figures. isclose's relative")
    print("  tolerance treats them as close, which is what you almost always mean")

    print("--- the constraint answered ---")
    print("  == on computed floats is a bug because binary float is inexact, and")
    print("  a hand-picked epsilon is wrong across scales. math.isclose (3.5)")
    print("  encodes the correct comparison: relative tolerance by default,")
    print("  absolute tolerance for near-zero. 'are these floats close enough?'")
    print("  became a standard function instead of an ad-hoc guess")


if __name__ == "__main__":
    main()
