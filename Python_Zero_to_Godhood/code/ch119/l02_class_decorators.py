"""Listing 119.2 - class decorators, and the three tools for customizing classes.

A class decorator is a function that receives a class and returns a (usually the
same, modified) class. @dataclass is one. It runs ONCE, after the class body, and
is the simplest of the three ways to customize class creation:
  - CLASS DECORATOR: modifies one class explicitly at its definition. Not inherited.
  - __init_subclass__: a base hook that runs for every subclass. Inherited.
  - METACLASS (Chapter 31): controls class creation itself; most powerful, heaviest.
This listing shows a class decorator and contrasts the reach of each tool.
"""


def auto_repr(cls):
    """A class decorator: add a __repr__ listing the instance's fields."""
    def __repr__(self):
        fields = ", ".join(f"{k}={v!r}" for k, v in vars(self).items())
        return f"{type(self).__name__}({fields})"
    cls.__repr__ = __repr__
    return cls                           # return the (modified) class


@auto_repr
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y


@auto_repr
class Person:
    def __init__(self, name):
        self.name = name


def main() -> None:
    print("--- a class decorator modifies the class at definition ---")
    print(f"  Point(1, 2)   : {Point(1, 2)!r}")
    print(f"  Person('ann') : {Person('ann')!r}")

    print("--- it is NOT inherited: a subclass is not re-decorated ---")
    class Point3D(Point):
        def __init__(self, x, y, z):
            super().__init__(x, y)
            self.z = z
    # Point3D inherits Point's __repr__ (set by the decorator on Point), but the
    # decorator itself did not run for Point3D
    print(f"  Point3D(1, 2, 3) uses inherited repr : {Point3D(1, 2, 3)!r}")

    print("--- the three tools, by reach ---")
    print(f"  class decorator   : one class, explicit, not inherited (e.g. @dataclass)")
    print(f"  __init_subclass__ : every subclass of a base, inherited (registries)")
    print(f"  metaclass         : class creation itself, most powerful (Chapter 31)")

    print("--- the rule ---")
    print(f"  prefer the lightest tool that works: class decorator for one class,")
    print(f"  __init_subclass__ for a family, metaclass only when neither suffices")


if __name__ == "__main__":
    main()
