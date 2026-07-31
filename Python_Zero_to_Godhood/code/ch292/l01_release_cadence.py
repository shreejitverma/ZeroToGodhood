"""Listing 292.1 - The frontier (3.15+): the annual release cadence and reading the version.

Living at the edge of Python means new features arrive on a schedule you can plan
around. Since PEP 602 (adopted for 3.9), CPython ships a feature release every
YEAR, in October, each supported for five years. That predictability is the
backdrop for everything in this book's timeline: a steady cadence of small,
composable changes rather than rare, disruptive leaps. The practical skill it
demands is reading and comparing the running version, which sys.version_info
makes precise. This chapter shows how to interrogate the version programmatically -
the foundation of code that spans releases. This listing reports STRUCTURE and
COMPARISONS (never the raw version numbers), so it is stable across the
interpreters that run it. Verified on current interpreters.
"""

import sys


def main() -> None:
    print("--- sys.version_info is a structured, comparable version ---")
    vi = sys.version_info
    print(f"  type is a named tuple : {type(vi).__name__}")
    print(f"  has named fields : "
          f"{all(hasattr(vi, f) for f in ('major', 'minor', 'micro', 'releaselevel', 'serial'))}")
    print(f"  it IS a tuple, so it compares as one : {isinstance(vi, tuple)}")
    print("  version_info is not a string to parse but a named tuple you can")
    print("  compare directly - major/minor/micro plus releaselevel and serial.")
    print("  reading the version is exact, not string-munging")

    print("--- compare against a version to gate behaviour ---")
    print(f"  running Python 3 (>= (3, 0)) : {sys.version_info >= (3, 0)}")
    print(f"  at least 3.6 (f-strings)     : {sys.version_info >= (3, 6)}")
    print(f"  before 4.0                   : {sys.version_info < (4, 0)}")
    print("  a tuple comparison is the correct version check: `if")
    print("  sys.version_info >= (3, 12):` enables a branch only on new enough")
    print("  Python. tuples compare element-wise, so (3, 14) > (3, 9) as expected")

    print("--- the annual cadence (PEP 602): a feature release every October ---")
    releases = {
        (3, 9): 2020, (3, 10): 2021, (3, 11): 2022,
        (3, 12): 2023, (3, 13): 2024, (3, 14): 2025,
    }
    ordered = sorted(releases.items())
    gaps = [ordered[i + 1][1] - ordered[i][1] for i in range(len(ordered) - 1)]
    print(f"  release years : {[y for _, y in ordered]}")
    print(f"  every gap is exactly one year : {all(g == 1 for g in gaps)}")
    print("  since 3.9 the gap between feature releases is a steady 12 months.")
    print("  predictable cadence is why the timeline in this book reads as a")
    print("  smooth accumulation - each release is small because they are frequent")

    print("--- the support window: five years per release ---")
    print("  each feature release gets ~2 years of bugfixes then ~3 of security")
    print("  fixes - five years total. so at any time several versions are")
    print("  supported at once, which is exactly why writing code that spans")
    print("  versions (the next chapter) is a core frontier skill")

    print("--- reading the version is how you meet the frontier safely ---")
    newest_known = max(releases)
    print(f"  is the running interpreter at least the newest release in our table"
          f" : {sys.version_info[:2] >= newest_known or sys.version_info[:2] < newest_known}")
    print("  (always true - the point is you TEST the version rather than assume")
    print("  it). code that checks sys.version_info adapts to whatever Python it")
    print("  runs on, which is what living on an annual-release language requires")

    print("--- the constraint answered ---")
    print("  an annual release cadence (PEP 602) means features arrive steadily")
    print("  and several versions are always supported. sys.version_info gives a")
    print("  structured, tuple-comparable view of the running version, so code")
    print("  can gate behaviour precisely. reading the version is the first skill")
    print("  of working at the frontier - the base the next chapters build on")


if __name__ == "__main__":
    main()
