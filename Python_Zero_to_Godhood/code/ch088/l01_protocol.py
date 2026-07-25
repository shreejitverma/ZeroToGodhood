"""Listing 88.1 - Protocol (structural) vs ABC (nominal), and the isinstance gap.

A Protocol types by SHAPE: any class with the right methods matches, no
inheritance needed, duck typing made checkable, and it works on classes you do
not own (a third-party File, a stdlib object). An ABC types by LINEAGE: a class
matches only if it inherits from (or is registered with) the ABC. The catch with
Protocol: a runtime_checkable isinstance check verifies method NAMES are present,
NOT their signatures or return types, so a class with a same-named but
wrong-signature method passes isinstance and then fails when actually called. A
static checker verifies the full signature; runtime_checkable does not. This
listing shows both, and the gap.
"""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class Closeable(Protocol):
    def close(self) -> None: ...


class RealFile:
    def close(self):
        pass


class WrongClose:
    def close(self, mode, extra):   # same NAME, wrong signature
        pass


class CloseableABC(ABC):
    @abstractmethod
    def close(self) -> None: ...


class FileABC(CloseableABC):        # explicitly inherits
    def close(self):
        pass


class HasCloseNoInherit:
    def close(self):
        pass


def main() -> None:
    print("--- Protocol: structural, matches by shape (no inheritance) ---")
    print(f"  RealFile is Closeable          : {isinstance(RealFile(), Closeable)}")
    print(f"  (RealFile does not inherit anything: it just HAS close())")

    print("--- the gap: runtime_checkable checks NAMES, not signatures ---")
    print(f"  WrongClose is Closeable        : {isinstance(WrongClose(), Closeable)}")
    print(f"  (its close(self, mode, extra) has the wrong signature, yet passes!)")

    print("--- ABC: nominal, matches only by inheritance/registration ---")
    print(f"  FileABC is CloseableABC        : {isinstance(FileABC(), CloseableABC)}")
    print(f"  HasCloseNoInherit is CloseableABC : {isinstance(HasCloseNoInherit(), CloseableABC)}")
    print(f"  (has close() but does not inherit: does NOT match)")

    print("--- the rule ---")
    print(f"  Protocol: structural typing for shapes/duck typing (incl. classes you")
    print(f"            do not own); rely on a static checker for signature safety")
    print(f"  ABC: nominal, explicit opt-in via inheritance (no name-collision false hits)")


if __name__ == "__main__":
    main()
