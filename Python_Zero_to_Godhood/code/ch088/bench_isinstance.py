"""Benchmark 88.1 - a structural isinstance costs more than a nominal one.

isinstance against a runtime_checkable Protocol is STRUCTURAL: it checks that the
object has each of the Protocol's methods (a getattr/hasattr per method). isinstance
against an ABC is NOMINAL: it walks the class's MRO (and __subclasshook__). So the
Protocol check does more work, proportional to the number of methods, than the ABC
check. This measures both, so the cost of structural checking is visible, and it is
paid on top of the check being SHALLOWER (names only, no signatures).

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
from typing import Protocol, runtime_checkable
from abc import ABC, abstractmethod

@runtime_checkable
class P(Protocol):
    def a(self): ...
    def b(self): ...
    def c(self): ...

class ImplP:
    def a(self): pass
    def b(self): pass
    def c(self): pass

class Base(ABC):
    @abstractmethod
    def a(self): ...

class ImplABC(Base):
    def a(self): pass

p = ImplP()
ab = ImplABC()
"""


def main() -> None:
    results = [
        measure("isinstance(x, ABC) (nominal)", "isinstance(ab, Base)", SETUP, number=500000),
        measure("isinstance(x, Protocol) (structural)", "isinstance(p, P)", SETUP, number=500000),
    ]
    report("88.1  structural (Protocol) vs nominal (ABC) isinstance",
           results, baseline="isinstance(x, ABC) (nominal)")

    print()
    print("Reading this. The ABC check is a nominal MRO walk; the Protocol check is")
    print("structural, it verifies each of the Protocol's methods is present, so it")
    print("costs more (and more as the Protocol grows). Worse, that extra work only")
    print("checks method NAMES, not signatures, so it can pass a class that would")
    print("fail when called (Listing 88.1). So a runtime_checkable Protocol isinstance")
    print("is both slower AND weaker than it looks. Use Protocols for STATIC")
    print("structural typing (where a checker verifies signatures for free); use")
    print("runtime_checkable isinstance sparingly, and never treat it as proof the")
    print("object's methods have the right signatures.")


if __name__ == "__main__":
    main()
