"""Benchmark 72.1 - [] inside any() defeats short-circuiting.

any() over a generator expression stops at the first True; any() over a LIST
comprehension builds the entire list first, then checks it. When the answer is
decided early (an item near the front), the genexp examines a handful of items
and the listcomp examines a million. This measures any() with and without the
brackets over a 1,000,000-element source whose match is near the front.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
data = range(1_000_000)

def with_genexp():
    return any(x == 5 for x in data)      # lazy: stops at x == 5

def with_listcomp():
    return any([x == 5 for x in data])    # eager: builds 1,000,000 bools first
"""


def main() -> None:
    results = [
        measure("any(genexp) short-circuits", "with_genexp()", SETUP, number=2000),
        measure("any([listcomp]) builds all", "with_listcomp()", SETUP, number=200),
    ]
    report("72.1  any() over 1,000,000 items, match near the front",
           results, baseline="any(genexp) short-circuits")

    print()
    print("Reading this. The generator expression lets any() stop at the first")
    print("item that decides the answer, here the sixth. The list comprehension")
    print("builds all 1,000,000 results before any() even runs, so it does a")
    print("million times more work for the same answer. The two forms differ by")
    print("only a pair of brackets, but the brackets force full materialization and")
    print("defeat short-circuiting. Never wrap a comprehension in [] inside any(),")
    print("all(), next(), min(), max(), or sum() when a genexp would short-circuit")
    print("or stream: drop the brackets.")


if __name__ == "__main__":
    main()
