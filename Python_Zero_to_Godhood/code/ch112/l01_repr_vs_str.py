"""Listing 112.1 - __repr__ vs __str__: two string forms, two audiences.

An object has two string representations, and the object model keeps them distinct:
  - __repr__ is the UNAMBIGUOUS, developer-facing form. repr(x) uses it. Ideally
    it is valid Python that would recreate the object (eval(repr(x)) == x). It is
    what the REPL echoes and what CONTAINERS use for their elements.
  - __str__ is the READABLE, user-facing form. str(x) and print(x) use it.
If __str__ is not defined, it FALLS BACK to __repr__. If neither is defined, the
default __repr__ is <Module.Class object at 0x...>. This listing shows each.
"""


class Both:
    def __repr__(self):
        return "Both(unambiguous)"       # dev-facing

    def __str__(self):
        return "a readable Both"         # user-facing


class OnlyRepr:
    def __repr__(self):
        return "OnlyRepr(unambiguous)"   # __str__ will fall back to this


def main() -> None:
    b, o = Both(), OnlyRepr()

    print("--- repr() is dev-facing; str() is user-facing ---")
    print(f"  repr(b) : {repr(b)}")
    print(f"  str(b)  : {str(b)}")

    print("--- __str__ falls back to __repr__ when not defined ---")
    print(f"  repr(o) : {repr(o)}")
    print(f"  str(o)  : {str(o)}   (fell back to __repr__)")

    print("--- containers use __repr__ of their elements, even via str() ---")
    print(f"  str([b, b]) : {str([b, b])}   (list shows repr, not str)")

    print("--- print() uses str(); the values differ ---")
    print(f"  print(b) shows : ", end="")
    print(b)

    print("--- with neither defined, the default __repr__ has a stable shape ---")
    class Plain:
        pass
    r = repr(Plain())
    print(f"  starts with '<' : {r.startswith('<')}")
    print(f"  contains 'Plain object at 0x' : {'Plain object at 0x' in r}")

    print("--- the rule ---")
    print(f"  define __repr__ always (unambiguous, for devs/logs/containers);")
    print(f"  define __str__ only when users need a different, readable form")


if __name__ == "__main__":
    main()
