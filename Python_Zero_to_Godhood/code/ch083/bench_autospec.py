"""Benchmark 83.1 - autospec costs more to build, and catches bugs a Mock misses.

mock.Mock() creates a do-anything mock instantly. mock.create_autospec(target)
introspects the target's signature and builds a mock constrained to it, so it
costs more per mock. That cost buys signature validation: a call with the wrong
arguments fails, catching the bug where code (or a refactor) calls the mocked
thing incorrectly, which a bare Mock silently accepts. This measures the creation
cost of each.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
from unittest import mock

def target(a, b, c=3):
    return a + b + c
"""


def main() -> None:
    results = [
        measure("mock.Mock()", "mock.Mock()", SETUP, number=100000),
        measure("mock.create_autospec(target)", "mock.create_autospec(target)", SETUP, number=10000),
    ]
    report("83.1  bare Mock vs create_autospec creation cost",
           results, baseline="mock.Mock()")

    print()
    print("Reading this. create_autospec is far more expensive than a bare Mock")
    print("because it introspects the target's signature to build a constrained")
    print("mock. That cost buys correctness: an autospec mock rejects a call with")
    print("the wrong arguments, catching a bug (or a refactor that changed the real")
    print("signature) that a bare Mock, which accepts any call, silently passes as a")
    print("false green. The extra cost is per mock created (test setup), negligible")
    print("unless you build thousands. Prefer autospec (or spec=) for mocks that")
    print("stand in for real callables, so your tests fail when the real interface")
    print("changes.")


if __name__ == "__main__":
    main()
