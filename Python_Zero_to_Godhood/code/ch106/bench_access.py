"""Benchmark 106.1 - __getattr__ is free for hits; __getattribute__ taxes every access.

Reading an EXISTING attribute on three classes: a plain class, a class that adds
__getattr__ (the miss-only fallback), and a class that overrides __getattribute__
(the every-access hook). __getattr__ should cost nothing for a hit, because it is
never reached; __getattribute__ should cost several times more, because a Python
function now runs on every single access. This measures all three.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 10_000_000


class Plain:
    def __init__(self):
        self.x = 1


class HasGetattr:
    def __init__(self):
        self.x = 1

    def __getattr__(self, name):        # only fires on a miss
        raise AttributeError(name)


class HasGetattribute:
    def __init__(self):
        self.x = 1

    def __getattribute__(self, name):   # fires on EVERY access
        return object.__getattribute__(self, name)


def main():
    print("=== 106.1  reading an existing attribute: plain vs __getattr__ vs __getattribute__ ===")
    print(provenance())
    print()

    p, ga, gb = Plain(), HasGetattr(), HasGetattribute()

    t_p = min(timeit.repeat(lambda: p.x, number=N, repeat=5)) / N
    t_ga = min(timeit.repeat(lambda: ga.x, number=N, repeat=5)) / N
    t_gb = min(timeit.repeat(lambda: gb.x, number=N, repeat=5)) / N

    print(f"  plain              p.x : {t_p * 1e9:6.1f} ns   1.0x")
    print(f"  + __getattr__     ga.x : {t_ga * 1e9:6.1f} ns   {t_ga / t_p:.2f}x  (miss-only: free for hits)")
    print(f"  + __getattribute__ gb.x: {t_gb * 1e9:6.1f} ns   {t_gb / t_p:.2f}x  (every access: taxed)")

    print()
    print("Reading this. __getattr__ costs nothing for an existing attribute")
    print("because it is only called when normal lookup fails, so it never runs on")
    print("a hit. __getattribute__ runs a Python function on EVERY access, several")
    print("times slower here. The design rule follows: to add lazy or synthesized")
    print("attributes, implement __getattr__ (the miss-only fallback); reach for")
    print("__getattribute__ only when you must intercept every access (a proxy, an")
    print("access log), and know you are taxing every read to do it.")


if __name__ == "__main__":
    main()
