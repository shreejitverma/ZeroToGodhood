"""Listing 254.1 - Python 3.4 (2014): the statistics module, correct summaries in the stdlib.

Computing an average is easy to write and easy to get subtly wrong: sum/len is
fine until the list is empty (ZeroDivisionError) or you meant the MEDIAN, or you
confused sample and population standard deviation. People either re-derived these
each time or pulled in numpy for a one-line summary. Python 3.4's PEP 450 added
the statistics module: mean, median, mode, and the standard-deviation family as
correct, well-defined functions - median averaging the middle two on even-length
data, stdev being the SAMPLE deviation (the usual default) with pstdev for the
population. It handles Fraction and Decimal exactly, not just float. Deep volumes
own no statistics mechanism; this is the release that made basic descriptive
statistics batteries-included and correct. Verified on current interpreters.
"""

import statistics
from fractions import Fraction


def main() -> None:
    data = [2, 4, 4, 4, 5, 5, 7, 9]

    print("--- the central-tendency trio: mean, median, mode ---")
    print(f"  data : {data}")
    print(f"  mean   : {statistics.mean(data)}   (the average, 40/8)")
    print(f"  median : {statistics.median(data)}   (middle value)")
    print(f"  mode   : {statistics.mode(data)}   (most common value)")
    print("  three DIFFERENT notions of 'typical', each a named function. mean")
    print("  is the average, median the middle, mode the most frequent - naming")
    print("  them prevents the classic 'I said average but meant median' bug")

    print("--- median averages the middle TWO on even-length data ---")
    even = [1, 2, 3, 4]
    print(f"  median({even}) : {statistics.median(even)}   (mean of 2 and 3)")
    print("  with an even count there is no single middle, so median returns the")
    print("  average of the two central values - the correct definition, which")
    print("  a naive data[len//2] gets wrong")

    print("--- the standard-deviation family: sample vs population ---")
    sample = [2, 4, 4, 4, 5, 5, 7, 9]
    print(f"  stdev  (sample)     : {statistics.stdev(sample):.4f}")
    print(f"  pstdev (population) : {statistics.pstdev(sample):.4f}")
    print(f"  variance (sample)   : {statistics.variance(sample):.4f}")
    print(f"  pvariance (pop.)    : {statistics.pvariance(sample):.4f}")
    print("  stdev/variance use the SAMPLE formula (divide by n-1), the right")
    print("  default when your data is a sample of a larger population. pstdev/")
    print("  pvariance use n for a full population. confusing the two is a")
    print("  common statistics error the separate names prevent")

    print("--- exact arithmetic: Fraction and Decimal, not just float ---")
    fracs = [Fraction(1, 3), Fraction(1, 3), Fraction(1, 3)]
    print(f"  mean of three 1/3 : {statistics.mean(fracs)}   (EXACT, not 0.333...)")
    print("  statistics.mean preserves the input type: given Fractions it")
    print("  returns an exact Fraction, given Decimals an exact Decimal - so")
    print("  money and rationals stay precise instead of drifting into float")

    print("--- empty input is an explicit error, not a silent crash ---")
    try:
        statistics.mean([])
    except statistics.StatisticsError as exc:
        print(f"  mean([]) -> StatisticsError: {exc}")
    print("  a hand-rolled sum(x)/len(x) raises a bare ZeroDivisionError on")
    print("  empty data; statistics raises a clear, domain-specific")
    print("  StatisticsError that says what actually went wrong")

    print("--- the constraint answered ---")
    print("  basic statistics were re-derived (and mis-derived) everywhere or")
    print("  borrowed from numpy for a one-liner. the statistics module (3.4)")
    print("  made mean/median/mode and the sample-vs-population deviation family")
    print("  correct, named, exact-arithmetic-aware, and batteries-included -")
    print("  the right definitions, in the standard library")


if __name__ == "__main__":
    main()
