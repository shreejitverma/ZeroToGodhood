"""Benchmark 93.1 - building a union inline in isinstance costs; precompute it.

isinstance accepts a union type (int | str) since 3.10. But writing the union
INLINE in the call, isinstance(x, int | str), builds a new union object every
time. An (int, str) tuple avoids that, and a PRECOMPUTED union (built once, at
module level) is faster still, the union check itself is efficient once the object
exists. So the cost is in constructing the union, not checking it. This measures
the three forms.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
PRECOMPUTED = int | str
"""


def main() -> None:
    results = [
        measure("precomputed union", "isinstance(5, PRECOMPUTED)", SETUP, number=2000000),
        measure("tuple (int, str)", "isinstance(5, (int, str))", SETUP, number=2000000),
        measure("inline union int | str", "isinstance(5, int | str)", SETUP, number=2000000),
    ]
    report("93.1  isinstance with a union: precomputed vs tuple vs inline",
           results, baseline="precomputed union")

    print()
    print("Reading this. Checking against a precomputed union is the fastest, the")
    print("union object already exists and the check is efficient. A tuple is close.")
    print("Writing the union INLINE (isinstance(x, int | str)) is the slowest,")
    print("because it BUILDS a new union object on every call. So the cost is in")
    print("constructing the union, not the membership test. For a one-off check the")
    print("difference is nothing; in a hot loop, precompute the union once (a module")
    print("constant) or use a tuple, do not build `int | str` per iteration.")


if __name__ == "__main__":
    main()
