"""Benchmark 117.1 - dataclasses are free: same speed as hand-written, smaller with slots.

Two measurements that place @dataclass correctly:
  - CONSTRUCTION SPEED: a @dataclass __init__ vs a hand-written one. The decorator
    GENERATES the __init__ source once at class-creation time, so there is no runtime
    magic and no per-call overhead; the two should be the same speed.
  - MEMORY: a plain @dataclass vs @dataclass(slots=True). slots drops the per-instance
    __dict__ (Chapter 22), so slotted instances are smaller.

Memory via tracemalloc, time via timeit. See _harness/bench.py.
"""

import sys
import timeit
import tracemalloc
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 1_000_000


@dataclass
class Reg:
    a: int
    b: int
    c: int


@dataclass(slots=True)
class Slotted:
    a: int
    b: int
    c: int


class Hand:
    def __init__(self, a, b, c):
        self.a, self.b, self.c = a, b, c


def main():
    print("=== 117.1  dataclass construction speed and slots memory ===")
    print(provenance())
    print()

    mb = 1024 * 1024

    tracemalloc.start()
    regs = [Reg(i, i, i) for i in range(N)]
    m_reg, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    tracemalloc.start()
    slotted = [Slotted(i, i, i) for i in range(N)]
    m_slot, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    n = 5_000_000
    t_dc = min(timeit.repeat(lambda: Reg(1, 2, 3), number=n, repeat=5)) / n
    t_hd = min(timeit.repeat(lambda: Hand(1, 2, 3), number=n, repeat=5)) / n

    print(f"  construction, @dataclass    : {t_dc * 1e9:5.1f} ns   ({t_dc / t_hd:.2f}x hand-written)")
    print(f"  construction, hand-written  : {t_hd * 1e9:5.1f} ns   1.00x")
    print()
    print(f"  memory, @dataclass          : {m_reg / mb:6.1f} MB   1.00x")
    print(f"  memory, @dataclass(slots)   : {m_slot / mb:6.1f} MB   {m_reg / m_slot:.2f}x smaller")

    del regs, slotted

    print()
    print("Reading this. @dataclass writes the __init__/__repr__/__eq__ source once,")
    print("at class-creation time, and compiles it like any method, so construction")
    print("is the SAME speed as a hand-written __init__: the decorator is a code")
    print("generator, not a runtime wrapper, there is no per-call overhead. And")
    print("slots=True drops the per-instance __dict__, making instances clearly")
    print("smaller. So a dataclass costs nothing at runtime over the class you would")
    print("have written by hand, and slots=True makes it cheaper on memory. Use")
    print("dataclasses for value/record types by default; add slots=True when you")
    print("hold many instances.")


if __name__ == "__main__":
    main()
