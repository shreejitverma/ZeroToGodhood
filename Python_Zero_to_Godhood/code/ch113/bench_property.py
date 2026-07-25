"""Benchmark 113.1 - a property is a descriptor, so every read calls a function.

property is a DATA descriptor whose __get__ calls your getter function. So reading
a property runs a Python function call on every access, where reading a plain stored
attribute is a direct dict/slot fetch. This measures a trivial property (returning a
stored value) against a plain attribute, to price the descriptor indirection.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 10_000_000


class WithProperty:
    def __init__(self):
        self._x = 1

    @property
    def x(self):
        return self._x                   # getter runs on every read


class Direct:
    def __init__(self):
        self.x = 1                       # plain stored attribute


def main():
    print("=== 113.1  property access vs plain attribute access ===")
    print(provenance())
    print()

    p, d = WithProperty(), Direct()

    t_prop = min(timeit.repeat(lambda: p.x, number=N, repeat=5)) / N
    t_attr = min(timeit.repeat(lambda: d.x, number=N, repeat=5)) / N

    print(f"  plain attribute d.x         : {t_attr * 1e9:5.1f} ns   1.0x")
    print(f"  property       p.x (getter) : {t_prop * 1e9:5.1f} ns   {t_prop / t_attr:.1f}x")

    print()
    print("Reading this. A property is a data descriptor: reading p.x invokes the")
    print("descriptor's __get__, which calls your getter function, so a trivial")
    print("property costs about 2x a plain attribute read. That is the right price")
    print("when the property computes, validates, or protects something. It is wasted")
    print("when the property just returns a stored value: wrapping a plain attribute")
    print("in a pass-through property 'for future-proofing' doubles every read for no")
    print("benefit. Start with a plain attribute; Python lets you convert it to a")
    print("property later WITHOUT changing the attribute-access API, so there is no")
    print("cost to waiting until you actually need the computation or validation.")


if __name__ == "__main__":
    main()
