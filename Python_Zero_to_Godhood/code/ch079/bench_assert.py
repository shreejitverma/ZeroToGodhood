"""Benchmark 79.1 - assert is not a cheaper check; it just vanishes under -O.

People sometimes justify assert-for-validation as "faster". It is not: when it
RUNS (normal mode), an assert costs about the same as the equivalent if-raise,
both evaluate the condition. Its only performance difference is that under -O it
is removed entirely (zero cost, and zero checking). So assert buys no speed when
you need the check, and no check when you want the speed. This measures assert vs
if-raise in normal mode.

Within a single interpreter (normal mode); min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
def with_assert(x):
    assert x >= 0
    return x

def with_if(x):
    if x < 0:
        raise ValueError
    return x
"""


def main() -> None:
    results = [
        measure("if-raise (always runs)", "with_if(5)", SETUP, number=2000000),
        measure("assert (normal mode)", "with_assert(5)", SETUP, number=2000000),
    ]
    report("79.1  a passing check: assert vs if-raise (normal mode)",
           results, baseline="if-raise (always runs)")

    print()
    print("Reading this. In normal mode the assert and the if-raise cost about the")
    print("same, both evaluate the condition. assert is not a faster way to check.")
    print("Its only difference is that -O strips it to nothing: zero cost AND zero")
    print("checking. So use assert only for internal invariants you are willing to")
    print("have disappear in an optimized run (a documented 'this cannot happen'),")
    print("and use an explicit if-raise for any validation or security check that")
    print("must run in every mode. Never guard real inputs with assert.")


if __name__ == "__main__":
    main()
