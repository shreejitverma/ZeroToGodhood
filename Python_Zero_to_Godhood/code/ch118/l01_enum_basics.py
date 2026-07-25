"""Listing 118.1 - Enum: named constant members that are singletons.

enum.Enum turns a class of NAME = value assignments into a set of named, singleton
members. Each member:
  - has a .name and a .value,
  - is a SINGLETON (exactly one object; compare with 'is'),
  - is reachable by name (Color['RED']) and by value (Color(1)),
  - and the class is iterable (in definition order).
auto() assigns the next value automatically. Duplicate values create ALIASES (a
second name for the same member), which do not appear in iteration. This listing
shows each.
"""

from enum import Enum, auto


class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = auto()                        # auto -> 3 (next after GREEN)


class Status(Enum):
    ACTIVE = 1
    RUNNING = 1                          # duplicate value -> ALIAS for ACTIVE


def main() -> None:
    print("--- a member has a name and a value ---")
    print(f"  Color.RED        : {Color.RED}")
    print(f"  Color.RED.name   : {Color.RED.name}")
    print(f"  Color.RED.value  : {Color.RED.value}")
    print(f"  Color.BLUE.value : {Color.BLUE.value}   (auto)")

    print("--- members are SINGLETONS: compare with is ---")
    print(f"  Color.RED is Color.RED : {Color.RED is Color.RED}")
    print(f"  Color(1) is Color.RED  : {Color(1) is Color.RED}   (value lookup)")
    print(f"  Color['RED'] is Color.RED : {Color['RED'] is Color.RED}   (name lookup)")

    print("--- the class is iterable, in definition order ---")
    print(f"  list(Color) names : {[c.name for c in Color]}")

    print("--- a duplicate value is an ALIAS, not a new member ---")
    print(f"  Status.RUNNING is Status.ACTIVE : {Status.RUNNING is Status.ACTIVE}")
    print(f"  iteration excludes aliases      : {[s.name for s in Status]}")

    print("--- the rule ---")
    print(f"  Enum members are named singletons with .name/.value; compare with is,")
    print(f"  look up by name or value, iterate the class; duplicate values are aliases")


if __name__ == "__main__":
    main()
