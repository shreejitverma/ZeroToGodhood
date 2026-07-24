"""Listing 4.4 - C3 linearization: a single consistent order, or a TypeError.

C3 gives multiple inheritance a total order over the ancestors with two
guarantees: local precedence (bases appear in declared order) and monotonicity
(if X precedes Y in one MRO, X precedes Y in every subclass's MRO). When the
constraints contradict, there is no such order and CPython refuses to build the
class.
"""

print("--- the simple diamond: O <- {X, Y} <- A ---")


class O:
    pass


class X(O):
    pass


class Y(O):
    pass


class A(X, Y):
    pass


print("  A.__mro__:", [c.__name__ for c in A.__mro__])

print()
print("--- Pedroni's monotonicity stress test ---")


class Ao: pass
class Bo: pass
class Co: pass
class Do: pass
class Eo: pass
class K1(Ao, Bo, Co): pass
class K2(Do, Bo, Eo): pass
class K3(Do, Ao): pass
class Z(K1, K2, K3): pass


print("  Z.__mro__:", [c.__name__ for c in Z.__mro__])
print("  matches the hand computation [Z,K1,K2,K3,D,A,B,C,E,object].")

print()
print("--- an impossible hierarchy is rejected at class-creation time ---")
try:
    class Bad1: pass
    class Bad2(Bad1): pass
    class Bad3(Bad1, Bad2): pass     # demands Bad1 before AND after Bad2
except TypeError as exc:
    print("  TypeError:", exc)
