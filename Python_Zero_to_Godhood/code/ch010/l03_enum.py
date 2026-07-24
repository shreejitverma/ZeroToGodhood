"""Listing 10.3 - enum members are singletons, iterable, dual-keyed, and
immutable.

Before 3.4, "enums" were bare module constants (RED = 1): no namespacing, no
type safety, no iteration, no readable repr, and any int compared equal. enum
(PEP 435) provides real enumerations. The EnumMeta metaclass uses a custom
namespace dict during class creation to capture members in order and reject
duplicate names, then replaces each NAME = value with a singleton instance and
installs lookup hooks for name and value.
"""

from enum import Enum, unique


class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3


print("--- iteration, dual-key lookup, singleton identity, immutability ---")
print("  members (declaration order):", [c.name for c in Color])
print("  by name  Color['RED']       :", Color["RED"])
print("  by value Color(2)           :", Color(2))
print("  singleton  Color.RED is Color(1):", Color.RED is Color(1))
try:
    Color.RED.value = 99
except AttributeError as exc:
    print("  Color.RED.value = 99        ->", type(exc).__name__, "(immutable)")

print()
print("--- duplicate VALUES create aliases, not new members ---")


class Status(Enum):
    ACTIVE = 1
    RUNNING = 1        # an alias for ACTIVE, not a new member


print("  Status.RUNNING is Status.ACTIVE:", Status.RUNNING is Status.ACTIVE)
print("  distinct members              :", [s.name for s in Status])

print()
print("--- @unique forbids that when you want distinct values enforced ---")
try:
    @unique
    class MustDiffer(Enum):
        A = 1
        B = 1
except ValueError as exc:
    print("  @unique with duplicate value ->", type(exc).__name__ + ":", str(exc)[:50])
