"""Benchmark 92.1 - generics are free to CALL; subscripting them allocates.

Two runtime facts about generics. Calling a generic function costs the same as a
non-generic one, the TypeVar is erased, there is no runtime type check. But
SUBSCRIPTING a generic (list[int], dict[str, int]) builds a types.GenericAlias
object each time, so it costs several times a bare type reference. In deferred
annotations (Chapter 12) the subscription is never evaluated, so this cost is
irrelevant there; it matters only if you build parameterized generics at runtime
in a hot path. This measures both.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
from typing import Any

def generic[T](items: list[T]) -> T:
    return items[0]

def plain(items: list) -> Any:
    return items[0]
"""


def main() -> None:
    results = [
        measure("call plain (Any)", "plain([1, 2, 3])", SETUP, number=2000000),
        measure("call generic[T]", "generic([1, 2, 3])", SETUP, number=2000000),
        measure("reference bare 'list'", "list", SETUP, number=2000000),
        measure("subscript list[int]", "list[int]", SETUP, number=2000000),
    ]
    report("92.1  generics: calling (erased, free) vs subscripting (allocates)",
           results, baseline="reference bare 'list'")

    print()
    print("Reading this. Calling a generic function costs the same as a non-generic")
    print("one, the TypeVar is erased and there is no runtime check, so a generic")
    print("preserves precise static types (better than Any) for free. The only")
    print("runtime cost is SUBSCRIPTING a generic (list[int]), which allocates a")
    print("GenericAlias object, several times a bare type reference. That cost is")
    print("paid only when you evaluate a parameterized generic at runtime; in")
    print("deferred annotations it never runs. So annotate generically without")
    print("hesitation; avoid building list[int]/dict[str,int] in a hot loop.")


if __name__ == "__main__":
    main()
