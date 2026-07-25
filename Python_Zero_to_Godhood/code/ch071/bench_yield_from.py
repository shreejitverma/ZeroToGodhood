"""Benchmark 71.1 - yield from short-circuits deep delegation chains.

For a single level of delegation, yield from and a manual re-yield loop cost about
the same. But delegation chains DEEP: a value from a generator nested D levels
down must travel up through every level. A manual re-yield chain suspends and
resumes at each of the D levels per value; yield from delegates more directly, so
its advantage grows with depth. This measures a depth-50 chain both ways.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
DEPTH = 50

def leaf(n):
    for i in range(n):
        yield i

def yf_chain(n, depth):
    if depth == 0:
        yield from leaf(n)
    else:
        yield from yf_chain(n, depth - 1)

def manual_chain(n, depth):
    if depth == 0:
        for x in leaf(n):
            yield x
    else:
        for x in manual_chain(n, depth - 1):
            yield x

def consume(g):
    t = 0
    for x in g:
        t += x
    return t
"""


def main() -> None:
    results = [
        measure("yield from (depth 50)", "consume(yf_chain(200, DEPTH))", SETUP, number=3000),
        measure("manual re-yield (depth 50)", "consume(manual_chain(200, DEPTH))", SETUP, number=3000),
    ]
    report("71.1  delegating through a depth-50 generator chain",
           results, baseline="yield from (depth 50)")

    print()
    print("Reading this. At one level, yield from and a manual re-yield loop cost")
    print("about the same. But through a deep chain, a value must pass every level,")
    print("and the manual loop suspends/resumes at each one, while yield from")
    print("delegates more directly, so yield from pulls ahead as depth grows. Speed")
    print("aside, yield from is the CORRECT delegation: it forwards send/throw/close")
    print("and captures the sub-generator's return value (Listing 71.1), which the")
    print("manual loop does not. Use yield from to delegate to a sub-generator or")
    print("coroutine; never hand-roll the re-yield loop.")


if __name__ == "__main__":
    main()
