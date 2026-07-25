"""Benchmark 111.1 - 'x is None' versus 'x == None'.

Testing an object against the None singleton, two ways: 'is None' (a pointer
identity comparison) and '== None' (which dispatches the object's __eq__). For an
object with a custom __eq__, the equality path runs a Python method call per test,
several times slower, and it can also be WRONG if __eq__ mishandles None. This
measures the speed gap; correctness is shown in Listing 111.2.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 10_000_000


class Custom:
    def __init__(self, v):
        self.v = v

    def __eq__(self, other):
        return isinstance(other, Custom) and self.v == other.v


def main():
    print("=== 111.1  x is None vs x == None (object with a custom __eq__) ===")
    print(provenance())
    print()

    x = Custom(5)

    t_is = min(timeit.repeat(lambda: x is None, number=N, repeat=5)) / N
    t_eq = min(timeit.repeat(lambda: x == None, number=N, repeat=5)) / N

    print(f"  x is None (identity)     : {t_is * 1e9:5.1f} ns   1.0x")
    print(f"  x == None (dispatch __eq__): {t_eq * 1e9:5.1f} ns   {t_eq / t_is:.1f}x slower")

    print()
    print("Reading this. 'is None' is a single pointer comparison against the one")
    print("None object; nothing can intercept it. '== None' calls the object's")
    print("__eq__ (a Python method here), several times slower, and __eq__ can")
    print("return the wrong answer for None (Listing 111.2), so '== None' is both")
    print("slower and less safe. Always test singletons, None, True, False,")
    print("Ellipsis, NotImplemented, with 'is'. Linters flag '== None' for exactly")
    print("this reason.")


if __name__ == "__main__":
    main()
