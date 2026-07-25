"""Benchmark 95.1 - demanding a concrete list forces callers to convert.

The practical payoff of variance: a parameter you only READ should be typed as a
general read-only type (Iterable/Sequence), which is covariant and accepts any
iterable, so a caller with a generator passes it directly. A parameter typed as a
concrete list[int] (invariant) forces a caller with a generator to convert with
list(...), allocating the whole thing. This measures summing a generator through an
Iterable parameter (no conversion) versus a list parameter (forced list()).

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
from typing import Iterable

def total_iterable(xs: Iterable[int]) -> int:
    return sum(xs)

def total_list(xs: list[int]) -> int:
    return sum(xs)

def make_gen():
    return (i for i in range(1000))
"""


def main() -> None:
    results = [
        measure("Iterable param (pass generator)", "total_iterable(make_gen())", SETUP, number=20000),
        measure("list param (list(gen) first)", "total_list(list(make_gen()))", SETUP, number=20000),
    ]
    report("95.1  summing a generator: Iterable parameter vs list parameter",
           results, baseline="Iterable param (pass generator)")

    print()
    print("Reading this. The Iterable parameter accepts the generator directly and")
    print("streams it; the list parameter forces the caller to materialize the whole")
    print("generator with list() first, allocating an O(n) list before the call. So")
    print("it costs more time AND O(n) memory the streaming path avoids. Because a")
    print("read-only view is covariant, typing a read-only parameter as Iterable or")
    print("Sequence (not the concrete list/dict) lets callers pass anything, a list,")
    print("tuple, generator, set, without converting. Accept general read-only types;")
    print("return concrete ones (Postel's law for types).")


if __name__ == "__main__":
    main()
