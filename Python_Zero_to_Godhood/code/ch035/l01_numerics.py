"""Listing 35.1 - three number types, three contracts.

float   : IEEE 754 double, fast, binary, and NOT exact for decimal fractions.
Decimal : exact decimal arithmetic (you choose the precision and rounding).
Fraction: exact rational arithmetic (numerator/denominator, no rounding at all).

The point of the chapter: the "just use float" folklore is fine until money,
tax, or repeated summation is involved, at which point the representation error
is a correctness bug, not a rounding cosmetic. This listing shows the contract
each type offers; the benchmark shows what the exactness costs.
"""

from decimal import Decimal, getcontext
from fractions import Fraction


def main() -> None:
    print("--- float: binary IEEE 754, not exact for decimal fractions ---")
    s = 0.1 + 0.2
    print(f"  0.1 + 0.2            : {s!r}")
    print(f"  0.1 + 0.2 == 0.3    : {s == 0.3}")

    print("--- Decimal: exact decimal arithmetic ---")
    d = Decimal("0.1") + Decimal("0.2")
    print(f"  D('0.1')+D('0.2')   : {d}")
    print(f"  == D('0.3')         : {d == Decimal('0.3')}")
    getcontext().prec = 6
    print(f"  1/7 at prec=6       : {Decimal(1) / Decimal(7)}")

    print("--- Fraction: exact rational, no rounding at all ---")
    f = Fraction(1, 10) + Fraction(2, 10)
    print(f"  F(1,10)+F(2,10)     : {f}")
    print(f"  == F(3,10)          : {f == Fraction(3, 10)}")
    print(f"  (1/3)*3 exactly     : {Fraction(1, 3) * 3}")

    print("--- float summation: naive fold vs sum() vs math.fsum ---")
    import math

    def naive_fold(vals):
        t = 0.0
        for v in vals:
            t += v            # the loop everyone writes; no compensation
        return t

    # wide dynamic range: the exact answer is 1e-16 (via Fraction below)
    xs = [1.0, 1e-16, 1e16, -1e16, -1.0]
    exact = float(sum(Fraction(v) for v in xs))
    print(f"  values              : {xs}")
    print(f"  exact answer        : {exact!r}")
    print(f"  naive t += v fold   : {naive_fold(xs)!r}")
    print(f"  builtin sum()       : {sum(xs)!r}")
    print(f"  math.fsum()         : {math.fsum(xs)!r}")


if __name__ == "__main__":
    main()
