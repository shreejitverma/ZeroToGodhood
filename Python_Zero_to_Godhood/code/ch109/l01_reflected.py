"""Listing 109.1 - the six comparison methods, the reflected fallback, and sorting.

Ordering is six independent special methods: __lt__ __le__ __gt__ __ge__ (order)
plus __eq__ __ne__ (equality). Two facts about how they interact:
  - They are REFLECTIVE in pairs: a > b, if type(a) has no usable __gt__, falls
    back to the reflected type(b).__lt__(b, a). So < and > are two ends of one
    relation, and defining __lt__ alone makes BOTH a < b and b > a work.
  - But there is NO automatic derivation across the pairs: defining __lt__ does
    NOT give you __le__ or __ge__; those raise TypeError until defined.
Sorting, min, max, and heapq need ONLY __lt__. This listing shows each.
"""


class Only:
    """Defines __lt__ only."""

    def __init__(self, v):
        self.v = v

    def __lt__(self, other):
        return self.v < other.v

    def __repr__(self):
        return f"Only({self.v})"


class Traced:
    def __init__(self, v):
        self.v = v

    def __lt__(self, other):
        print("    -> Traced.__lt__ was called")
        return self.v < other.v


def main() -> None:
    print("--- sorting needs ONLY __lt__ ---")
    print(f"  sorted([Only(3), Only(1), Only(2)]) : {sorted([Only(3), Only(1), Only(2)])}")
    print(f"  min : {min([Only(3), Only(1), Only(2)])}   max : {max([Only(3), Only(1), Only(2)])}")

    print("--- a > b falls back to the reflected b.__lt__ ---")
    a, b = Traced(1), Traced(2)
    result = b > a                       # Traced has no __gt__; reflects to a.__lt__
    print(f"  b > a evaluates to : {result}   (via the reflected __lt__ above)")

    print("--- but __le__/__ge__ are NOT derived from __lt__ ---")
    try:
        Only(1) >= Only(1)
    except TypeError as e:
        ok = "not supported" in str(e)
        print(f"  Only(1) >= Only(1) raises {type(e).__name__} (>= undefined): {ok}")

    print("--- the rule ---")
    print(f"  < and > reflect to one relation; equality is separate; but the four")
    print(f"  order methods are otherwise independent (see total_ordering next)")


if __name__ == "__main__":
    main()
