"""Listing 247.1 - Python 3.2 (2011): functools.total_ordering, six comparisons from two.

To make a class fully orderable - usable with <, <=, >, >=, ==, != and with
sorted(), min(), max() - Python's data model asks for the rich-comparison
methods __lt__, __le__, __gt__, __ge__, __eq__. Writing all six by hand is
tedious and a place for bugs: get one inconsistent and sorting misbehaves in
ways that are painful to trace. Python 3.2's @total_ordering class decorator
derives the rest: define __eq__ and just ONE ordering method (say __lt__), and
it supplies __le__, __gt__, __ge__ consistently. Deep B owns the comparison
protocol; this is the release that made 'a fully ordered type' two methods
instead of six, with the consistency guaranteed rather than hand-maintained.
Verified on current interpreters.
"""

from functools import total_ordering


@total_ordering
class Version:
    """Order by (major, minor). Define only __eq__ and __lt__."""
    def __init__(self, major, minor):
        self.major = major
        self.minor = minor

    def _key(self):
        return (self.major, self.minor)

    def __eq__(self, other):
        return self._key() == other._key()

    def __lt__(self, other):
        return self._key() < other._key()

    def __repr__(self):
        return f"v{self.major}.{self.minor}"


def main() -> None:
    a = Version(1, 4)
    b = Version(2, 0)
    c = Version(1, 4)

    print("--- we defined only __eq__ and __lt__; the rest are derived ---")
    print(f"  a={a}, b={b}, c={c}")
    print(f"  a <  b : {a < b}   (defined)")
    print(f"  a <= c : {a <= c}   (DERIVED from __lt__ and __eq__)")
    print(f"  b >  a : {b > a}   (DERIVED)")
    print(f"  b >= a : {b >= a}   (DERIVED)")
    print(f"  a == c : {a == c}   (defined)")
    print(f"  a != b : {a != b}   (from __eq__)")
    print("  @total_ordering filled in <=, >, >= from the __lt__ and __eq__ we")
    print("  wrote. all six operators, two method definitions")

    print("--- the derived operators are present on the class ---")
    for op in ("__lt__", "__le__", "__gt__", "__ge__"):
        print(f"  Version defines {op} : {op in vars(Version)}")
    print("  the decorator ADDED __le__/__gt__/__ge__ to the class; we wrote")
    print("  only __lt__. they are real methods, derived once at class creation")

    print("--- it just works with sorted(), min(), max() ---")
    versions = [Version(2, 0), Version(1, 4), Version(1, 10), Version(1, 2)]
    print(f"  unsorted : {versions}")
    print(f"  sorted   : {sorted(versions)}")
    print(f"  min      : {min(versions)}")
    print(f"  max      : {max(versions)}")
    print("  sorting and min/max only need a consistent ordering, which the")
    print("  derived operators provide. note v1.10 > v1.4 because we order by")
    print("  the (major, minor) TUPLE, not by string - the __lt__ we chose")

    print("--- the consistency guarantee: no hand-maintained contradictions ---")
    print("  a < b and b > a agree :", (a < b) and (b > a))
    print("  a <= c and c >= a agree :", (a <= c) and (c >= a))
    print("  because all four ordering ops come from ONE __lt__, they cannot")
    print("  disagree. hand-writing six methods risks a typo that makes <= and")
    print("  > contradict each other - the decorator removes that whole class")
    print("  of bug")

    print("--- the constraint answered ---")
    print("  a fully ordered type needed six rich-comparison methods, tedious")
    print("  to write and easy to make inconsistent. @total_ordering (3.2)")
    print("  derives four of them from __eq__ plus one ordering method, so a")
    print("  sortable type is two definitions with consistency guaranteed -")
    print("  Deep B's comparison protocol, minus the boilerplate")


if __name__ == "__main__":
    main()
