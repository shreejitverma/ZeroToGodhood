"""Listing 284.1 - Python 3.13 (2024): copy.replace(), a generic 'copy with changes'.

Working with immutable objects means you never mutate - you make a NEW object that
differs in a few fields. dataclasses had dataclasses.replace() for this, and
namedtuples had ._replace(), and datetime had .replace() - each its own spelling
of the same idea, and custom immutable types had none. Python 3.13's copy.replace()
plus the __replace__ protocol unify it: copy.replace(obj, field=value) returns a
copy of obj with those fields changed, for ANY type that implements __replace__ -
and dataclasses and datetime got it automatically. Deep volumes own no copy
mechanism; this is the release that gave 'copy but change these fields' one
standard function across types. Verified on current interpreters.
"""

import copy
import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    debug: bool = False


class Money:
    """A custom immutable type that opts in with __replace__."""
    def __init__(self, amount, currency):
        self._amount = amount
        self._currency = currency

    def __replace__(self, /, **changes):
        return Money(changes.get("amount", self._amount),
                     changes.get("currency", self._currency))

    def __repr__(self):
        return f"Money({self._amount}, {self._currency!r})"


def main() -> None:
    print("--- copy.replace() returns a NEW object with some fields changed ---")
    base = Config(host="localhost", port=8000)
    prod = copy.replace(base, host="prod.example.com", port=443)
    print(f"  base : {base}")
    print(f"  prod : {prod}")
    print(f"  base is unchanged : {base.host == 'localhost'}")
    print("  copy.replace(base, host=..., port=...) built a NEW Config with those")
    print("  fields overridden and the rest copied. the original is untouched -")
    print("  the functional-update pattern immutable code lives on")

    print("--- unspecified fields are carried over unchanged ---")
    debug_variant = copy.replace(base, debug=True)
    print(f"  copy.replace(base, debug=True) : {debug_variant}")
    print(f"  host and port copied from base : "
          f"{(debug_variant.host, debug_variant.port) == (base.host, base.port)}")
    print("  you name only what changes; everything else is inherited from the")
    print("  original. that is what makes it ergonomic for objects with many")
    print("  fields where you want to tweak one")

    print("--- it works on datetime, which grew __replace__ ---")
    d = datetime.date(2024, 1, 15)
    moved = copy.replace(d, year=2025)
    print(f"  date 2024-01-15 with year=2025 : {moved}")
    print("  datetime.date already had a .replace() method; in 3.13 it also")
    print("  supports copy.replace(), so the same generic function works on it -")
    print("  the point of a unifying protocol")

    print("--- custom types opt in by defining __replace__ ---")
    price = Money(100, "USD")
    discounted = copy.replace(price, amount=80)
    converted = copy.replace(price, amount=92, currency="EUR")
    print(f"  original  : {price}")
    print(f"  amount=80 : {discounted}")
    print(f"  to EUR    : {converted}")
    print("  Money defined __replace__(self, **changes) returning a new Money.")
    print("  now copy.replace() works on it exactly like on a dataclass - any")
    print("  immutable type joins the protocol by implementing one method")

    print("--- the standard-across-types payoff ---")
    print("  dataclasses.replace(cfg, ...), nt._replace(...), dt.replace(...) were")
    print("  three different spellings. copy.replace(obj, ...) is ONE, dispatching")
    print("  through __replace__ - so generic code can 'copy-with-changes' any")
    print("  supporting object without knowing which kind it is")

    print("--- the constraint answered ---")
    print("  immutable-object updates needed a per-type replace method with a")
    print("  different name for each type, and no story for custom classes.")
    print("  copy.replace() + __replace__ (3.13) unified it: one function that")
    print("  copies an object with named fields changed, for dataclasses,")
    print("  datetime, and any type that opts in. functional update, standardised")


if __name__ == "__main__":
    main()
