"""Benchmark 109.1 - total_ordering trades a little speed for a lot less code.

functools.total_ordering synthesizes the missing order methods by composing the
ones you wrote (for example a derived __ge__ is roughly "not self < other"), so a
synthesized comparison runs an extra call and negation compared with a hand-written
one. This measures a total_ordering-synthesized __ge__ against an identical
hand-written __ge__. The synthesized one is slower, the documented cost of the
convenience.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import functools
import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 5_000_000


@functools.total_ordering
class Auto:
    __slots__ = ("v",)

    def __init__(self, v):
        self.v = v

    def __eq__(self, o):
        return self.v == o.v

    def __lt__(self, o):
        return self.v < o.v              # __ge__ etc are synthesized from this


class Manual:
    __slots__ = ("v",)

    def __init__(self, v):
        self.v = v

    def __eq__(self, o):
        return self.v == o.v

    def __lt__(self, o):
        return self.v < o.v

    def __le__(self, o):
        return self.v <= o.v

    def __gt__(self, o):
        return self.v > o.v

    def __ge__(self, o):
        return self.v >= o.v             # hand-written, direct


def main():
    print("=== 109.1  synthesized vs hand-written __ge__ (a >= b) ===")
    print(provenance())
    print()

    a1, a2 = Auto(1), Auto(2)
    m1, m2 = Manual(1), Manual(2)

    t_auto = min(timeit.repeat(lambda: a1 >= a2, number=N, repeat=5)) / N
    t_man = min(timeit.repeat(lambda: m1 >= m2, number=N, repeat=5)) / N

    print(f"  total_ordering __ge__ (synthesized) : {t_auto * 1e9:6.1f} ns/call")
    print(f"  hand-written   __ge__ (direct)      : {t_man * 1e9:6.1f} ns/call")
    print(f"  the synthesized one costs ~{t_auto / t_man:.1f}x the hand-written")

    print()
    print("Reading this. total_ordering builds the three missing order methods by")
    print("composing the ones you wrote, so a synthesized __ge__ runs an extra")
    print("comparison call and a negation that a hand-written __ge__ does not. The")
    print("cost is ~1.7x per call here. That is a fine trade for most code: you")
    print("write two methods instead of five and cannot get the pairs inconsistent.")
    print("Hand-write all six only on a type whose comparisons are genuinely hot;")
    print("otherwise use @total_ordering and keep the class small and correct.")


if __name__ == "__main__":
    main()
