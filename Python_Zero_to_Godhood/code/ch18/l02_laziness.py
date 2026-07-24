"""Listing 18.2 - the value of a type alias is not computed until you ask.

This is the single semantic that justifies the `type` statement existing at
all. Everything else about PEP 695 is ergonomics; this is a change in when
code runs.
"""

# Self-referential, with no quotes, and `Tree` is not yet bound to anything.
type Tree = list[Tree | int]

# Refers to a class that does not exist yet.
type UsesLater = list[DefinedLater]

# Refers to a name that will never exist.
type Broken = list[NeverDefined]

print("--- all three aliases were defined without error ---")
print("no exception raised at definition time")


class DefinedLater:
    pass


print()
print("--- forcing evaluation resolves against the CURRENT module namespace ---")
print("Tree.__value__      =", Tree.__value__)
print("UsesLater.__value__ =", UsesLater.__value__)

print()
print("--- an unresolvable alias fails at access time, not definition time ---")
try:
    Broken.__value__
except NameError as exc:
    print("NameError:", exc)

print()
print("--- the computed value is cached: the lazy scope runs at most once ---")
first, second = Tree.__value__, Tree.__value__
print("Tree.__value__ is Tree.__value__ ->", first is second)

print()
print("--- contrast: the pre-695 idiom needs a string and never self-heals ---")
from typing import TypeAlias, Union  # noqa: E402  (placed here for contrast)

OldTree: TypeAlias = "list[Union[OldTree, int]]"
print("type(OldTree)       =", type(OldTree).__name__)
print("OldTree             =", OldTree)
print("it is a str; resolving it is the type checker's problem, or eval()'s")
