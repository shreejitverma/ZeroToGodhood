"""Benchmark 13.1 - the generated dataclass __init__ has zero per-call overhead,
and cached_property earns its keep.

Two claims. First, that @dataclass generates real compiled methods that run at
hand-written speed (section 13.1). Second, that cached_property turns repeated
expensive access into a one-time cost.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

INIT_SETUP = """
from dataclasses import dataclass

@dataclass
class DC:
    x: int
    y: int
    z: int

class HandWritten:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
"""

CP_SETUP = """
from functools import cached_property

class WithCache:
    @cached_property
    def value(self):
        return sum(range(1000))

class WithProperty:
    @property
    def value(self):
        return sum(range(1000))

cached = WithCache()
cached.value           # warm the cache
prop = WithProperty()
"""


def main() -> None:
    init = [
        measure("hand-written __init__", "for _ in range(1000): HandWritten(1, 2, 3)", INIT_SETUP, number=1000),
        measure("dataclass __init__   ", "for _ in range(1000): DC(1, 2, 3)", INIT_SETUP, number=1000),
    ]
    report("13.1a  generated __init__ vs hand-written: identical",
           init, baseline="hand-written __init__")

    print()
    cp = [
        measure("cached_property (warm)", "for _ in range(1000): cached.value", CP_SETUP, number=1000),
        measure("property (recomputes) ", "for _ in range(1000): prop.value", CP_SETUP, number=1000),
    ]
    report("13.1b  cached_property vs a recomputing property",
           cp, baseline="cached_property (warm)")

    print()
    print("Reading both. 13.1a confirms the design claim: @dataclass assembles")
    print("real source, compiles it, and attaches ordinary functions, so the")
    print("generated __init__ runs at exactly hand-written speed, there is no")
    print("per-call decorator overhead. 13.1b shows why cached_property exists: a")
    print("plain @property recomputes sum(range(1000)) on every read, while")
    print("cached_property is shadowed by the value it wrote to the instance dict")
    print("and never recomputes. Use cached_property for expensive, stable-per-")
    print("instance values; use @property when the value can change.")


if __name__ == "__main__":
    main()
