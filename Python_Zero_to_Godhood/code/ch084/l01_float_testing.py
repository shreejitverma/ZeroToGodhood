"""Listing 84.1 - comparing floats in tests: relative tolerance, not == or absolute.

== fails on computed floats (0.1 + 0.2 != 0.3, Chapter 35), so tests must compare
with a tolerance. But the tolerance KIND matters. assertAlmostEqual uses ABSOLUTE
tolerance (7 decimal places by default), which is wrong at both ends of the
magnitude scale: too STRICT for large numbers (adjacent floats differ by more than
1e-7, so it rejects values that are as close as floats get) and too LOOSE for small
numbers (it accepts values that are relatively far apart because both round to ~0).
math.isclose uses RELATIVE tolerance, which scales with the magnitude and is correct
across scales. Use math.isclose (or pytest.approx). This listing shows all three.
"""

import math
import unittest


def main() -> None:
    tc = unittest.TestCase()

    print("--- == fails on computed floats ---")
    print(f"  0.1 + 0.2 == 0.3          : {0.1 + 0.2 == 0.3}")
    print(f"  math.isclose(0.1+0.2, 0.3): {math.isclose(0.1 + 0.2, 0.3)}")

    print("--- absolute tolerance is too STRICT for large numbers ---")
    a, b = 1e16, 1e16 + 2      # 2 apart == adjacent representable floats at 1e16
    print(f"  1e16 and 1e16+2 (as close as floats get here)")
    try:
        tc.assertAlmostEqual(a, b)
        abs_ok = True
    except AssertionError:
        abs_ok = False
    print(f"  assertAlmostEqual passes  : {abs_ok}  (absolute: wrongly rejects)")
    print(f"  math.isclose passes       : {math.isclose(a, b)}  (relative: correct)")

    print("--- absolute tolerance is too LOOSE for small numbers ---")
    c, d = 1e-10, 2e-10        # 2x apart: relatively very different
    try:
        tc.assertAlmostEqual(c, d)
        abs_ok2 = True
    except AssertionError:
        abs_ok2 = False
    print(f"  1e-10 and 2e-10 (2x apart)")
    print(f"  assertAlmostEqual passes  : {abs_ok2}  (absolute: wrongly accepts)")
    print(f"  math.isclose passes       : {math.isclose(c, d)}  (relative: correct)")

    print("--- the rule ---")
    print(f"  compare computed floats with math.isclose (or pytest.approx): relative")
    print(f"  tolerance, correct at any magnitude; set abs_tol only for values near 0")


if __name__ == "__main__":
    main()
