"""Benchmark 116.1 - isinstance against an ABC is several times slower.

isinstance(x, ConcreteClass) is a fast C-level check that walks x's type and MRO.
isinstance(x, SomeABC) instead runs ABCMeta.__instancecheck__, which consults the
__subclasshook__/registry and a cache. Even cached, that custom check costs more
than the built-in path. This measures a concrete-class check against an ABC check
and a collections.abc protocol check.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import abc
import sys
import timeit
from collections.abc import Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 5_000_000


class Concrete:
    pass


class MyABC(abc.ABC):
    pass


class Impl(MyABC):
    pass


def main():
    print("=== 116.1  isinstance: concrete class vs ABC ===")
    print(provenance())
    print()

    c, i, lst = Concrete(), Impl(), [1, 2, 3]

    t_con = min(timeit.repeat(lambda: isinstance(c, Concrete), number=N, repeat=5)) / N
    t_abc = min(timeit.repeat(lambda: isinstance(i, MyABC), number=N, repeat=5)) / N
    t_proto = min(timeit.repeat(lambda: isinstance(lst, Iterable), number=N, repeat=5)) / N

    print(f"  isinstance(x, ConcreteClass)   : {t_con * 1e9:5.1f} ns   1.0x")
    print(f"  isinstance(x, ABC)             : {t_abc * 1e9:5.1f} ns   {t_abc / t_con:.1f}x")
    print(f"  isinstance(x, abc.Iterable)    : {t_proto * 1e9:5.1f} ns   {t_proto / t_con:.1f}x")

    print()
    print("Reading this. A concrete isinstance is a fast built-in check. An ABC")
    print("isinstance runs ABCMeta.__instancecheck__, which applies the")
    print("__subclasshook__/registry logic (with a cache), several times slower here.")
    print("ABCs are an interface and design tool, define required methods, recognize")
    print("structural conformers, document a protocol, not a hot-path type test. Do")
    print("not scatter isinstance-against-an-ABC through inner loops; check once at a")
    print("boundary, or prefer duck typing (just call the method) where you can.")


if __name__ == "__main__":
    main()
