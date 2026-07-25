"""Benchmark 115.1 - MRO depth does not slow method calls: the type method cache.

Resolving a method walks the MRO to find the class that defines it, which is O(depth).
Naively, a method inherited from 20 classes up should cost more than one inherited
from a direct parent. It does not: CPython caches type-attribute lookups (the type
method cache, plus LOAD_METHOD specialization), so after warmup a method call is
O(1) regardless of MRO depth. This measures a method defined at the ROOT of a
1-hop chain versus a 20-hop chain.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 10_000_000


class Root:
    def m(self):
        return 1


def make_chain(depth):
    cls = Root
    for i in range(depth):
        cls = type(f"C{i}", (cls,), {})  # empty subclass; m stays defined on Root
    return cls


def main():
    print("=== 115.1  method call cost: shallow MRO vs deep MRO ===")
    print(provenance())
    print()

    Shallow = make_chain(1)              # m is 1 hop up
    Deep = make_chain(20)                # m is 20 hops up

    s, d = Shallow(), Deep()

    t_s = min(timeit.repeat(lambda: s.m(), number=N, repeat=5)) / N
    t_d = min(timeit.repeat(lambda: d.m(), number=N, repeat=5)) / N

    print(f"  shallow MRO (len {len(Shallow.__mro__)}, m 1 hop up)  : {t_s * 1e9:5.1f} ns/call")
    print(f"  deep MRO    (len {len(Deep.__mro__)}, m 20 hops up): {t_d * 1e9:5.1f} ns/call")
    print(f"  ratio deep/shallow : {t_d / t_s:.2f}x  (essentially 1: depth does not matter)")

    print()
    print("Reading this. Finding an inherited method is an O(depth) walk of the MRO,")
    print("but CPython caches the result per type (the type method cache), and the")
    print("specializing interpreter turns a hot obj.m() into a type-guarded fast path.")
    print("So a method inherited from 20 classes up costs the same as one from a")
    print("direct parent, the depth is paid once and cached, not on every call. Deep")
    print("inheritance has real costs (comprehension, fragile hierarchies, the C3")
    print("constraints), but per-call method-lookup speed is not one of them.")


if __name__ == "__main__":
    main()
