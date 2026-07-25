"""Benchmark 55.1 - formatting a traceback is far costlier than the message alone.

Catching an exception three ways: catch only, catch and str(e) (the message),
and catch and traceback.format_exc() (the full formatted traceback).
format_exc walks every frame in the traceback and reads the source lines for
each, so it is much more expensive than stringifying the exception message. This
matters when logging errors at high rate: the full traceback is invaluable for
debugging but should not be produced on a path that fires constantly.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import traceback

def deep(n):
    if n == 0:
        raise ValueError("boom")
    return deep(n - 1)

def just_catch():
    try:
        deep(20)
    except ValueError:
        return 1

def catch_str():
    try:
        deep(20)
    except ValueError as e:
        return str(e)

def catch_format():
    try:
        deep(20)
    except ValueError:
        return traceback.format_exc()
"""


def main() -> None:
    results = [
        measure("catch only", "just_catch()", SETUP, number=20000),
        measure("catch + str(e)", "catch_str()", SETUP, number=20000),
        measure("catch + format_exc()", "catch_format()", SETUP, number=20000),
    ]
    report("55.1  handling an exception: catch vs str vs full traceback",
           results, baseline="catch + str(e)")

    print()
    print("Reading this. Catching the exception and stringifying its message is")
    print("cheap. traceback.format_exc() is far more expensive because it walks")
    print("every frame in the traceback and reads the source lines for each. The")
    print("full traceback is essential for debugging, so log it, but produce it in")
    print("the error path, not on a path that fires constantly. For a high-rate")
    print("expected error, log the message (str) and count it; reserve the full")
    print("traceback for unexpected failures.")


if __name__ == "__main__":
    main()
