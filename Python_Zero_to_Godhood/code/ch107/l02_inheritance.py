"""Listing 107.2 - __slots__ and inheritance: how the saving is kept or lost.

__slots__ constrains only the class that declares it. If a subclass does NOT
declare __slots__, its instances get a __dict__ back, and both the memory saving
and the attribute lock are LOST for that subclass. To keep the block through a
subclass that adds no fields, declare __slots__ = (). To add fields, declare only
the NEW ones (slots are inherited; repeating a base slot wastes space). This
listing shows each case.
"""


class Base:
    __slots__ = ("a",)


class SubNoSlots(Base):              # forgot __slots__: __dict__ comes back
    pass


class SubEmpty(Base):                # __slots__ = () keeps the block, adds nothing
    __slots__ = ()


class SubMore(Base):                 # adds one NEW slot; 'a' is inherited
    __slots__ = ("b",)


def main() -> None:
    print("--- a subclass WITHOUT __slots__ regains a __dict__ (saving defeated) ---")
    sn = SubNoSlots()
    print(f"  SubNoSlots has __dict__ : {hasattr(sn, '__dict__')}")
    sn.anything = 1                  # arbitrary attributes allowed again
    print(f"  sn.anything = 1 works   : {sn.anything}")

    print("--- __slots__ = () keeps the block through a field-less subclass ---")
    se = SubEmpty()
    print(f"  SubEmpty has __dict__   : {hasattr(se, '__dict__')}")
    try:
        se.x = 1
    except AttributeError:
        print(f"  se.x = 1 -> AttributeError (still locked)")

    print("--- add only NEW slots; inherited ones still work ---")
    sm = SubMore()
    sm.a, sm.b = 10, 20              # 'a' inherited from Base, 'b' new
    print(f"  SubMore has __dict__    : {hasattr(sm, '__dict__')}")
    print(f"  sm.a (inherited), sm.b (new) : {sm.a}, {sm.b}")

    print("--- the rule ---")
    print(f"  slots bind only the declaring class; a subclass without __slots__")
    print(f"  restores __dict__. Use __slots__ = () to keep the block, add only new")


if __name__ == "__main__":
    main()
