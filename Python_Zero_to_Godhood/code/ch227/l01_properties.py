"""Listing 227.1 - Python 2.2 (2001): properties, computed attributes that keep the interface.

A classic OO problem: you expose obj.price as a plain attribute, code everywhere
does obj.price, then you need price to be VALIDATED or COMPUTED. In Java you'd
have written getPrice()/setPrice() from the start (ugly) to keep the option
open. Python 2.2's `property` (built on the new-style-class descriptor protocol)
lets a plain attribute BECOME a computed one with NO change to the calling code:
obj.price still reads as obj.price, but now runs a method. This is why Python
code uses public attributes freely - you can always add a property later. Deep C
owns the descriptor mechanism; this is the release that made 'attributes you can
upgrade' the norm. Verified on current interpreters.
"""


class Order:
    def __init__(self, qty, unit_price):
        self.qty = qty
        self._unit_price = unit_price            # 'private' by convention

    @property
    def total(self):                             # a COMPUTED attribute
        return self.qty * self._unit_price

    @property
    def unit_price(self):
        return self._unit_price

    @unit_price.setter
    def unit_price(self, value):                 # a VALIDATED attribute
        if value < 0:
            raise ValueError("price cannot be negative")
        self._unit_price = value


def main() -> None:
    print("--- a property reads like a plain attribute but runs a method ---")
    o = Order(qty=10, unit_price=5)
    print(f"  o.total is accessed like an attribute : {o.total}")
    print(f"  but it is COMPUTED (10 * 5), not stored : {o.total == 10 * 5}")
    o.qty = 20
    print(f"  change qty, total recomputes on read    : {o.total}")
    print("  o.total has no parentheses - it reads as an attribute - yet runs")
    print("  a method each access. the CALLER cannot tell it from a stored")
    print("  field, which is the whole point")

    print("--- a setter adds validation without changing the interface ---")
    print(f"  o.unit_price reads normally : {o.unit_price}")
    o.unit_price = 7                             # assignment runs the setter
    print(f"  o.unit_price = 7 (via setter): {o.unit_price}")
    try:
        o.unit_price = -1                        # setter validates
    except ValueError as exc:
        print(f"  o.unit_price = -1 rejected  : ValueError({exc})")
    print("  assignment (o.unit_price = 7) runs the setter method - so you can")
    print("  validate, log, or convert on assignment, and the caller still")
    print("  writes plain 'o.unit_price = 7'. the interface never changed")

    print("--- the payoff: start with a plain attribute, upgrade later ---")
    class V1:
        def __init__(self, x):
            self.value = x                       # plain public attribute

    class V2:
        def __init__(self, x):
            self._value = x

        @property
        def value(self):                         # SAME interface, now computed
            return self._value * 2               # (validation/logging/etc.)

    print(f"  V1().value (plain field)   : {V1(21).value}")
    print(f"  V2().value (now a property): {V2(21).value}")
    print("  code doing obj.value works UNCHANGED on both - the plain field")
    print("  became a property with zero caller impact. this is why Python")
    print("  exposes public attributes: you never lose the option to add")
    print("  behaviour, so getters/setters up front (Java-style) are needless")

    print("--- properties are descriptors on the CLASS, not the instance ---")
    print(f"  Order.total is a property object : "
          f"{type(Order.total).__name__}")
    print(f"  the instance has no 'total' in its dict : "
          f"{'total' not in Order(1, 1).__dict__}")
    print("  a property lives on the CLASS as a descriptor (Deep C); accessing")
    print("  it on an instance triggers __get__/__set__. that is the mechanism")
    print("  behind the 'looks like an attribute, runs a method' magic")

    print("--- the constraint answered ---")
    print("  new-style classes (2.2) brought the descriptor protocol, and")
    print("  property is its friendliest use: it lets a public attribute gain")
    print("  computation or validation with no interface change. that removed")
    print("  the reason to write getters/setters defensively, and made 'just")
    print("  use a public attribute' the correct Python default")


if __name__ == "__main__":
    main()
