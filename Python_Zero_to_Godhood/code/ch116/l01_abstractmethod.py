"""Listing 116.1 - abstract base classes: @abstractmethod enforces an interface.

An abstract base class (ABC) defines an interface that subclasses MUST implement.
Inherit from abc.ABC (whose metaclass is ABCMeta) and mark required methods with
@abstractmethod. Then:
  - the ABC itself cannot be instantiated (TypeError) while any abstract method is
    unimplemented, and
  - a subclass becomes concrete (instantiable) only once it overrides EVERY abstract
    method.
This turns 'you forgot to implement area()' from a runtime AttributeError deep in
the code into a TypeError at construction. This listing shows the enforcement.
"""

import abc


class Shape(abc.ABC):
    @abc.abstractmethod
    def area(self):
        """Subclasses must implement this."""

    @abc.abstractmethod
    def name(self):
        ...


class Circle(Shape):
    def __init__(self, r):
        self.r = r

    def area(self):
        return 3.14159 * self.r ** 2

    def name(self):
        return "circle"


class Incomplete(Shape):                 # implements area but NOT name
    def area(self):
        return 0


def main() -> None:
    print("--- the ABC itself cannot be instantiated ---")
    try:
        Shape()
    except TypeError as e:
        print(f"  Shape() -> TypeError (is abstract): {'abstract' in str(e)}")

    print("--- a fully-implementing subclass is concrete ---")
    c = Circle(2)
    print(f"  Circle(2).area() : {c.area():.5f}   name: {c.name()}")

    print("--- a subclass missing an abstract method is STILL abstract ---")
    try:
        Incomplete()
    except TypeError as e:
        print(f"  Incomplete() -> TypeError (name unimplemented): {'abstract' in str(e)}")

    print("--- isinstance/issubclass see the interface relationship ---")
    print(f"  isinstance(Circle(2), Shape) : {isinstance(c, Shape)}")
    print(f"  issubclass(Circle, Shape)    : {issubclass(Circle, Shape)}")

    print("--- the rule ---")
    print(f"  abc.ABC + @abstractmethod defines a required interface; the class")
    print(f"  cannot be instantiated until every abstract method is overridden")


if __name__ == "__main__":
    main()
