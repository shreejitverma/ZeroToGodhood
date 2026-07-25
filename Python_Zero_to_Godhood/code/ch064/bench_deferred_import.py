"""Benchmark 64.1 - deferring an import into a function has a small per-call cost.

The fix for a circular import is to move the cross-import out of module level and
into the function that uses it. That import runs on EVERY call, but because the
module is already loaded, it is a sys.modules cache hit (Chapter 63), not a
re-execution. This measures a function that uses a module imported at top level
versus one that imports it in-function each call, so the cost of the deferral is
visible: a few dozen nanoseconds, the cache-hit lookup.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import math as _toplevel_math

def uses_toplevel():
    return _toplevel_math.sqrt(2.0)

def uses_deferred():
    import math                 # sys.modules cache hit every call
    return math.sqrt(2.0)
"""


def main() -> None:
    results = [
        measure("top-level import + use", "uses_toplevel()", SETUP, number=1000000),
        measure("deferred (in-function)", "uses_deferred()", SETUP, number=1000000),
    ]
    report("64.1  top-level vs in-function import on each call",
           results, baseline="top-level import + use")

    print()
    print("Reading this. The in-function import adds a sys.modules cache-hit lookup")
    print("on every call, a few dozen nanoseconds over a plain top-level reference.")
    print("For breaking a circular import this cost is negligible in ordinary code.")
    print("On a genuinely hot path, bind the import to a local once (import inside")
    print("the module but after both are loaded, or cache the reference), or better")
    print("restructure to remove the cycle. The deferral is a correctness fix with")
    print("a tiny, bounded price, not something to fear.")


if __name__ == "__main__":
    main()
