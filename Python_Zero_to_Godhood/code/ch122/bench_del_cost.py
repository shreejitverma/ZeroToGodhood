"""Benchmark 122.1 - defining __del__ makes every object more expensive to destroy.

An object whose class defines __del__ needs the finalizer invoked when it is
destroyed, and historically has complicated cyclic collection. So a class with a
__del__ pays a per-object lifecycle tax that a plain class does not. This measures
the create-and-destroy cost of a class with __del__ versus an identical class without.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 2_000_000


class Plain:
    __slots__ = ("x",)

    def __init__(self):
        self.x = 1


class WithDel:
    __slots__ = ("x",)

    def __init__(self):
        self.x = 1

    def __del__(self):
        pass                             # empty, but its presence is the cost


def main():
    print("=== 122.1  create+destroy cost: class without __del__ vs with __del__ ===")
    print(provenance())
    print()

    t_plain = min(timeit.repeat(lambda: Plain(), number=N, repeat=5)) / N
    t_del = min(timeit.repeat(lambda: WithDel(), number=N, repeat=5)) / N

    print(f"  no __del__   : {t_plain * 1e9:5.1f} ns/lifecycle   1.0x")
    print(f"  with __del__ : {t_del * 1e9:5.1f} ns/lifecycle   {t_del / t_plain:.2f}x")

    print()
    print("Reading this. Each temporary is created and then freed by reference")
    print("counting the instant the next one is bound. When the class defines")
    print("__del__, freeing it must invoke that finalizer, so every object of the")
    print("class pays a lifecycle tax, about 1.5x here, even with an empty __del__.")
    print("Combined with __del__'s unreliability (swallowed exceptions, unspecified")
    print("timing in cycles), this is why __del__ is a poor default for cleanup.")
    print("Use a context manager (deterministic, no per-object tax) or")
    print("weakref.finalize (reliable, cost only on objects you register).")


if __name__ == "__main__":
    main()
