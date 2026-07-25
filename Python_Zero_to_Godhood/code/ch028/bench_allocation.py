"""Benchmark 28.1 - pymalloc makes small-object allocation fast.

Small objects (<= 512 bytes) go through pymalloc's free list; larger objects go
straight to the system malloc. This measures the difference: repeatedly
allocating a small object (pymalloc, free-list reuse) versus a large one (system
malloc). The small path is the common case in Python, and pymalloc exists to make
it fast.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402


def main() -> None:
    results = [
        measure("small (64 B, pymalloc)", "for _ in range(1000): bytes(64)", "", number=2000),
        measure("large (2 KB, malloc)  ", "for _ in range(1000): bytes(2048)", "", number=2000),
    ]
    report("28.1  small (pymalloc) vs large (system malloc) allocation",
           results, baseline="small (64 B, pymalloc)")

    print()
    print("Reading this. A small allocation is roughly twice as fast as a large")
    print("one, because the small one pops a block off pymalloc's free list (no")
    print("system call, no search) while the large one calls the system malloc.")
    print("Some of the gap is the size difference, but the mechanism is real: the")
    print("common Python case, churning small short-lived objects, hits the fast")
    print("path by design. pymalloc is why a language that allocates an object")
    print("for every int result is not dominated by allocation cost.")


if __name__ == "__main__":
    main()
