"""Benchmark 107.1 - __slots__ is a MEMORY tool, not a speed tool.

A four-field object, a million of them, with and without __slots__: peak memory
(tracemalloc) and per-attribute read time (timeit). __slots__ should use clearly
less memory (no per-instance dict) but give essentially the SAME access speed,
because both the dict path and the slot path resolve in C. This measures both, to
place __slots__ correctly: it saves memory and locks the attribute set; it does
not meaningfully speed up attribute access.

Memory via tracemalloc, time via timeit. See _harness/bench.py.
"""

import sys
import timeit
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 1_000_000


class WithDict:
    def __init__(self):
        self.a = self.b = self.c = self.d = 0


class WithSlots:
    __slots__ = ("a", "b", "c", "d")

    def __init__(self):
        self.a = self.b = self.c = self.d = 0


def main():
    print("=== 107.1  1,000,000 four-field objects: __dict__ vs __slots__ ===")
    print(provenance())
    print()

    mb = 1024 * 1024

    tracemalloc.start()
    dicts = [WithDict() for _ in range(N)]
    m_d, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    tracemalloc.start()
    slots = [WithSlots() for _ in range(N)]
    m_s, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    wd, ws = WithDict(), WithSlots()
    n = 10_000_000
    t_d = min(timeit.repeat(lambda: wd.a, number=n, repeat=5)) / n
    t_s = min(timeit.repeat(lambda: ws.a, number=n, repeat=5)) / n

    print(f"  memory, __dict__   : {m_d / mb:6.1f} MB   1.00x")
    print(f"  memory, __slots__  : {m_s / mb:6.1f} MB   {m_s / m_d:.2f}x   ({m_d / m_s:.2f}x smaller)")
    print(f"  access, __dict__   : {t_d * 1e9:6.1f} ns")
    print(f"  access, __slots__  : {t_s * 1e9:6.1f} ns   ({t_s / t_d:.2f}x)")

    del dicts, slots

    print()
    print("Reading this. __slots__ uses clearly less memory, it drops the")
    print("per-instance dict and stores fields in a compact slot layout, but")
    print("attribute reads are essentially the SAME speed: both the instance-dict")
    print("path and the slot-descriptor path resolve in C. So __slots__ is a memory")
    print("optimization and an attribute-set lock (typos become errors), not a")
    print("speed optimization. Use it for objects you make in large numbers or want")
    print("to keep closed; do not reach for it expecting faster attribute access.")


if __name__ == "__main__":
    main()
