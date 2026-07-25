"""Benchmark 87.1 - NewType is near-free; a wrapper class costs time and memory.

A NewType "constructor" returns its argument unchanged (identity), so making a
UserId is barely more than a function call and allocates NO new object. A real
wrapper class allocates an instance per value and runs __init__. This measures
both against a bare int, so the cost of static-only distinctness (NewType) versus
runtime distinctness (a class) is visible.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
from typing import NewType
UserId = NewType("UserId", int)

class UserIdClass:
    __slots__ = ("value",)
    def __init__(self, value):
        self.value = value
"""


def main() -> None:
    results = [
        measure("bare int(42)", "int(42)", SETUP, number=2000000),
        measure("UserId(42) (NewType)", "UserId(42)", SETUP, number=2000000),
        measure("UserIdClass(42) (wrapper)", "UserIdClass(42)", SETUP, number=2000000),
    ]
    report("87.1  making a distinct id: NewType vs wrapper class",
           results, baseline="bare int(42)")

    print()
    print("Reading this. NewType('UserId', int) returns its argument unchanged, so")
    print("UserId(42) is barely more than a call and allocates no object, a UserId")
    print("IS the int. A wrapper class allocates an instance per value (and, without")
    print("__slots__, a per-instance dict). So NewType buys static distinctness")
    print("(UserId vs OrderId caught by the checker) at essentially zero runtime")
    print("cost and zero memory, while a wrapper buys RUNTIME distinctness and")
    print("methods at a real cost. Use NewType to keep same-underlying-type ids from")
    print("being confused; use a class when you need behavior, validation, or a")
    print("runtime-distinct type.")


if __name__ == "__main__":
    main()
