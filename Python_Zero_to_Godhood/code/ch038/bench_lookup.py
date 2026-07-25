"""Benchmark 38.1 - three ways to reach an enum member, three costs.

Color.RED is attribute access: the member is already an attribute of the class,
so it is the fastest. Color['RED'] is a name lookup through the enum's member
map. Color(1) is a VALUE lookup: it goes through EnumType.__call__ and the
value-to-member map, and is the slowest by a wide margin. Knowing which is which
matters when enum lookup is on a hot path (e.g. decoding a wire value per
message).

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
from enum import Enum, auto

class Color(Enum):
    RED = auto()
    GREEN = auto()
    BLUE = auto()
"""


def main() -> None:
    results = [
        measure("Color.RED    (attribute)", "Color.RED", SETUP, number=100000),
        measure("Color['RED'] (name)", "Color['RED']", SETUP, number=100000),
        measure("Color(1)     (value)", "Color(1)", SETUP, number=100000),
    ]
    report("38.1  three ways to reach an enum member",
           results, baseline="Color.RED    (attribute)")

    print()
    print("Reading this. Color.RED is a plain attribute access on the enum class")
    print("and is the fastest. Color['RED'] looks the name up in the member map.")
    print("Color(1) is a VALUE lookup through EnumType.__call__ and the value-to-")
    print("member map, and is several times slower. When decoding a wire value to")
    print("a member on a hot path, cache the mapping or accept the cost knowingly;")
    print("do not assume Color(x) is as cheap as Color.RED.")


if __name__ == "__main__":
    main()
