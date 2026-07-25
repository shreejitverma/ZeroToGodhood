"""Listing 110.2 - why __new__ exists: immutable subclasses and instance control.

__init__ cannot help two important cases, and __new__ is the answer to both:
  - IMMUTABLE types (str, int, tuple, frozenset). Their value is fixed at
    creation, so a subclass must set it in __new__, BEFORE the object exists;
    __init__ runs too late to change it. UpperStr customizes str this way.
  - INSTANCE CONTROL. Because __new__ decides WHICH object to return, it can
    return a SHARED, cached instance instead of a fresh one (the flyweight /
    interning pattern, exactly how CPython caches small ints, Chapter 19).
This listing shows both.
"""


class UpperStr(str):
    """An immutable str subclass: the value must be set in __new__."""

    def __new__(cls, value):
        # str is immutable: uppercase BEFORE the object is created
        return super().__new__(cls, value.upper())


class Color:
    """Flyweight: __new__ returns a shared instance per name."""

    _cache = {}

    def __new__(cls, name):
        obj = cls._cache.get(name)
        if obj is None:
            obj = super().__new__(cls)
            obj.name = name
            cls._cache[name] = obj
        return obj


def main() -> None:
    print("--- immutable subclass: value fixed in __new__ ---")
    s = UpperStr("hello")
    print(f"  UpperStr('hello') : {s}")
    print(f"  is a real str     : {isinstance(s, str)}")

    print("--- instance control: __new__ returns a SHARED instance ---")
    red1 = Color("red")
    red2 = Color("red")
    blue = Color("blue")
    print(f"  Color('red') is Color('red')  : {red1 is red2}   (same cached object)")
    print(f"  Color('red') is Color('blue') : {red1 is blue}")
    print(f"  distinct objects created      : {len(Color._cache)}   (red, blue)")

    print("--- the rule ---")
    print(f"  use __new__ to set immutable state (before creation) and to control")
    print(f"  which instance is returned (caching, singletons); __init__ cannot")


if __name__ == "__main__":
    main()
