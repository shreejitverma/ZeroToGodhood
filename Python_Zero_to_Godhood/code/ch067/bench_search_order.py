"""Benchmark 67.1 - sys.path position affects import resolution cost.

The path-based finder walks sys.path in order, checking each directory for the
module, so a module found near the FRONT is located quickly, while one found at
the BACK (or a missing module) requires scanning every directory before it. This
builds a long sys.path (60 extra directories) with a target only in the last one
versus the first, and times find_spec, so the linear-scan cost of import
resolution is visible.

Does its own timing (it mutates sys.path), guarded by __main__. See
_harness/bench.py.
"""

import importlib
import importlib.util
import os
import sys
import tempfile
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N_DIRS = 60


def main():
    print("=== 67.1  import resolution cost vs sys.path position ===")
    print(provenance())
    print()

    d = tempfile.mkdtemp()
    dirs = [os.path.join(d, f"p{i:02}") for i in range(N_DIRS)]
    for p in dirs:
        os.mkdir(p)
    with open(os.path.join(dirs[0], "target_front.py"), "w") as f:
        f.write("X = 1\n")
    with open(os.path.join(dirs[-1], "target_back.py"), "w") as f:
        f.write("X = 1\n")

    base = sys.path[:]
    sys.path[:] = base + dirs          # append so the stdlib stays reachable
    importlib.invalidate_caches()
    n = 20000
    front = min(timeit.timeit(lambda: importlib.util.find_spec("target_front"), number=n) for _ in range(3)) / n * 1e9
    back = min(timeit.timeit(lambda: importlib.util.find_spec("target_back"), number=n) for _ in range(3)) / n * 1e9
    missing = min(timeit.timeit(lambda: importlib.util.find_spec("nope_xyz_none"), number=n) for _ in range(3)) / n * 1e9
    sys.path[:] = base

    print(f"  sys.path length          : {N_DIRS} extra dirs")
    print(f"  found near the front     : {front:>10,.0f} ns")
    print(f"  found at the back        : {back:>10,.0f} ns")
    print(f"  missing (scan them all)  : {missing:>10,.0f} ns")
    print(f"  back / front             : {back / front:>10.1f}x")

    print()
    print("Reading this. find_spec walks sys.path in order, so a module at the back")
    print("of a long path costs several times one at the front, and a missing module")
    print("pays the full scan. Two lessons: keep sys.path short and put the most-used")
    print("locations first; and because the FIRST match wins, a directory early on")
    print("the path (like the script's own directory, sys.path[0]) shadows anything")
    print("later, including the standard library. Never name a file after a stdlib")
    print("module.")


if __name__ == "__main__":
    main()
