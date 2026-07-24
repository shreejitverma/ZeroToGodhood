"""Listing 13.1 - @dataclass generates the boilerplate from annotations, as real
compiled functions.

A plain-data class needs __init__, __repr__, __eq__, often ordering and hashing:
dozens of lines that are pure boilerplate and easy to get subtly wrong.
@dataclass reads the class's __annotations__ (Chapter 12) and, at class-
definition time, assembles the SOURCE TEXT of each requested method, compiles and
execs it in the class namespace, and attaches the real function objects. The
generated __init__ is ordinary bytecode running at hand-written speed.
"""

from dataclasses import dataclass, field, FrozenInstanceError, asdict


@dataclass(order=True)
class Point:
    x: int
    y: int = 0
    tags: list = field(default_factory=list)   # fresh [] per instance; see the edges
    def __post_init__(self):
        self.dist = (self.x ** 2 + self.y ** 2) ** 0.5


p = Point(3, 4)
print("--- generated methods ---")
print("  repr        :", repr(p))
print("  eq          :", Point(3, 4, []) == Point(3, 4, []))
print("  order (<)   :", Point(1, 0) < Point(2, 0))
print("  __post_init__:", p.dist)
print("  asdict      :", asdict(Point(1, 2)))


@dataclass(frozen=True)
class Config:
    name: str


print()
print("--- frozen=True generates a raising __setattr__ ---")
c = Config("prod")
try:
    c.name = "dev"
except FrozenInstanceError as exc:
    print("  c.name = 'dev' ->", type(exc).__name__)
print()
print("field(default_factory=list) is the fix for the mutable-default trap: each")
print("instance gets a fresh list. A bare `tags: list = []` in a dataclass is a")
print("hard error precisely because it would share one list across instances.")
