"""Benchmark 17.1 - monomorphism is the lever the specializing interpreter gives
you.

The chapter's coding guidance is "keep hot call sites monomorphic." This measures
why: the same attribute-read and add loops, run over a single type versus two
types, so the specializer can hold its bet in the first case and thrashes in the
second.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

ATTR_SETUP = """
class A:
    def __init__(self): self.x = 1
class B:
    def __init__(self): self.x = 2

def read(o):
    return o.x

a, b = A(), B()
mono = [a] * 100          # one type
poly = [a, b] * 50        # two types, same site
"""

ADD_SETUP = """
def add(a, b):
    return a + b

ints = [(1, 2)] * 100                 # int + int, monomorphic
mixed = [(1, 2), ('a', 'b')] * 50     # int + int AND str + str at one site
"""


def main() -> None:
    attr = [
        measure("monomorphic (one type) ", "for o in mono: read(o)", ATTR_SETUP, number=3000),
        measure("polymorphic (two types)", "for o in poly: read(o)", ATTR_SETUP, number=3000),
    ]
    report("17.1a  attribute read: monomorphic vs polymorphic site",
           attr, baseline="monomorphic (one type) ")

    print()
    add = [
        measure("monomorphic (int + int)", "for a, b in ints: add(a, b)", ADD_SETUP, number=3000),
        measure("polymorphic (int / str)", "for a, b in mixed: add(a, b)", ADD_SETUP, number=3000),
    ]
    report("17.1b  binary add: monomorphic vs polymorphic site",
           add, baseline="monomorphic (int + int)")

    print()
    print("Reading both. The monomorphic sites hold their specialization")
    print("(LOAD_ATTR_INSTANCE_VALUE, BINARY_OP_ADD_INT) and take the fast path")
    print("every time. The polymorphic sites see two types at one instruction, so")
    print("the guard misses on half the calls and deoptimizes, costing about")
    print("1.5x. This is why monomorphism is the real lever in 3.11+ code: the")
    print("biggest wins come from consistent types at hot sites, not from chasing")
    print("opcode counts by hand. Split a polymorphic hot function into separate")
    print("monomorphic ones if the profile shows it matters.")


if __name__ == "__main__":
    main()
