"""Listing 105.4 - operator dispatch and the NotImplemented fallback.

An operator is not a synonym for one dunder call. x + y runs a PROTOCOL: try
type(x).__add__(x, y); if that returns the NotImplemented sentinel (meaning "I
do not know how to add these"), try the REFLECTED method type(y).__radd__(y, x).
Only if both decline does Python raise TypeError. This two-sided fallback is what
lets a new type on the RIGHT of + cooperate with a builtin on the left. This
listing shows each step: the sentinel, the reflected call, and the failure.
"""


def main() -> None:
    print("--- a dunder can decline by returning NotImplemented ---")
    print(f"  (1).__add__('x') : {(1).__add__('x')!r}   (int cannot add a str)")
    print(f"  it is a sentinel, not an error: type = {type((1).__add__('x')).__name__}")

    print("--- the operator uses that to try the OTHER operand's reflected op ---")
    class R:
        def __radd__(self, other):
            return f"R.__radd__({other!r})"
    print(f"  1 + R() : {1 + R()!r}")
    print(f"  int.__add__(1, R()) returned NotImplemented, so Python tried R.__radd__")

    print("--- left operand's __add__ wins when it does NOT decline ---")
    class L:
        def __add__(self, other):
            return "L.__add__"
    print(f"  L() + 1 : {L() + 1!r}   (L.__add__ handled it; no fallback)")

    print("--- when both decline, THEN TypeError ---")
    try:
        object() + object()
    except TypeError as e:
        print(f"  object() + object() -> TypeError : {e}")

    print("--- the rule ---")
    print(f"  x + y = try type(x).__add__; on NotImplemented try type(y).__radd__;")
    print(f"  if both decline, TypeError. The operator is a protocol, not one call")


if __name__ == "__main__":
    main()
