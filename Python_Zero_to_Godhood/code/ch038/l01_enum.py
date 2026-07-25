"""Listing 38.1 - enum: named singletons, and the IntEnum footgun.

An Enum turns a set of related constants into a type: each member is a named
singleton, so identity (is) works and the set is closed and self-documenting.
This listing shows the singleton property, the difference between Enum and
IntEnum (IntEnum compares equal to plain ints, which is a footgun), auto()
values, and Flag for combinable bit-sets.
"""

from enum import Enum, IntEnum, Flag, auto


class Color(Enum):
    RED = auto()
    GREEN = auto()
    BLUE = auto()


class Status(IntEnum):
    OK = 200
    NOT_FOUND = 404


class Perm(Flag):
    R = auto()
    W = auto()
    X = auto()


def main() -> None:
    print("--- members are singletons: identity works ---")
    print(f"  Color.RED is Color.RED : {Color.RED is Color.RED}")
    print(f"  Color(1) is Color.RED  : {Color(1) is Color.RED}")   # value lookup
    print(f"  Color['RED'] is RED    : {Color['RED'] is Color.RED}")  # name lookup

    print("--- Enum vs IntEnum: the equality footgun ---")
    print(f"  Color.RED == 1         : {Color.RED == 1}")     # plain Enum: False
    print(f"  Status.OK == 200       : {Status.OK == 200}")   # IntEnum: True (!)
    print(f"  isinstance(Status.OK,int): {isinstance(Status.OK, int)}")

    print("--- auto() assigns values; the member remembers name and value ---")
    print(f"  Color.GREEN            : {Color.GREEN!r}")
    print(f"  .name / .value         : {Color.GREEN.name} / {Color.GREEN.value}")

    print("--- Flag: combinable bit-sets ---")
    rw = Perm.R | Perm.W
    print(f"  Perm.R | Perm.W        : {rw}")
    print(f"  Perm.R in (R|W)        : {Perm.R in rw}")
    print(f"  Perm.X in (R|W)        : {Perm.X in rw}")


if __name__ == "__main__":
    main()
