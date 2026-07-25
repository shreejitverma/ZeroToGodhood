"""Listing 107.1 - __slots__: no per-instance __dict__, fixed attributes, descriptors.

By default an instance stores attributes in a __dict__ (Chapter 21). Declaring
__slots__ = (...) on a class replaces that dict with a FIXED set of slots: the
named attributes are stored in a compact C-level layout, the instance has NO
__dict__, and assigning any name NOT in __slots__ raises AttributeError. Each slot
is exposed as a MEMBER DESCRIPTOR on the class (a data descriptor, Chapter 21's
rank 1). This listing shows the missing dict, the blocked attribute, and the
descriptors.
"""


class WithDict:
    def __init__(self, a, b):
        self.a, self.b = a, b


class WithSlots:
    __slots__ = ("a", "b")           # fixed attribute set; no __dict__

    def __init__(self, a, b):
        self.a, self.b = a, b


def main() -> None:
    wd = WithDict(1, 2)
    ws = WithSlots(1, 2)

    print("--- a normal instance has a __dict__; a slotted one does not ---")
    print(f"  WithDict  has __dict__ : {hasattr(wd, '__dict__')}")
    print(f"  WithSlots has __dict__ : {hasattr(ws, '__dict__')}")

    print("--- both store their declared attributes the same way to read ---")
    print(f"  wd.a, wd.b : {wd.a}, {wd.b}")
    print(f"  ws.a, ws.b : {ws.a}, {ws.b}")

    print("--- but a slotted instance REJECTS any undeclared attribute ---")
    try:
        ws.c = 3
    except AttributeError as e:
        print(f"  ws.c = 3 -> AttributeError : {e}")
    print(f"  wd.c = 3 (normal instance) : ", end="")
    wd.c = 3
    print(f"allowed -> {wd.c}")

    print("--- each slot is a member_descriptor (a data descriptor) on the class ---")
    print(f"  type(WithSlots.a) : {type(WithSlots.__dict__['a']).__name__}")

    print("--- the rule ---")
    print(f"  __slots__ replaces the instance __dict__ with fixed slot descriptors:")
    print(f"  smaller objects, a locked attribute set, no arbitrary assignment")


if __name__ == "__main__":
    main()
