"""Listing 109.2 - functools.total_ordering, and NotImplemented across types.

Because the four order methods are independent (Listing 109.1), defining all of
them by hand is repetitive and error-prone. functools.total_ordering synthesizes
the missing three order methods from __eq__ plus ONE of __lt__/__le__/__gt__/__ge__.
You write two comparisons; you get all six. This listing shows total_ordering
filling in the rest, and shows that a comparison method should return NotImplemented
(not raise) for a type it does not understand, so cross-type comparison degrades to
a clean TypeError rather than a wrong answer.
"""

import functools


@functools.total_ordering
class Version:
    """Defines only __eq__ and __lt__; total_ordering supplies __le__/__gt__/__ge__."""

    def __init__(self, n):
        self.n = n

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented        # let the other operand try
        return self.n == other.n

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self.n < other.n

    def __hash__(self):
        return hash(self.n)


def main() -> None:
    x, y = Version(1), Version(2)

    print("--- total_ordering gives all six from __eq__ + __lt__ ---")
    print(f"  x <  y : {x < y}      x <= y : {x <= y}")
    print(f"  x >  y : {x > y}     x >= y : {x >= y}")
    print(f"  x == y : {x == y}     x != y : {x != y}")
    print(f"  x <= x : {x <= x}   (derived __le__ works on equal values)")

    print("--- which methods actually exist on the class now ---")
    have = [m for m in ("__lt__", "__le__", "__gt__", "__ge__") if m in vars(Version)]
    print(f"  order methods in Version.__dict__ : {have}")
    print(f"  (only __lt__ was written; the rest were synthesized)")

    print("--- NotImplemented => clean TypeError across unrelated types ---")
    try:
        Version(1) < 5
    except TypeError as e:
        print(f"  Version(1) < 5 raises {type(e).__name__} : {'not supported' in str(e)}")

    print("--- the rule ---")
    print(f"  write __eq__ + one order method + @total_ordering for all six;")
    print(f"  return NotImplemented (not raise) for types you do not handle")


if __name__ == "__main__":
    main()
