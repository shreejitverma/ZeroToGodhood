"""Listing 115.1 - the method resolution order (MRO) and C3 linearization.

With multiple inheritance, which base provides an inherited attribute? Python
answers with the MRO: a single linear ordering of a class and all its ancestors,
computed by the C3 linearization algorithm. C3 guarantees:
  - a class appears before all its bases (children before parents), and
  - the relative order of bases is preserved (local precedence), and
  - the order is monotonic (a subclass's MRO is consistent with its bases').
Attribute lookup walks the MRO left to right and takes the FIRST match. If no
consistent order exists, the class cannot be created. This listing shows the
classic diamond and a hierarchy C3 rejects.
"""


class A:
    def who(self):
        return "A"


class B(A):
    def who(self):
        return "B"


class C(A):
    def who(self):
        return "C"


class D(B, C):                           # diamond: D -> B, C -> A
    pass


def main() -> None:
    print("--- the diamond's MRO (C3 linearization) ---")
    print(f"  D.__mro__ : {[c.__name__ for c in D.__mro__]}")

    print("--- lookup walks the MRO and takes the first match ---")
    print(f"  D().who() : {D().who()}   (B: first in the MRO to define who, not A)")

    print("--- C3 preserves local precedence: B before C because D(B, C) ---")
    print(f"  D lists bases (B, C), so B precedes C in the MRO")

    print("--- an INCONSISTENT hierarchy cannot be linearized: TypeError ---")
    class X:
        pass

    class Y(X):
        pass

    try:
        # X before Y contradicts Y(X) requiring Y before X: no consistent order
        class Bad(X, Y):
            pass
    except TypeError as e:
        print(f"  class Bad(X, Y) -> TypeError (inconsistent MRO): "
              f"{'consistent method resolution' in str(e)}")

    print("--- the rule ---")
    print(f"  the MRO is one linear order of a class and its ancestors (C3);")
    print(f"  lookup takes the first match; inconsistent hierarchies are rejected")


if __name__ == "__main__":
    main()
