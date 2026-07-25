"""Listing 105.3 - implicit special-method lookup bypasses __getattribute__.

Because the interpreter reads the slot on the type directly (Listing 105.2), an
implicit special-method call (len(x), x + y, iter(x)) does NOT go through the
normal attribute machinery: it skips __getattribute__ and the instance __dict__
entirely. An EXPLICIT call (x.__len__()) is an ordinary attribute access and does
go through __getattribute__. This listing makes the difference audible: a class
whose __getattribute__ prints, called both ways.
"""


class Loud:
    def __getattribute__(self, name):
        print(f"    __getattribute__ intercepted: {name!r}")
        return object.__getattribute__(self, name)

    def __len__(self):
        return 3


def main() -> None:
    lo = Loud()

    print("--- EXPLICIT lo.__len__(): ordinary attribute access ---")
    n = lo.__len__()
    print(f"  result: {n}   (__getattribute__ WAS called above)")

    print("--- IMPLICIT len(lo): slot dispatch on the type ---")
    n = len(lo)
    print(f"  result: {n}   (no __getattribute__ line above: it was bypassed)")

    print("--- the rule ---")
    print(f"  implicit dunder dispatch reads the type slot directly, skipping")
    print(f"  __getattribute__ and the instance dict; explicit access does not")


if __name__ == "__main__":
    main()
