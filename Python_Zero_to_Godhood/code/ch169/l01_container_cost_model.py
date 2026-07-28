"""Listing 169.1 - the container decision, counted rather than argued.

Chapter 87 said to fix the exponent before the constant. In Python the exponent is
almost always decided by which CONTAINER you reached for, because the standard library
already provides a data structure with the right exponent for every common access
pattern. Choosing badly is the single most common way to write an accidental quadratic;
choosing well is usually a one-line change.

This listing counts the primitive operations each container performs for a lookup, at
n=1024 and n=2048, so the growth is visible rather than asserted:

  dict / set membership   1 hash, whatever n is         -> constant
  bisect on a sorted list exactly log2(n) comparisons   -> logarithmic
  list.index              exactly n comparisons         -> linear
  heapq                   the cost of maintaining order incrementally

The numbers are exact because they are counts, so they are identical on both
verification interpreters, and the logarithmic row is the most convincing: 10
comparisons at 1024 elements and 11 at 2048, which is what log2 looks like when you can
see it.
"""

import bisect
import heapq

SMALL = 1024
LARGE = 2048


class Counted:
    """Reports every comparison and hash it takes part in."""

    __slots__ = ("value",)
    operations = 0

    def __init__(self, value):
        self.value = value

    def __lt__(self, other):
        type(self).operations += 1
        return self.value < other.value

    def __eq__(self, other):
        type(self).operations += 1
        return self.value == other.value

    def __hash__(self):
        type(self).operations += 1
        return hash(self.value)


def reset():
    Counted.operations = 0


def dict_lookup(n):
    table = {Counted(i): i for i in range(n)}
    reset()
    return table.get(Counted(n // 3))


def set_membership(n):
    members = {Counted(i) for i in range(n)}
    reset()
    return Counted(n // 3) in members


def bisect_sorted_list(n):
    data = [Counted(i) for i in range(n)]
    reset()
    return bisect.bisect_left(data, Counted(n // 3))


def list_index(n):
    data = [Counted(i) for i in range(n)]
    reset()
    return data.index(Counted(n - 1))


def heap_build_then_min(n):
    heap = []
    reset()
    for i in range(n):
        heapq.heappush(heap, Counted((i * 37) % n))
    heapq.heappop(heap)
    return len(heap)


CASES = (
    ("dict[key]", dict_lookup, "constant"),
    ("x in set", set_membership, "constant"),
    ("bisect on a sorted list", bisect_sorted_list, "logarithmic"),
    ("list.index(x)", list_index, "linear"),
    ("n heappush + one heappop", heap_build_then_min, "n log n"),
)


def count(fn, n):
    fn(n)
    return Counted.operations


def main() -> None:
    print(f"--- primitive operations for one lookup, at n={SMALL} and n={LARGE} ---")
    print(f"  {'operation':<26} {'n=1024':>8} {'n=2048':>8}  growth")
    print("  " + "-" * 56)
    for label, fn, growth in CASES:
        print(f"  {label:<26} {count(fn, SMALL):8,} {count(fn, LARGE):8,}  {growth}")

    print("--- the logarithmic row, spelled out ---")
    print(f"  bisect at n=1024 takes {count(bisect_sorted_list, SMALL)} comparisons, "
          f"and log2(1024) = 10")
    print(f"  at n=2048 it takes {count(bisect_sorted_list, LARGE)}, and log2(2048) = 11")
    print("  doubling the data costs exactly one more comparison")

    print("--- the decision, as a table of access patterns ---")
    print("  membership, by key            -> set / dict          constant")
    print("  ordered scan, append at end   -> list                amortised constant")
    print("  append or pop at BOTH ends    -> collections.deque   constant")
    print("  smallest item, repeatedly     -> heapq               log n per operation")
    print("  nearest item in sorted order  -> bisect on a list    log n")
    print("  counting occurrences          -> collections.Counter constant per item")
    print("  fixed-width numbers, compact  -> array.array         constant, no boxing")

    print("--- and the two questions that pick the container ---")
    print("  1. what do you do to it MOST OFTEN? that operation must be cheap.")
    print("  2. what do you do to it RARELY? that operation may be linear.")

    print("--- the rule ---")
    print("  a wrong container is an exponent, not a constant; the standard library")
    print("  already has one with the exponent you want")


if __name__ == "__main__":
    main()
