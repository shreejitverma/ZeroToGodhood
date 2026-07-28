"""Listing 168.1 - measuring an algorithm's exponent exactly, by counting rather than timing.

The most valuable number in performance work is not how long something takes; it is how
that time GROWS. A 30% constant-factor win is a good afternoon. Turning an accidental
O(n^2) into O(n) is a different program, and it is the difference that survives your
input getting larger.

The exponent can be measured exactly, with no timer and therefore no noise, using the
doubling method:

    run the operation at n and at 2n, count the primitive operations it performed,
    and take log2(count(2n) / count(n))

That figure IS the exponent. 1.00 is linear, 2.00 is quadratic, 0.00 is constant, and
n log n lands a little above 1. Because it counts rather than times, it is exact,
reproducible, and identical on both verification interpreters.

The primitive being counted here is a comparison or a hash, made observable by a small
class that tallies its own __eq__ and __hash__ calls. That is the same trick a real
investigation uses when the operation is not this convenient: count the thing the
algorithm does per step, whatever it is - rows fetched, bytes copied, files opened.
"""

import math

SMALL = 100
LARGE = 200


class Counted:
    """An object that reports every comparison and hash it takes part in."""

    __slots__ = ("value",)
    comparisons = 0
    hashes = 0

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        type(self).comparisons += 1
        return self.value == other.value

    def __lt__(self, other):
        type(self).comparisons += 1
        return self.value < other.value

    def __hash__(self):
        type(self).hashes += 1
        return hash(self.value)


def reset():
    Counted.comparisons = Counted.hashes = 0


def total():
    return Counted.comparisons + Counted.hashes


def membership_in_list(n):
    data = [Counted(i) for i in range(n)]
    reset()
    return Counted(-1) in data


def membership_in_set(n):
    data = {Counted(i) for i in range(n)}
    reset()
    return Counted(-1) in data


def duplicates_naive(n):
    data = [Counted(i) for i in range(n)]
    reset()
    for i in range(len(data)):
        for j in range(i + 1, len(data)):
            if data[i] == data[j]:
                return True
    return False


def duplicates_with_a_set(n):
    data = [Counted(i) for i in range(n)]
    reset()
    seen = set()
    for item in data:
        if item in seen:
            return True
        seen.add(item)
    return False


def sort_shuffled(n):
    data = [Counted((i * 37) % n) for i in range(n)]
    reset()
    data.sort()
    return data


CASES = (
    ("x in list", membership_in_list),
    ("x in set", membership_in_set),
    ("duplicates, nested loops", duplicates_naive),
    ("duplicates, with a set", duplicates_with_a_set),
    ("list.sort() on shuffled", sort_shuffled),
)


def exponent(fn):
    fn(SMALL)
    small = total()
    fn(LARGE)
    large = total()
    if small == 0:
        return small, large, 0.0
    return small, large, math.log2(large / small)


def classify(value):
    if value < 0.2:
        return "constant"
    if value < 1.05:
        return "linear"
    if value < 1.6:
        return "n log n"
    if value < 2.2:
        return "quadratic"
    return "worse than quadratic"


def main() -> None:
    print(f"--- primitive operations at n={SMALL} and n={LARGE}, and the exponent ---")
    print(f"  {'operation':<26} {'n=100':>8} {'n=200':>8} {'exponent':>9}  class")
    print("  " + "-" * 66)
    for label, fn in CASES:
        small, large, value = exponent(fn)
        print(f"  {label:<26} {small:8,} {large:8,} {value:9.2f}  {classify(value)}")

    print("--- what the doubling method is actually doing ---")
    print("  cost(n) = c * n^k, so cost(2n)/cost(n) = 2^k regardless of c;")
    print("  taking log2 of the ratio cancels the constant and leaves the exponent")

    print("--- and why the constant does not matter to this measurement ---")
    print("  a linear algorithm with a terrible constant still doubles when n doubles;")
    print("  a quadratic one with a tiny constant still quadruples, and wins the race")
    print("  in the other direction at every subsequent doubling")

    print("--- the rule ---")
    print("  measure the exponent before the constant: count operations at n and 2n,")
    print("  and only optimise the constant once the exponent is the one you want")


if __name__ == "__main__":
    main()
