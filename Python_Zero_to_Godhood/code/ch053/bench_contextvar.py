"""Benchmark 53.1 - a ContextVar is not slower than a plain lookup.

A worry about ContextVar is that its per-context machinery makes access slow.
It does not: ContextVar.get() and .set() are implemented in C over an efficient
immutable-mapping context, and get() is about as fast as a dict lookup. So the
correctness of per-context state (Listing 53.1) comes at essentially no cost,
there is no speed reason to reach for a fragile global instead.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import contextvars
cv = contextvars.ContextVar("cv")
cv.set(42)
g = {"v": 42}
"""


def main() -> None:
    results = [
        measure("dict global lookup", "g['v']", SETUP, number=200000),
        measure("ContextVar.get()", "cv.get()", SETUP, number=200000),
        measure("ContextVar.set()", "cv.set(7)", SETUP, number=200000),
    ]
    report("53.1  ContextVar access vs a plain dict lookup",
           results, baseline="dict global lookup")

    print()
    print("Reading this. ContextVar.get() is about as fast as a dict lookup, and")
    print(".set() is cheap too. The per-context correctness of a ContextVar")
    print("(Listing 53.1) is therefore essentially free: there is no performance")
    print("reason to keep request-scoped state in a fragile module global that")
    print("async interleaving corrupts. Use a ContextVar for request id, current")
    print("user, and trace context in any concurrent (async or threaded) code.")


if __name__ == "__main__":
    main()
