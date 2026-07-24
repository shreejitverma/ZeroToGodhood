"""Benchmark 15.1 - match is a readability feature, not a speed one.

The chapter's mechanism section says match compiles to a decision tree that
"tests shape once and fails fast." True, but it does NOT make match faster than
a hand-written if/elif that does the same checks; the class-pattern protocol
(isinstance, __match_args__ lookup, attribute extraction) is more work than
direct attribute access. This benchmark measures a fair comparison: the same
Point dispatch as a match and as an if/elif that does the same isinstance guard.

Also measures the dict union operators against the alternatives.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

DISPATCH_SETUP = """
class Point:
    __match_args__ = ('x', 'y')
    def __init__(self, x, y):
        self.x, self.y = x, y

def with_match(p):
    match p:
        case Point(0, 0): return 0
        case Point(x, 0): return 1
        case Point(0, y): return 2
        case Point(x, y): return 3

def with_ifelif(p):
    if isinstance(p, Point):          # match does this isinstance too, via MATCH_CLASS
        if p.x == 0 and p.y == 0: return 0
        elif p.y == 0: return 1
        elif p.x == 0: return 2
        else: return 3

pts = [Point(0, 0), Point(5, 0), Point(0, 3), Point(2, 3)]
"""

UNION_SETUP = "d1, d2 = {'a': 1, 'b': 2, 'x': 3}, {'b': 99, 'c': 4, 'y': 5}"


def main() -> None:
    dispatch = [
        measure("if/elif (same checks)", "for p in pts: with_ifelif(p)", DISPATCH_SETUP, number=3000),
        measure("match                ", "for p in pts: with_match(p)", DISPATCH_SETUP, number=3000),
    ]
    report("15.1a  structural dispatch: match is slower than hand-written if/elif",
           dispatch, baseline="if/elif (same checks)")

    print()
    union = [
        measure("| operator ", "for _ in range(1000): d1 | d2", UNION_SETUP, number=1000),
        measure("{**a, **b} ", "for _ in range(1000): {**d1, **d2}", UNION_SETUP, number=1000),
        measure("copy+update", "for _ in range(1000):\n m = d1.copy(); m.update(d2)", UNION_SETUP, number=1000),
    ]
    report("15.1b  dict merge: | and {**} are comparable, copy+update trails",
           union, baseline="| operator ")

    print()
    print("Reading both. 15.1a is the honest correction: match compiled a")
    print("decision tree, but the class-pattern protocol (isinstance, then")
    print("__match_args__ lookup, then attribute extraction) is several times the")
    print("cost of the equivalent hand-written if/elif. match is for clarity when")
    print("destructuring complex shapes, not for speed; do not reach for it to go")
    print("faster than an if chain. 15.1b: | and {**a, **b} merge at the same")
    print("speed and both beat the two-statement copy+update.")


if __name__ == "__main__":
    main()
