"""Benchmark 16.1 - typing is erased, but it is not free.

Two claims. First, that @runtime_checkable isinstance is "slow": it is, relative
to a nominal isinstance, and this sizes it. Second, the widespread belief that
annotations have "zero runtime overhead": type CHECKING is free (it happens
outside the interpreter), but annotation EVALUATION at def time is not, and its
cost differs between 3.13 (eager) and 3.14 (PEP 649 lazy).

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

ISINSTANCE_SETUP = """
from typing import Protocol, runtime_checkable
from abc import ABC

@runtime_checkable
class Rendered(Protocol):
    def render(self) -> str: ...

class NominalBase(ABC):
    pass

class Impl(NominalBase):
    def render(self) -> str:
        return "x"

obj = Impl()
"""


def main() -> None:
    isinst = [
        measure("nominal isinstance ", "for _ in range(1000): isinstance(obj, NominalBase)", ISINSTANCE_SETUP, number=1000),
        measure("protocol isinstance", "for _ in range(1000): isinstance(obj, Rendered)", ISINSTANCE_SETUP, number=1000),
    ]
    report("16.1a  @runtime_checkable isinstance vs a nominal one",
           isinst, baseline="nominal isinstance ")

    print()
    defcost = [
        measure("bare def     ", "def f(x): pass", number=100_000),
        measure("annotated def", "def f(x: list[int]) -> dict[str, int]: pass", number=100_000),
    ]
    report("16.1b  annotation EVALUATION cost at def time (version-dependent)",
           defcost, baseline="bare def     ")

    print()
    print("Reading both. 16.1a: a @runtime_checkable isinstance costs roughly")
    print("twice a nominal one, because it goes through the protocol metaclass's")
    print("__instancecheck__ rather than a direct MRO test. Coarse AND slower;")
    print("keep it out of hot loops. 16.1b: an annotated def is several times a")
    print("bare one, because the annotations are objects the def statement builds.")
    print("This is why 'annotations have zero runtime overhead' is wrong: type")
    print("CHECKING is free, annotation EVALUATION is not. On 3.14, PEP 649 makes")
    print("annotations lazy and cuts this cost (about 3.5x vs 3.13's 5.4x), but")
    print("does not zero it: the __annotate__ function is still built.")


if __name__ == "__main__":
    main()
