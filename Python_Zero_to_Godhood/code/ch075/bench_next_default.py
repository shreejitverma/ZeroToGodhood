"""Benchmark 75.1 - next(it, default) avoids the cost of catching StopIteration.

When you want "the next value or a fallback" and exhaustion is common, next(it,
default) returns the default directly, while try/except StopIteration must raise
and catch an exception on every exhausted call. Raising/catching is more expensive
than returning a default, so when the exhausted branch is hot, the builtin form is
faster. This measures both on an iterator that is immediately exhausted (the
fallback path taken every call).

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
def with_default():
    it = iter([1])
    next(it, None)          # consume the one value
    return next(it, None)   # exhausted -> None, no exception

def with_except():
    it = iter([1])
    next(it, None)
    try:
        return next(it)     # exhausted -> raises StopIteration
    except StopIteration:
        return None
"""


def main() -> None:
    results = [
        measure("next(it, default)", "with_default()", SETUP, number=1000000),
        measure("try/except StopIteration", "with_except()", SETUP, number=1000000),
    ]
    report("75.1  next-or-fallback: builtin default vs catching StopIteration",
           results, baseline="next(it, default)")

    print()
    print("Reading this. When the iterator is exhausted, next(it, default) returns")
    print("the default with no exception, while try/except must raise and catch")
    print("StopIteration, which is more expensive. So when the fallback path is")
    print("common, the builtin form is both cleaner and faster. (When exhaustion is")
    print("rare, the two are close, because the exception is seldom raised.) Prefer")
    print("next(it, default) for next-or-fallback, and iter(callable, sentinel) for")
    print("call-until-sentinel loops, over hand-written StopIteration handling.")


if __name__ == "__main__":
    main()
