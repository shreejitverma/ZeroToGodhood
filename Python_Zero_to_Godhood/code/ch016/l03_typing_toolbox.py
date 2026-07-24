"""Listing 16.3 - the 3.8-3.10 typing toolbox, all static contracts over
ordinary runtime objects.

Five additions are now everyday vocabulary: builtin generics (list[int], PEP
585), X | Y unions (PEP 604), TypedDict (PEP 589), Literal (PEP 586), Final
(PEP 591). All are STATIC contracts: a checker enforces them; the runtime sees
ordinary objects.
"""

from typing import TypedDict, Literal, Final


def first(xs: list[int]) -> int:        # PEP 585: no typing.List needed
    return xs[0]


print("--- builtin generics (PEP 585): a GenericAlias, not the bare class ---")
print("  first([10, 20])          :", first([10, 20]))
print("  type(list[int])          :", type(list[int]).__name__)
print("  list[int] is list        :", list[int] is list, "<- erased means NOT the same object")


def parse(x: int | str) -> str:         # PEP 604 union
    return str(x)


print()
print("--- X | Y unions (PEP 604): work in isinstance, unlike old typing.Union ---")
print("  parse(5), parse('z')     :", parse(5), parse("z"))
print("  isinstance(5, int | str) :", isinstance(5, int | str))
print("  isinstance(1.0, int | str):", isinstance(1.0, int | str))


class Movie(TypedDict):
    title: str
    year: int


m: Movie = {"title": "Inception", "year": 2010}
print()
print("--- TypedDict / Literal / Final: static contracts, ordinary runtime objects ---")
print("  TypedDict at runtime is a plain dict:", type(m).__name__, m)


def set_mode(mode: Literal["r", "w"]) -> str:
    return mode


print("  Literal arg              :", set_mode("r"))
MAX: Final = 100
print("  Final (not runtime-enforced):", MAX)

print()
print("--- you cannot isinstance a PARAMETERIZED generic ---")
try:
    isinstance([1], list[int])
except TypeError as exc:
    print("  isinstance([1], list[int]) ->", str(exc))
print("  isinstance([1], list)      :", isinstance([1], list), "(bare class works)")
