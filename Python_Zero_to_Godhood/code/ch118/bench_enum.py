"""Benchmark 118.1 - Color.RED (direct) vs Color(1) (value lookup).

Accessing an enum member three ways: by attribute (Color.RED), by value (Color(1)),
and by name (Color['RED']). Attribute access is a direct read; value lookup goes
through EnumType.__call__, which searches the value->member mapping, so it is much
slower. This measures all three, to guide when to use each.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import timeit
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 5_000_000


class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3


def main():
    print("=== 118.1  enum member access: attribute vs value lookup vs name lookup ===")
    print(provenance())
    print()

    t_attr = min(timeit.repeat(lambda: Color.RED, number=N, repeat=5)) / N
    t_call = min(timeit.repeat(lambda: Color(1), number=N, repeat=5)) / N
    t_name = min(timeit.repeat(lambda: Color["RED"], number=N, repeat=5)) / N

    print(f"  Color.RED    (attribute)    : {t_attr * 1e9:6.1f} ns   1.0x")
    print(f"  Color(1)     (value lookup) : {t_call * 1e9:6.1f} ns   {t_call / t_attr:.1f}x")
    print(f"  Color['RED'] (name lookup)  : {t_name * 1e9:6.1f} ns   {t_name / t_attr:.1f}x")

    print()
    print("Reading this. Color.RED is a direct attribute read. Color(1) goes through")
    print("EnumType.__call__, which looks the value up in the value->member mapping,")
    print("several times slower here. The guidance follows: refer to enum members by")
    print("NAME in your code (Color.RED), which is direct, self-documenting, and")
    print("checked by tools. Reserve Color(value) for the BOUNDARY where you convert")
    print("an external value (a byte from a wire protocol, a code from a database) into")
    print("a member, and do it once there, not per use in a hot loop.")


if __name__ == "__main__":
    main()
