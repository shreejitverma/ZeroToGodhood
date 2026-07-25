"""Benchmark 50.1 - comprehension vs append loop: bytecode gap, runtime near-parity.

The comprehension compiles to a dedicated LIST_APPEND opcode; the append loop
looks up list.append (LOAD_ATTR) and CALLs it every iteration (Listing 50.1).
Historically that made comprehensions clearly faster. This measures the gap on a
modern interpreter, where the specializing interpreter (Chapter 17) optimizes the
method call and narrows it. dis explains WHAT differs; the benchmark says how
much it is worth NOW.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
def comp():
    return [x * x for x in range(1000)]

def loop():
    out = []
    for x in range(1000):
        out.append(x * x)
    return out
"""


def main() -> None:
    results = [
        measure("list comprehension", "comp()", SETUP, number=20000),
        measure("append loop", "loop()", SETUP, number=20000),
    ]
    report("50.1  building a 1000-element list: comprehension vs append loop",
           results, baseline="list comprehension")

    print()
    print("Reading this. dis (Listing 50.1) shows the comprehension uses a")
    print("dedicated LIST_APPEND opcode while the loop looks up and calls")
    print("list.append every iteration, a real structural difference. But the")
    print("measured gap is small on a modern interpreter: the specializing")
    print("interpreter (Chapter 17) turns the repeated .append lookup+call into a")
    print("fast specialized path, so the once-large comprehension advantage is now")
    print("modest. Prefer comprehensions for readability (and a small speed edge),")
    print("not for a dramatic speedup that no longer exists. dis is how you check")
    print("such claims instead of repeating folklore.")


if __name__ == "__main__":
    main()
