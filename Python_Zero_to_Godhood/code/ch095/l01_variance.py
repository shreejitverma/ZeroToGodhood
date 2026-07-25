"""Listing 95.1 - variance: why list is invariant, and to accept Iterable.

Variance decides when a container of a subtype can stand in for a container of a
supertype. A MUTABLE list is INVARIANT: list[Dog] is NOT a list[Animal], because
if it were, you could append a plain Animal through the Animal view and then read
a non-Dog where a Dog is expected, an unsound write. A READ-ONLY container is
COVARIANT: a tuple[Dog] or Sequence[Dog] CAN be used as tuple[Animal]/
Sequence[Animal], because you cannot write to it, so nothing unsound can happen.
The practical payoff: type a parameter you only READ as a general read-only type
(Iterable/Sequence), so callers can pass anything without converting. This listing
shows the flexibility and, at runtime, the unsound write invariance prevents.
"""

from typing import Iterable


class Animal:
    pass


class Dog(Animal):
    def bark(self) -> str:
        return "woof"


def total(xs: Iterable[int]) -> int:      # accepts ANY iterable (covariant read)
    return sum(xs)


def main() -> None:
    print("--- an Iterable parameter accepts any iterable, no conversion ---")
    print(f"  total([1, 2, 3])            : {total([1, 2, 3])}")
    print(f"  total((4, 5))               : {total((4, 5))}")
    print(f"  total(i for i in range(3))  : {total(i for i in range(3))}")
    print(f"  (a list[int] parameter would force callers to convert first)")

    print("--- why a MUTABLE list is invariant: the unsound write it prevents ---")
    dogs = [Dog()]
    aliased_as_animals = dogs           # imagine list[Dog] used as list[Animal] (unsound)
    aliased_as_animals.append(Animal())  # append a non-Dog through the Animal view
    print(f"  after appending an Animal, the 'list of Dogs' has : {[type(x).__name__ for x in dogs]}")
    try:
        dogs[1].bark()                  # read it back as a Dog: it is not one
        broke = False
    except AttributeError:
        broke = True
    print(f"  calling .bark() on the non-Dog raises AttributeError : {broke}")
    print(f"  the checker forbids list[Dog] as list[Animal] to prevent exactly this")

    print("--- a READ-ONLY tuple/Sequence is covariant (safe, no writes) ---")
    dog_tuple: tuple[Dog, ...] = (Dog(),)
    print(f"  tuple[Dog] usable as tuple[Animal] (read-only, no unsound write) : True")
    print(f"  its element barks: {dog_tuple[0].bark()!r}")

    print("--- the rule ---")
    print(f"  mutable containers: invariant. read-only containers: covariant.")
    print(f"  type a read-only parameter as Iterable/Sequence, return a concrete list")


if __name__ == "__main__":
    main()
