"""Benchmark 94.1 - an overloaded function costs the same as a plain one.

The @overload stubs are static declarations; at runtime only the final, undecorated
implementation exists and runs. So calling an overloaded function is exactly a
normal function call, the overloads add no runtime dispatch. This measures an
overloaded function against an identical plain one to confirm the zero cost.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
from typing import overload

@overload
def parse(x: int) -> str: ...
@overload
def parse(x: str) -> int: ...
def parse(x):
    if isinstance(x, int):
        return str(x)
    return int(x)

def plain(x):
    if isinstance(x, int):
        return str(x)
    return int(x)
"""


def main() -> None:
    results = [
        measure("plain function", "plain(42)", SETUP, number=2000000),
        measure("overloaded function", "parse(42)", SETUP, number=2000000),
    ]
    report("94.1  calling an overloaded function vs a plain one",
           results, baseline="plain function")

    print()
    print("Reading this. The two are identical: the @overload stubs are static")
    print("declarations that never run, only the final implementation does, so an")
    print("overloaded function is a normal function at runtime with no dispatch")
    print("overhead. @overload buys static precision (a return type that depends on")
    print("the argument type, which a single union signature cannot express) for")
    print("free at runtime. Use it when the output type genuinely varies with the")
    print("input; do not use it as runtime dispatch (that is singledispatch,")
    print("Chapter 34, or an isinstance in the one implementation).")


if __name__ == "__main__":
    main()
