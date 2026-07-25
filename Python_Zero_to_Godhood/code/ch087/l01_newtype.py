"""Listing 87.1 - NewType: a statically distinct type at zero runtime cost.

Many bugs come from mixing up values that share an underlying type: a UserId and
an OrderId are both int, so nothing stops you passing one where the other is
expected. NewType('UserId', int) creates a type that a STATIC checker treats as
distinct from int (and from OrderId), catching the mix-up, while at RUNTIME a
UserId simply IS an int: NewType is essentially the identity function, so
UserId(42) returns the int 42 unchanged, with no wrapper object and no memory
overhead. It exploits type erasure (Chapter 86) deliberately: the distinction
exists only for the type checker. This listing shows the runtime identity; the
benchmark shows it is far cheaper than a real wrapper class.
"""

from typing import NewType

UserId = NewType("UserId", int)
OrderId = NewType("OrderId", int)


def main() -> None:
    uid = UserId(42)

    print("--- at runtime, a UserId IS just an int ---")
    print(f"  UserId(42)            : {uid!r}")
    print(f"  type(UserId(42))      : {type(uid).__name__}")
    print(f"  isinstance(uid, int)  : {isinstance(uid, int)}")
    print(f"  uid == 42             : {uid == 42}")
    print(f"  no wrapper: same object as the int : {uid == int(42)}")

    print("--- the distinction is STATIC only ---")
    oid = OrderId(42)
    print(f"  UserId(42) == OrderId(42) at runtime : {uid == oid}  (both are int 42)")
    print(f"  but a static checker rejects passing an OrderId where a UserId is wanted")
    print(f"  (mypy/pyright flag it; the runtime does not)")

    print("--- the rule ---")
    print(f"  NewType: static distinctness for same-underlying-type values")
    print(f"           (UserId vs OrderId, both int), at zero runtime cost")
    print(f"  a wrapper class: runtime distinctness + methods/validation, but costs")


if __name__ == "__main__":
    main()
