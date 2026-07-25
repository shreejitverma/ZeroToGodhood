"""Benchmark 90.1 - a Literal value is free (a plain str); an Enum member costs.

A Literal parameter is a plain str at runtime, so passing and using it is exactly
as cheap as a bare str. An Enum parameter is a member object, and getting its
underlying value goes through .value (an attribute access). This measures a
function taking a Literal str versus one taking an Enum member, so the cost of
runtime members versus static-only literals is visible.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
from typing import Literal
from enum import Enum

def with_literal(mode: Literal["r", "w", "a"]) -> str:
    return "opened " + mode

class Mode(Enum):
    R = "r"
    W = "w"
    A = "a"

def with_enum(mode: Mode) -> str:
    return "opened " + mode.value
"""


def main() -> None:
    results = [
        measure("Literal (plain str)", "with_literal('w')", SETUP, number=2000000),
        measure("Enum (member.value)", "with_enum(Mode.W)", SETUP, number=2000000),
    ]
    report("90.1  a fixed-set parameter: Literal str vs Enum member",
           results, baseline="Literal (plain str)")

    print()
    print("Reading this. A Literal value is a plain str, so passing and using it is")
    print("as cheap as any str, the Literal annotation is erased and costs nothing.")
    print("An Enum member is a real object, and reaching its underlying value goes")
    print("through .value, so it costs more. So Literal is the cheaper choice when a")
    print("small fixed set of values needs only STATIC checking (the runtime does")
    print("not enforce it). Reach for an Enum when you need the runtime members,")
    print("identity comparison, iteration over the set, or runtime rejection of")
    print("invalid values, and accept the small cost for those capabilities.")


if __name__ == "__main__":
    main()
