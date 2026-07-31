"""Listing 221.1 - Python 2.0 (2000): augmented assignment, and its two faces.

Python 2.0 added augmented assignment: x += 1 for x = x + 1. Convenient, and
for immutable types purely sugar. But for MUTABLE types it exposes a subtlety
that is one of Python's most instructive gotchas: `a += b` on a list mutates
IN PLACE (calls __iadd__), while `a = a + b` builds a NEW list. Same-looking
syntax, different object identity, and the difference bites when the list is
shared. This listing demonstrates both faces on current interpreters - the
convenience and the trap - because understanding += is understanding the line
between mutation and rebinding (Chapter 4's object model, in daily code).
"""


def main() -> None:
    print("--- for immutable types, += is pure sugar (new object) ---")
    x = 10
    before = id(x)
    x += 5
    print(f"  int x += 5 : value {x}, new object : {id(x) != before}")
    s = "ab"
    before = id(s)
    s += "cd"
    print(f"  str s += 'cd' : value {s!r}, new object : {id(s) != before}")
    print("  immutable objects cannot change, so += REBINDS to a new object -")
    print("  identical to x = x + 5. no surprise here")

    print("--- for mutable types, += mutates IN PLACE (same object) ---")
    a = [1, 2]
    before = id(a)
    a += [3, 4]
    print(f"  list a += [3,4] : {a}, SAME object : {id(a) == before}")
    b = [1, 2]
    before = id(b)
    b = b + [3, 4]
    print(f"  list b = b+[3,4]: {b}, NEW object  : {id(b) != before}")
    print("  a += b calls list.__iadd__ (in-place extend); a = a+b builds a")
    print("  NEW list. same result value, DIFFERENT object identity - and")
    print("  that difference is the whole gotcha")

    print("--- the trap: += through a shared reference ---")
    shared = [1, 2]
    alias = shared                               # alias points at the SAME list
    shared += [3]                                # mutates in place...
    print(f"  after shared += [3]: shared={shared}, alias={alias}")
    print(f"  the alias sees the change : {alias == [1, 2, 3]}")
    other = [1, 2]
    other_alias = other
    other = other + [3]                          # rebinds 'other' only
    print(f"  after other = other+[3]: other={other}, other_alias="
          f"{other_alias}")
    print(f"  the alias does NOT see it  : {other_alias == [1, 2]}")
    print("  += mutates the shared object (every alias sees it); = + rebinds")
    print("  the name (aliases keep the old object). this is Chapter 4's")
    print("  names-vs-objects distinction, in the code you write every day")

    print("--- the tuple-of-list trap: += that both works AND raises ---")
    t = ([1, 2],)                                # a tuple holding a list
    try:
        t[0] += [3]                              # mutates the list AND reassigns
    except TypeError as exc:
        print(f"  t[0] += [3] raised {type(exc).__name__}...")
    print(f"  ...but the list WAS mutated anyway : {t[0]}")
    print("  the famous gotcha: += on a list inside a tuple mutates the list")
    print("  (in-place succeeds) then tries to reassign t[0] (tuple item")
    print("  assignment fails). the operation half-completes - proof that +=")
    print("  is mutate-THEN-rebind, and the two steps can disagree")

    print("--- the constraint answered, and the lesson ---")
    print("  2.0 added += for convenience; it exposed the mutation-vs-rebinding")
    print("  line that was always there (Chapter 4). the lesson is not 'avoid")
    print("  +=' but 'know whether your object is mutable' - because += means")
    print("  DIFFERENT things for the two kinds, and the difference is identity")


if __name__ == "__main__":
    main()
