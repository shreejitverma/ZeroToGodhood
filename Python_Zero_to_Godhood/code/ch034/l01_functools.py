"""Listing 34.1 - functools: higher-order helpers for functions.

functools operates ON functions: partial application, reduction, single-dispatch
generic functions, comparison completion, and memoization. (functools.wraps and
lru_cache were Chapter 5; cached_property was Chapter 13; this listing covers the
rest.)
"""

import functools


def add3(a, b, c):
    return a + b + c


print("--- partial: bind some arguments, get a new callable ---")
add_10_20 = functools.partial(add3, 10, 20)
print("  partial(add3, 10, 20)(5):", add_10_20(5))
print("  captured args           :", add_10_20.args)

print()
print("--- reduce: fold a binary function over an iterable ---")
print("  reduce(a*b, 1..5) = 5! :", functools.reduce(lambda a, b: a * b, range(1, 6)))


@functools.singledispatch
def describe(x):
    return f"generic: {x!r}"


@describe.register
def _(x: int):
    return f"int: {x}"


@describe.register
def _(x: list):
    return f"list of {len(x)}"


print()
print("--- singledispatch: one function, type-based implementations ---")
print("  describe(5)      :", describe(5))
print("  describe([1,2,3]):", describe([1, 2, 3]))
print("  describe('hi')   :", describe("hi"), "(falls back to generic)")


@functools.total_ordering
class Version:
    def __init__(self, n):
        self.n = n

    def __eq__(self, other):
        return self.n == other.n

    def __lt__(self, other):
        return self.n < other.n


print()
print("--- total_ordering: define __eq__ and __lt__, get the other four ---")
print("  Version(3) >= Version(2):", Version(3) >= Version(2))
print("  Version(1) >  Version(2):", Version(1) > Version(2))
print("  (>=, >, <=, != were all synthesized from __eq__ and __lt__)")
