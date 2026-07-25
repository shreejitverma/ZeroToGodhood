"""Listing 115.2 - super() follows the MRO, not 'the parent'.

The most misunderstood fact about super(): super() does NOT mean 'call my parent
class'. It means 'call the NEXT class in the MRO of type(self), after me'. In a
diamond, that next class depends on the RUNTIME type, not on the static parent
relationship. This is what makes cooperative multiple inheritance work: each class
calls super().method(), and the chain visits every class in the diamond exactly
once, in MRO order, even classes that are 'siblings' not ancestors. This listing
shows the chain visiting L then R (siblings) then Base, driven by the MRO.
"""


class Base:
    def m(self):
        return "Base"


class L(Base):
    def m(self):
        return "L->" + super().m()       # super() = next in MRO after L


class R(Base):
    def m(self):
        return "R->" + super().m()       # super() = next in MRO after R


class LR(L, R):                          # diamond: LR -> L, R -> Base
    def m(self):
        return "LR->" + super().m()


def main() -> None:
    print("--- the MRO of the diamond ---")
    print(f"  LR.__mro__ : {[c.__name__ for c in LR.__mro__]}")

    print("--- super() walks that MRO: LR -> L -> R -> Base ---")
    print(f"  LR().m() : {LR().m()}")

    print("--- the key point: L.super() reaches R, which is L's SIBLING ---")
    print(f"  inside L.m, super() is R (the next in LR's MRO), NOT L's parent Base")
    print(f"  proof: calling m on an L alone skips R entirely ->")
    print(f"  L().m() : {L().m()}   (here super() after L is Base; no R in this MRO)")

    print("--- so super() is runtime-type-dependent, not static-parent ---")
    print(f"  same L.m source, different super() target depending on the MRO it runs in")

    print("--- the rule ---")
    print(f"  super() = the next class in type(self).__mro__ after the current one;")
    print(f"  have every class in a diamond call super().m() for a single clean chain")


if __name__ == "__main__":
    main()
