"""Listing 117.2 - the mutable-default trap, default_factory, and slots=True.

Two things every dataclass user must know:
  - A MUTABLE default (list, dict, set) is REJECTED at class creation, because a
    single default object would be SHARED across all instances (the classic mutable-
    default bug, Chapter on functions). Use field(default_factory=list) to get a
    fresh one per instance.
  - slots=True (Python 3.10+) generates the class with __slots__ (Chapter 22), so
    instances have no __dict__: smaller objects and a locked attribute set.
This listing shows the rejection, the factory fix, and slotted instances.
"""

from dataclasses import dataclass, field


def main() -> None:
    print("--- a mutable default is rejected at class creation ---")
    try:
        @dataclass
        class Bad:
            items: list = []             # would be shared across instances
    except ValueError as e:
        print(f"  list default -> ValueError (use default_factory): "
              f"{'default_factory' in str(e)}")

    print("--- default_factory gives each instance its own object ---")
    @dataclass
    class Cart:
        items: list = field(default_factory=list)

    a, b = Cart(), Cart()
    a.items.append("apple")
    print(f"  a.items : {a.items}   b.items : {b.items}   (isolated, not shared)")

    print("--- slots=True: no __dict__, smaller instances, locked attributes ---")
    @dataclass(slots=True)
    class SlottedPoint:
        x: int
        y: int

    sp = SlottedPoint(1, 2)
    print(f"  has __dict__ : {hasattr(sp, '__dict__')}")
    print(f"  fields work  : {sp.x}, {sp.y}")
    try:
        sp.z = 3                         # not a declared field
    except AttributeError:
        print(f"  sp.z = 3 -> AttributeError (locked attribute set)")

    print("--- the rule ---")
    print(f"  mutable defaults need field(default_factory=...); slots=True generates")
    print(f"  __slots__ for smaller, attribute-locked instances")


if __name__ == "__main__":
    main()
