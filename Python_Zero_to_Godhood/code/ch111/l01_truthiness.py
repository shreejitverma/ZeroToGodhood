"""Listing 111.1 - truthiness: how bool(x) and 'if x:' decide.

Every object is either truthy or falsy, and bool(x) (which is what 'if x:',
'while x:', 'not x', and boolean operators use) decides by a fixed protocol:
  1. If the type defines __bool__, call it (must return a bool).
  2. Else if it defines __len__, the object is falsy iff len(x) == 0.
  3. Else the object is truthy (the default: every object is true).
So containers are falsy when empty (via __len__) and everything else is true
unless it says otherwise. This listing shows each branch, the __bool__-over-__len__
precedence, and the standard falsy values.
"""


class HasBool:
    def __bool__(self):
        return False                     # explicitly falsy


class HasLen:
    def __init__(self, n):
        self.n = n

    def __len__(self):
        return self.n                    # falsy iff length is 0


class Neither:
    pass                                 # no __bool__, no __len__: always truthy


class Both:
    def __bool__(self):
        return True                      # __bool__ wins...

    def __len__(self):
        return 0                         # ...even though __len__ says falsy


def main() -> None:
    print("--- branch 1: __bool__ decides directly ---")
    print(f"  bool(HasBool()) : {bool(HasBool())}")

    print("--- branch 2: no __bool__, so __len__ decides (falsy iff len == 0) ---")
    print(f"  bool(HasLen(0)) : {bool(HasLen(0))}   bool(HasLen(3)) : {bool(HasLen(3))}")

    print("--- branch 3: neither defined, so the object is always truthy ---")
    print(f"  bool(Neither()) : {bool(Neither())}")

    print("--- __bool__ takes precedence over __len__ ---")
    print(f"  bool(Both()) : {bool(Both())}   (__bool__=True beats __len__=0)")

    print("--- the standard falsy values (all bool() to False) ---")
    falsy = (0, 0.0, "", [], {}, (), set(), None, False, range(0))
    print(f"  0, 0.0, '', [], {{}}, (), set(), None, False, range(0)")
    print(f"  all falsy : {all(not bool(x) for x in falsy)}")

    print("--- the rule ---")
    print(f"  bool(x): __bool__ if defined, else __len__==0 test, else True;")
    print(f"  'if x:' uses this, so define __bool__ or __len__ to be falsy")


if __name__ == "__main__":
    main()
