"""Benchmark 43.1 - pathlib's object overhead is real and irrelevant.

pathlib.Path joins build path OBJECTS, so a pure path manipulation is several
times slower than the equivalent os.path string call. This measures that gap,
and then measures a single os.stat (one filesystem syscall) as the yardstick:
the point is that a Path join costs LESS than one stat, and any code that
actually touches the filesystem does so many stats/opens/reads, next to which
the join overhead vanishes. So choose pathlib for correctness and readability,
not against it for speed.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import os.path, tempfile, os
from pathlib import PurePosixPath
d = tempfile.mkdtemp()
f = os.path.join(d, "probe")
open(f, "w").close()
"""


def main() -> None:
    results = [
        measure("os.path.join (string)", "os.path.join('/a/b', 'c', 'd.txt')", SETUP, number=100000),
        measure("Path / join (object)", "PurePosixPath('/a/b') / 'c' / 'd.txt'", SETUP, number=100000),
        measure("os.stat (1 syscall)", "os.stat(f)", SETUP, number=100000),
    ]
    report("43.1  path manipulation vs one filesystem syscall",
           results, baseline="os.path.join (string)")

    print()
    print("Reading this. The Path join is several times slower than os.path.join")
    print("because it builds an object, but it still costs less than a single")
    print("os.stat, and os.stat is the cheapest real filesystem operation there")
    print("is. Any code that opens, reads, or walks files does many such syscalls,")
    print("and the path-join overhead disappears next to them. The only time the")
    print("gap matters is millions of pure path manipulations with no I/O at all,")
    print("which is rare. Choose pathlib for correctness; the speed worry is")
    print("misplaced.")


if __name__ == "__main__":
    main()
