"""Listing 118.2 - plain Enum safety, IntEnum interop, and Flag bitwise sets.

A plain Enum member is NOT equal to its raw value: Color.RED != 1. This is a safety
feature, it stops an enum from being accidentally confused with a bare int or string.
When you DO need the member to behave as its value (for C interop, or comparing with
external numeric codes), IntEnum makes members real ints. Flag members combine with
bitwise | & ~ to represent sets of options. This listing shows all three.
"""

from enum import Enum, IntEnum, Flag, auto


class Color(Enum):
    RED = 1
    GREEN = 2


class Priority(IntEnum):                 # members ARE ints
    LOW = 1
    HIGH = 2


class Perm(Flag):                        # members combine bitwise
    R = auto()
    W = auto()
    X = auto()


def main() -> None:
    print("--- a plain Enum member is NOT its value (safety) ---")
    print(f"  Color.RED == 1        : {Color.RED == 1}   (not equal: avoids confusion)")
    print(f"  Color.RED.value == 1  : {Color.RED.value == 1}   (the value is)")

    print("--- IntEnum members ARE ints (interop with numeric codes) ---")
    print(f"  Priority.HIGH == 2    : {Priority.HIGH == 2}")
    print(f"  Priority.HIGH + 1     : {Priority.HIGH + 1}   (arithmetic works)")
    print(f"  isinstance(Priority.HIGH, int) : {isinstance(Priority.HIGH, int)}")

    print("--- Flag: combine options with bitwise operators ---")
    rw = Perm.R | Perm.W
    print(f"  Perm.R | Perm.W       : {rw}")
    print(f"  Perm.R in (R|W)       : {Perm.R in rw}")
    print(f"  Perm.X in (R|W)       : {Perm.X in rw}")
    print(f"  (R|W) & W             : {rw & Perm.W}")

    print("--- the rule ---")
    print(f"  plain Enum is value-safe (member != raw value); IntEnum for numeric")
    print(f"  interop; Flag for bitwise sets of options")


if __name__ == "__main__":
    main()
