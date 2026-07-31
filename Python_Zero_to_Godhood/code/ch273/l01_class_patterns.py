"""Listing 273.1 - Python 3.10 (2021): class patterns in match/case.

Sequence and mapping patterns match built-in containers; class patterns match
YOUR objects - by type, and by their attributes, binding them in one step. This
is what makes match genuinely useful for typed data: an AST, a shape hierarchy,
a set of event classes. `case Circle(radius=r)` means 'a Circle whose radius,
bound to r'. With __match_args__ (which dataclasses set automatically), you can
match POSITIONALLY: `case Point(x, y)`. Class patterns turn a chain of isinstance
+ attribute access into declarative, type-directed dispatch. Deep C owns the type
model and __match_args__; this chapter is the class-pattern facet of the 3.10
release. Verified on current interpreters.
"""

from dataclasses import dataclass


@dataclass
class Point:
    x: int
    y: int


@dataclass
class Circle:
    center: Point
    radius: float


@dataclass
class Rectangle:
    width: float
    height: float


def area(shape):
    match shape:
        case Circle(radius=r):                   # a Circle; bind its radius
            return 3.14159 * r * r
        case Rectangle(width=w, height=h):
            return w * h
        case Point():                            # any Point (a degenerate shape)
            return 0.0
        case _:
            return None


def main() -> None:
    print("--- class patterns match by TYPE and bind attributes ---")
    shapes = [Circle(Point(0, 0), 2.0), Rectangle(3.0, 4.0), Point(1, 1)]
    for s in shapes:
        print(f"  area({type(s).__name__}) : {area(s)}")
    print("  `case Circle(radius=r)` matches an instance of Circle AND binds its")
    print("  .radius to r. one pattern does the isinstance check and the")
    print("  attribute pull that used to be two separate steps")

    print("--- positional matching via __match_args__ (dataclasses set it) ---")
    print(f"  Point.__match_args__ : {Point.__match_args__}")
    def describe(p):
        match p:
            case Point(0, 0):                    # positional: x==0 and y==0
                return "origin"
            case Point(x, 0):
                return f"on x-axis at {x}"
            case Point(0, y):
                return f"on y-axis at {y}"
            case Point(x, y):
                return f"point ({x}, {y})"
    for p in [Point(0, 0), Point(5, 0), Point(2, 3)]:
        print(f"  describe({p}) : {describe(p)}")
    print("  __match_args__ = ('x', 'y') lets `Point(x, y)` match POSITIONALLY,")
    print("  mapping the first sub-pattern to .x and the second to .y. @dataclass")
    print("  sets it from the field order, so positional matching just works")

    print("--- nested class patterns: match structure several levels deep ---")
    def centered_at_origin(shape):
        match shape:
            case Circle(center=Point(0, 0), radius=r):  # a Circle centred at (0,0)
                return f"origin circle, radius {r}"
            case Circle(center=Point(x, y)):
                return f"circle centred at ({x}, {y})"
            case _:
                return "not a circle"
    print(f"  {centered_at_origin(Circle(Point(0, 0), 5.0))}")
    print(f"  {centered_at_origin(Circle(Point(3, 4), 1.0))}")
    print("  the sub-pattern for `center` is ITSELF a class pattern Point(0, 0).")
    print("  patterns nest, so you match a Circle whose center is the origin in")
    print("  one expression - deep structural dispatch on typed objects")

    print("--- a class pattern also checks isinstance, so subtypes match ---")
    @dataclass
    class ColoredPoint(Point):
        color: str = "black"
    def is_point(obj):
        match obj:
            case Point():
                return True
            case _:
                return False
    print(f"  is_point(ColoredPoint(1, 2, 'red')) : "
          f"{is_point(ColoredPoint(1, 2, 'red'))}")
    print("  `case Point()` matches any Point OR subclass, because the type")
    print("  check is an isinstance test (Deep C). a ColoredPoint IS a Point, so")
    print("  it matches - type-directed dispatch that respects inheritance")

    print("--- the constraint answered ---")
    print("  matching YOUR objects meant isinstance checks plus attribute")
    print("  access, branch after branch. class patterns (3.10) do both at once:")
    print("  `Type(attr=pattern)` checks the type and binds attributes, positional")
    print("  matching via __match_args__, patterns nest, and subclasses match.")
    print("  typed data got declarative, structural dispatch")


if __name__ == "__main__":
    main()
