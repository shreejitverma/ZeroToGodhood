"""Benchmark 59.1 - casefold is as fast as lower, so use it for comparison.

A reason people give for using lower() instead of casefold() for comparison is
speed. There is none: casefold applies a slightly larger fold table but is
essentially the same cost as lower on typical text. So the choice between them is
purely about correctness (casefold matches caselessly; lower is for display), not
performance.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
s = "The Quick Brown Fox Jumps Over The Lazy Dog " * 20
"""


def main() -> None:
    results = [
        measure("str.lower()", "s.lower()", SETUP, number=100000),
        measure("str.casefold()", "s.casefold()", SETUP, number=100000),
    ]
    report("59.1  str.lower vs str.casefold on typical text",
           results, baseline="str.lower()")

    print()
    print("Reading this. casefold costs essentially the same as lower, so there is")
    print("no performance reason to prefer lower for comparison. Use casefold for")
    print("any caseless match, search, or dedup (it folds ß to ss, final sigma to")
    print("sigma, and more), and use lower only when you want lowercase for")
    print("DISPLAY. Combine casefold with NFC normalization (Chapter 58) for the")
    print("robust caseless-equality recipe.")


if __name__ == "__main__":
    main()
