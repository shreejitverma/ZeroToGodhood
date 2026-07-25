"""Listing 117.1 - @dataclass generates the boilerplate of a value class.

@dataclass reads the class's type-annotated fields and GENERATES, at class-creation
time, the methods you would otherwise hand-write:
  __init__  from the fields (with defaults)
  __repr__  as Class(field=value, ...)
  __eq__    comparing the fields as a tuple
Options add more: frozen=True makes instances immutable AND hashable (a proper value
type, Chapter 23); order=True generates the comparison methods (Chapter 24). This
listing shows the generated methods and the frozen/order options.
"""

from dataclasses import dataclass, FrozenInstanceError


@dataclass
class Point:
    x: int
    y: int = 0                           # a field with a default


@dataclass(frozen=True)
class FrozenPoint:
    x: int
    y: int


@dataclass(order=True)
class Version:
    major: int
    minor: int


def main() -> None:
    print("--- generated __init__ and __repr__ ---")
    p = Point(1, 2)
    print(f"  Point(1, 2)  : {p!r}")
    print(f"  Point(5)     : {Point(5)!r}   (y defaulted to 0)")

    print("--- generated __eq__ compares fields ---")
    print(f"  Point(1, 2) == Point(1, 2) : {Point(1, 2) == Point(1, 2)}")
    print(f"  Point(1, 2) == Point(1, 9) : {Point(1, 2) == Point(1, 9)}")

    print("--- frozen=True: immutable and hashable (a value type) ---")
    fp = FrozenPoint(1, 2)
    print(f"  hashable   : {isinstance(hash(fp), int)}")
    print(f"  set dedups : {len({FrozenPoint(1, 2), FrozenPoint(1, 2)})}   (one element)")
    try:
        fp.x = 99
    except FrozenInstanceError as e:
        print(f"  fp.x = 99 -> {type(e).__name__} (immutable)")

    print("--- order=True: generated comparisons (field order = sort order) ---")
    print(f"  Version(1, 2) < Version(1, 3) : {Version(1, 2) < Version(1, 3)}")
    print(f"  Version(2, 0) > Version(1, 9) : {Version(2, 0) > Version(1, 9)}")

    print("--- the rule ---")
    print(f"  @dataclass generates __init__/__repr__/__eq__ from annotated fields;")
    print(f"  frozen=True for immutable+hashable value types, order=True for sorting")


if __name__ == "__main__":
    main()
