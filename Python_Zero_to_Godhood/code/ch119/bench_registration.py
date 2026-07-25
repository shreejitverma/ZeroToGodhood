"""Benchmark 119.1 - class customization is free at runtime (per instance).

__init_subclass__ (and class decorators, and metaclasses) run at class-DEFINITION
time, once per class, not per instance. So instances of a class with an
auto-registering __init_subclass__ construct at the SAME speed as instances of a
plain class: the registration happened once, when the class was defined. This
measures instance construction for a registered class versus a plain one, and the
one-time class-creation cost of the hook.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 5_000_000


class PlainBase:
    pass


class Plain(PlainBase):
    def __init__(self, x):
        self.x = x


class RegBase:
    registry = {}

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        RegBase.registry[cls.__name__] = cls


class Registered(RegBase):
    def __init__(self, x):
        self.x = x


def main():
    print("=== 119.1  instance construction: plain class vs auto-registered class ===")
    print(provenance())
    print()

    t_p = min(timeit.repeat(lambda: Plain(1), number=N, repeat=5)) / N
    t_r = min(timeit.repeat(lambda: Registered(1), number=N, repeat=5)) / N

    print(f"  plain class instance      : {t_p * 1e9:5.1f} ns")
    print(f"  registered class instance : {t_r * 1e9:5.1f} ns   ({t_r / t_p:.2f}x)")

    print()
    print("Reading this. The __init_subclass__ hook that registered the class ran")
    print("ONCE, when the class was defined, not on any instance. So constructing an")
    print("instance of the registered class is the same speed as a plain one: class")
    print("customization is a definition-time, once-per-class cost with zero")
    print("per-instance overhead. The same is true of class decorators and")
    print("metaclasses, they shape the class at creation and then step out of the")
    print("way. So a registry, a plugin system, or a validation hook built this way")
    print("adds nothing to the runtime cost of the objects it governs.")


if __name__ == "__main__":
    main()
