"""Benchmark 91.1 - get_type_hints is expensive; cache the resolved hints.

Reading raw __annotations__ is a dict attribute access. typing.get_type_hints
EVALUATES each annotation (resolving strings under deferred annotations, following
forward references, walking the MRO for classes), which is far more work. A
framework that reflects on a type per request should build the hints ONCE and
cache them, not call get_type_hints repeatedly. This measures both on a small
function.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = '''
import typing

# string annotations (as deferred/PEP-563 annotations produce) so get_type_hints
# has real resolution work to do, without a from __future__ import in this snippet
def f(a: "int", b: "str", c: "list") -> "dict":
    return {}

cached = typing.get_type_hints(f)
'''


def main() -> None:
    results = [
        measure("raw __annotations__", "f.__annotations__", SETUP, number=200000),
        measure("cached hints (dict access)", "cached['a']", SETUP, number=200000),
        measure("get_type_hints(f) (fresh)", "typing.get_type_hints(f)", SETUP, number=20000),
    ]
    report("91.1  raw annotations vs resolving type hints",
           results, baseline="raw __annotations__")

    print()
    print("Reading this. Reading __annotations__ is a dict access; get_type_hints")
    print("evaluates each annotation to a real type (resolving strings and forward")
    print("references), which is orders of magnitude more expensive. A cached result")
    print("is a plain dict access again. So a framework that needs resolved types")
    print("(serializers, validators like pydantic, dependency injection) must call")
    print("get_type_hints ONCE per type and cache it, exactly like caching")
    print("inspect.signature (Chapter 49); never resolve hints per request.")


if __name__ == "__main__":
    main()
