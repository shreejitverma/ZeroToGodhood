"""Listing 114.1 - property: a data descriptor for computed and validated attributes.

property is the descriptor protocol (Chapter 32) packaged for the common case:
turn a method into an attribute. It is a DATA descriptor, so it cannot be shadowed
by an instance attribute. Its three optional parts:
  @property            the getter (read)
  @<name>.setter       the setter (assignment; the place for validation)
  @<name>.deleter      the deleter
A property with a getter but no setter is READ-ONLY (assignment raises). This
listing shows a validated setter, a computed read-only property, and the read-only
enforcement, all via attribute syntax (t.celsius), no method calls at the call site.
"""


class Temperature:
    def __init__(self, celsius):
        self._celsius = celsius          # the stored value (private by convention)

    @property
    def celsius(self):
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        if value < -273.15:              # validation lives in the setter
            raise ValueError("below absolute zero")
        self._celsius = value

    @property
    def fahrenheit(self):                # computed, read-only (no setter)
        return self._celsius * 9 / 5 + 32


def main() -> None:
    t = Temperature(20)

    print("--- read via getter, both real and computed ---")
    print(f"  t.celsius    : {t.celsius}")
    print(f"  t.fahrenheit : {t.fahrenheit}   (computed from celsius)")

    print("--- assign via setter; the computed one follows ---")
    t.celsius = 25
    print(f"  after t.celsius = 25, t.fahrenheit : {t.fahrenheit}")

    print("--- the setter validates ---")
    try:
        t.celsius = -300
    except ValueError as e:
        print(f"  t.celsius = -300 -> ValueError : {e}")

    print("--- a getter-only property is READ-ONLY ---")
    try:
        t.fahrenheit = 100
    except AttributeError as e:
        print(f"  t.fahrenheit = 100 -> AttributeError (no setter): {'no setter' in str(e)}")

    print("--- property is a DATA descriptor (has __set__) ---")
    print(f"  hasattr(Temperature.__dict__['celsius'], '__set__') : "
          f"{hasattr(Temperature.__dict__['celsius'], '__set__')}")

    print("--- the rule ---")
    print(f"  @property turns methods into attributes: getter/setter/deleter, with")
    print(f"  validation in the setter; getter-only is read-only")


if __name__ == "__main__":
    main()
