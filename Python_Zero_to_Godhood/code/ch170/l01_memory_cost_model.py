"""Listing 170.1 - what a Python object costs, and why sys.getsizeof under-reports it.

Time is not the only resource with a cost model, and memory is the one Python spends
most freely. Every value is an object with a header; every container holds POINTERS to
objects rather than the values themselves; and the most common tool for measuring this,
sys.getsizeof, reports only the container, never what it points at.

Four facts, each measured rather than asserted, and each identical on both verification
interpreters because they are structural rather than allocator-dependent:

  a container's per-element cost, derived by differencing two sizes
  sys.getsizeof is SHALLOW, so a list of a million objects reports as 8 MB
  an instance with __dict__ against one with __slots__
  the boxing cost: a list of integers against the same integers in an array.array

The per-element figures are obtained by measuring a container at two sizes and dividing
the difference, which cancels the fixed header exactly as Chapter 87's doubling method
cancels the constant.
"""

import array
import sys

SMALL = 1_000
LARGE = 2_000


class WithDict:
    """An ordinary instance: attributes live in a per-instance __dict__."""

    def __init__(self, x, y):
        self.x = x
        self.y = y


class WithSlots:
    """The same two attributes, in fixed slots, with no per-instance dict."""

    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x = x
        self.y = y


def per_element(build):
    """Bytes the container itself spends per element, with the header differenced out."""
    return (sys.getsizeof(build(LARGE)) - sys.getsizeof(build(SMALL))) // (LARGE - SMALL)


def deep_size(sequence):
    """The container plus every object it points at, counted once each."""
    return sys.getsizeof(sequence) + sum(sys.getsizeof(item) for item in sequence)


def main() -> None:
    print("--- bytes per element in the container itself (header differenced out) ---")
    for label, build in (
        ("list", lambda n: [0] * n),
        ("tuple", lambda n: tuple([0] * n)),
        ("array.array('q')", lambda n: array.array("q", [0] * n)),
        ("bytes", lambda n: bytes(n)),
    ):
        print(f"  {label:<20} {per_element(build)} bytes")
    print("  a list, a tuple and an int64 array all cost 8 bytes per element, but the")
    print("  first two store POINTERS and the third stores the numbers themselves")

    print("--- sys.getsizeof is shallow, and that is the trap ---")
    # Both built the same way, so any difference is the contents and not the
    # list's over-allocation policy, which differs between a comprehension and [x] * n.
    hundred_objects = [object() for _ in range(100)]
    hundred_nones = [None for _ in range(100)]
    print(f"  a list of 100 distinct objects and a list of 100 Nones report the same size"
          f" : {sys.getsizeof(hundred_objects) == sys.getsizeof(hundred_nones)}")
    print(f"  because both hold 100 pointers; the objects are not counted")
    print(f"  deep size of the object list is larger : "
          f"{deep_size(hundred_objects) > sys.getsizeof(hundred_objects)}")

    print("--- an instance with __dict__ against one with __slots__ ---")
    plain = WithDict(1, 2)
    slotted = WithSlots(1, 2)
    plain_total = sys.getsizeof(plain) + sys.getsizeof(plain.__dict__)
    print(f"  WithDict  instance + its __dict__ : {plain_total} bytes")
    print(f"  WithSlots instance                : {sys.getsizeof(slotted)} bytes")
    print(f"  ratio                             : {plain_total / sys.getsizeof(slotted):.1f}x")
    print(f"  the slotted instance has no __dict__ at all : "
          f"{not hasattr(slotted, '__dict__')}")

    print("--- the boxing cost: the same numbers, two representations ---")
    numbers = [10 ** 18 + i for i in range(SMALL)]
    packed = array.array("q", numbers)
    print(f"  list of {SMALL:,} large ints, deep : {deep_size(numbers):,} bytes")
    print(f"  the same values in array('q')     : {sys.getsizeof(packed):,} bytes")
    print(f"  ratio                             : "
          f"{deep_size(numbers) / sys.getsizeof(packed):.1f}x")
    print(f"  one int object costs              : {sys.getsizeof(10 ** 18)} bytes"
          f"   (the value itself is 8 of them)")

    print("--- and why small integers can hide this ---")
    print(f"  0 through 256 are cached and shared, so a list of them looks cheaper")
    print(f"  than a list of the same COUNT of distinct large integers")

    print("--- the rule ---")
    print("  measure deep, not shallow; a container's size is pointers, and the objects")
    print("  behind them are usually the larger half")


if __name__ == "__main__":
    main()
