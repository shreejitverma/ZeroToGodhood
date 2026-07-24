"""Benchmark 14.1 - the walrus saves a recomputation; positional-only does not
save call time.

Two claims. The walrus's value is de-duplication: computing a value once instead
of twice when you both test and use it. That is measurable. The common
performance justification for positional-only parameters, that they speed up
calls via index-based vectorcall copying, is NOT borne out for positional calls,
and this benchmark says so honestly.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

WALRUS_SETUP = "import re\npat = re.compile(r'(\\d+)-(\\d+)')\ns = '12-34'"

# compute the match twice (test, then redo to extract) vs once with a walrus.
COMPUTE_TWICE = "for _ in range(1000):\n if pat.match(s):\n  g = pat.match(s).group(1)"
WALRUS_ONCE = "for _ in range(1000):\n if (m := pat.match(s)):\n  g = m.group(1)"

POSONLY_SETUP = """
def pos_only(a, b, c, /):
    return a + b + c

def pos_or_kw(a, b, c):
    return a + b + c
"""


def main() -> None:
    walrus = [
        measure("compute twice", COMPUTE_TWICE, WALRUS_SETUP, number=1000),
        measure("walrus once  ", WALRUS_ONCE, WALRUS_SETUP, number=1000),
    ]
    report("14.1a  the walrus avoids a recomputation", walrus, baseline="compute twice")

    print()
    posonly = [
        measure("positional-or-keyword def", "for _ in range(1000): pos_or_kw(1, 2, 3)", POSONLY_SETUP, number=2000),
        measure("positional-only def      ", "for _ in range(1000): pos_only(1, 2, 3)", POSONLY_SETUP, number=2000),
    ]
    report("14.1b  positional-only does NOT speed up a positional call",
           posonly, baseline="positional-or-keyword def")

    print()
    print("Reading both. 14.1a is the real win: when a value is both tested and")
    print("used, the walrus computes it once instead of twice, and for a")
    print("non-trivial computation (a regex match) that is a clear speedup. 14.1b")
    print("is the correction: calling a positional-only function with positional")
    print("arguments is the same speed as calling a positional-or-keyword one,")
    print("because a positional call already takes the fast path in both. The")
    print("marker's value is API stability and **kwargs safety, not call speed;")
    print("the vectorcall performance story is real only relative to a KEYWORD")
    print("call, which you would not make to a hot function anyway.")


if __name__ == "__main__":
    main()
