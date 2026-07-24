"""Benchmark 6.1 - the try is free until it fires, and expensive when it does.

Two claims meet here. Section 6.3 says a try adds nothing on the success path
since 3.11 (the exception table replaced the block stack). Section 6.5 says
raising and catching is still expensive per exception, so EAFP loses in a loop
where the miss is common. This measures both, which is the whole EAFP-vs-LBYL
decision made quantitative.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = "d = {'timeout': 30}"

NO_TRY = "for _ in range(1000):\n v = d['timeout']"
TRY_HIT = "for _ in range(1000):\n try:\n  v = d['timeout']\n except KeyError:\n  v = 0"
EAFP_MISS = "for _ in range(1000):\n try:\n  v = d['nope']\n except KeyError:\n  v = 0"
LBYL_MISS = "for _ in range(1000):\n v = d['nope'] if 'nope' in d else 0"


def main() -> None:
    success = [
        measure("no try (baseline)     ", NO_TRY, SETUP, number=2000),
        measure("try, no exception     ", TRY_HIT, SETUP, number=2000),
    ]
    report("6.1a  success path: the try is essentially free",
           success, baseline="no try (baseline)     ")

    print()
    miss = [
        measure("LBYL, miss every time ", LBYL_MISS, SETUP, number=2000),
        measure("EAFP, miss every time ", EAFP_MISS, SETUP, number=2000),
    ]
    report("6.1b  every-miss path: raising is expensive",
           miss, baseline="LBYL, miss every time ")

    print()
    print("The decision rule, made quantitative. On the success path a try costs")
    print("within a few percent of no try at all: that is what zero-cost")
    print("exceptions means, and it is why EAFP is not just idiomatic but cheap")
    print("WHEN THE MISS IS RARE. But an actually-raised-and-caught exception")
    print("costs several times a bare lookup, so when the miss is the common")
    print("case, the cheap LBYL pre-check wins by a wide margin. Choose EAFP or")
    print("LBYL by the expected miss rate, not by style.")


if __name__ == "__main__":
    main()
