"""Listing 230.1 - Python 2.2 (2001): __slots__, fixed attributes without a per-instance dict.

New-style classes (2.2) store instance attributes in a per-instance __dict__ -
flexible (add any attribute at runtime) but costly: every instance carries a
whole dictionary. When you have millions of small objects (points, rows, tree
nodes), that dict dominates memory. 2.2's __slots__ lets a class declare a
FIXED set of attributes stored in a compact array instead of a dict: much
smaller instances, and a typo-catching side effect (unknown attributes raise
instead of silently creating a field). Deep A owns the object layout; this is
the release that gave you a memory lever for high-count objects, the concern
Chapter 88's cost model raises for object-heavy code. Verified on current
interpreters.
"""

import sys


class PointDict:
    """Ordinary new-style class: attributes live in a per-instance __dict__."""
    def __init__(self, x, y):
        self.x = x
        self.y = y


class PointSlots:
    """__slots__: attributes live in a fixed array, no per-instance __dict__."""
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x = x
        self.y = y


def main() -> None:
    print("--- the default: every instance carries a __dict__ ---")
    pd = PointDict(1, 2)
    print(f"  PointDict instance has __dict__ : {hasattr(pd, '__dict__')}")
    print(f"  its contents : {pd.__dict__}")
    print("  the __dict__ is what lets you add pd.z = 9 at runtime. flexible,")
    print("  but every instance pays for a whole dictionary (Deep A's layout)")

    print("--- __slots__: a fixed array, no __dict__ ---")
    ps = PointSlots(1, 2)
    print(f"  PointSlots instance has __dict__ : {hasattr(ps, '__dict__')}")
    print(f"  x and y still work normally : {ps.x}, {ps.y}")
    print("  __slots__ = ('x','y') tells the type to store x and y in a compact")
    print("  slot array, NOT a dict. the attributes read and write identically;")
    print("  only the storage changed (the point of the mechanism)")

    print("--- the memory win: smaller instances ---")
    dict_size = sys.getsizeof(pd) + sys.getsizeof(pd.__dict__)
    slots_size = sys.getsizeof(ps)
    print(f"  PointDict  : object {sys.getsizeof(pd)} + dict "
          f"{sys.getsizeof(pd.__dict__)} = {dict_size} bytes")
    print(f"  PointSlots : object {slots_size} bytes (no dict)")
    print(f"  slots instance is smaller : {slots_size < dict_size}")
    print("  the dict is the bulk of a small object's cost. remove it and each")
    print("  instance shrinks - decisive when you have millions of them, which")
    print("  is exactly when Chapter 88's cost model says to care about layout")

    print("--- the side effect: __slots__ catches attribute typos ---")
    print(f"  pd.actve = True  (typo on a __dict__ class):")
    pd.actve = True                              # silently creates a NEW field
    print(f"    silently created pd.actve = {pd.actve}  (bug hides)")
    print(f"  ps.actve = True  (typo on a __slots__ class):")
    try:
        ps.actve = True                          # no slot named 'actve'
    except AttributeError as exc:
        print(f"    raised AttributeError({exc})  (bug caught)")
    print("  with a __dict__, a misspelled attribute silently becomes a new")
    print("  field and the real one stays unset - a classic silent bug. with")
    print("  __slots__, only declared names exist, so the typo raises at once")

    print("--- the cost of __slots__: you give up dynamic attributes ---")
    print("  ps.z = 9 would raise: 'z' is not a declared slot. that is the")
    print("  trade - you lose runtime attribute addition (and multiple")
    print("  inheritance gets fiddly) in exchange for memory and typo-safety.")
    print("  use it for high-count, fixed-shape objects; skip it otherwise")

    print("--- the constraint answered ---")
    print("  new-style classes (2.2) gave every instance a flexible __dict__,")
    print("  which costs memory that dominates when objects are small and")
    print("  numerous. __slots__ (same release) is the lever: declare the")
    print("  fields, drop the dict, shrink the instance, and catch typos - the")
    print("  memory knob for object-heavy code Chapter 88 tells you to reach for")


if __name__ == "__main__":
    main()
