"""Listing 116.2 - virtual subclasses: register() and __subclasshook__.

ABCs can recognize types that do NOT inherit from them, which is how Python reconciles
nominal interfaces with duck typing. Two mechanisms:
  - ABC.register(SomeClass) declares SomeClass a VIRTUAL subclass: isinstance and
    issubclass say True, but SomeClass does not inherit anything (not in the MRO).
  - __subclasshook__(cls, C) lets an ABC decide membership STRUCTURALLY, by what a
    class can do, so any class with the right methods 'is a' subclass without
    registering. This is how collections.abc works: anything with __len__ is Sized.
This listing shows both, and the built-in collections.abc ABCs.
"""

import abc
from collections.abc import Sized, Iterable


class Drawable(abc.ABC):
    pass


class Widget:                            # does not inherit Drawable
    pass


class SupportsClose(abc.ABC):
    @classmethod
    def __subclasshook__(cls, C):
        # structural: any class with a 'close' method counts
        if any("close" in B.__dict__ for B in C.__mro__):
            return True
        return NotImplemented


class Connection:                        # never registered, never inherited
    def close(self):
        pass


def main() -> None:
    print("--- register(): a virtual subclass (isinstance True, not in the MRO) ---")
    Drawable.register(Widget)
    print(f"  isinstance(Widget(), Drawable) : {isinstance(Widget(), Drawable)}")
    print(f"  issubclass(Widget, Drawable)   : {issubclass(Widget, Drawable)}")
    print(f"  Drawable in Widget.__mro__     : {Drawable in Widget.__mro__}   (NOT a real base)")

    print("--- __subclasshook__: STRUCTURAL membership, no registration needed ---")
    print(f"  isinstance(Connection(), SupportsClose) : {isinstance(Connection(), SupportsClose)}")
    print(f"  (Connection has close(), so the hook accepts it)")

    print("--- collections.abc uses this for the standard protocols ---")
    print(f"  isinstance([], Sized)    : {isinstance([], Sized)}")
    print(f"  isinstance([], Iterable) : {isinstance([], Iterable)}")
    print(f"  isinstance(5, Iterable)  : {isinstance(5, Iterable)}   (int has no __iter__)")

    print("--- the rule ---")
    print(f"  register() adds a virtual subclass; __subclasshook__ recognizes types")
    print(f"  structurally; both make isinstance work without real inheritance")


if __name__ == "__main__":
    main()
