"""Listing 108.2 - what breaks when the eq/hash invariant is violated, and is vs ==.

If a == b but hash(a) != hash(b), a dict or set silently loses the object: the
lookup hashes the key to pick a bucket, and the equal-but-differently-hashed key
lands in the WRONG bucket, so the container reports "not found" for something it
contains. This is not an error, it is a wrong answer, the worst kind of bug. This
listing shows the broken lookup, then contrasts identity (is) with equality (==).
"""


def main() -> None:
    print("--- a __hash__ that violates 'equal => same hash' breaks containers ---")
    class Broken:
        def __init__(self, v):
            self.v = v

        def __eq__(self, other):
            return isinstance(other, Broken) and self.v == other.v

        def __hash__(self):
            return id(self)              # WRONG: equal objects get different hashes

    x, y = Broken(1), Broken(1)
    d = {x: "stored under x"}
    print(f"  x == y            : {x == y}   (they are equal)")
    print(f"  hash(x) == hash(y): {hash(x) == hash(y)}   (but hash differently)")
    print(f"  y in d            : {y in d}   (container cannot find the equal key)")
    print(f"  no exception was raised: the wrong answer is returned silently")

    print("--- is compares identity; == compares value ---")
    class Val:
        def __init__(self, v):
            self.v = v

        def __eq__(self, other):
            return isinstance(other, Val) and self.v == other.v

        __hash__ = None                  # (unhashable is fine here; we only test ==)

    m, n = Val(5), Val(5)
    print(f"  m == n (value)   : {m == n}")
    print(f"  m is n (identity): {m is n}")
    print(f"  [] == []         : {[] == []}   (equal contents)")
    print(f"  [] is []         : {[] is []}   (distinct objects)")

    print("--- the rule ---")
    print(f"  equal objects MUST hash equal, or dict/set lose them silently;")
    print(f"  use == to compare values, is only for identity (None, sentinels)")


if __name__ == "__main__":
    main()
