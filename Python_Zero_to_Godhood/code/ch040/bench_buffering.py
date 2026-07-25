"""Benchmark 40.1 - buffering decides how many write syscalls you make.

A controlled comparison: the SAME per-line write loop over N lines, differing
only in the buffering parameter. Default block buffering batches the writes into
~8 KB syscalls; line buffering (buffering=1) issues a write() syscall on every
newline. The gap is the cost of a syscall per record, and it is large. No fsync
here: this isolates buffering (user space -> kernel) from durability (kernel ->
disk), which is a separate, even more expensive, decision.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import tempfile, os
d = tempfile.mkdtemp()
N = 100000
lines = [f"log entry {i}: something happened\\n" for i in range(N)]

def block_buffered():
    with open(os.path.join(d, 'b.txt'), 'w') as f:
        for s in lines:
            f.write(s)

def line_buffered():
    with open(os.path.join(d, 'l.txt'), 'w', buffering=1) as f:
        for s in lines:
            f.write(s)
"""


def main() -> None:
    # number=1: each call writes 100k lines; repeat gives the min over runs.
    # Same loop, same 100k write() calls; only the buffering parameter differs.
    results = [
        measure("block-buffered (default)", "block_buffered()", SETUP, number=1),
        measure("line-buffered (=1)", "line_buffered()", SETUP, number=1),
    ]
    report("40.1  writing 100k lines: block vs line buffering (same loop)",
           results, baseline="block-buffered (default)")

    print()
    print("Reading this. Both make 100,000 Python write() calls; the only")
    print("difference is the buffering parameter. Default block buffering batches")
    print("the lines into ~8 KB syscalls, so the OS sees a few dozen writes. Line")
    print("buffering (buffering=1) issues a write() syscall on every newline, so")
    print("the OS sees 100,000 writes, and that per-line syscall is the dominant")
    print("cost. Batch writes; do not flush (or line-buffer) per record unless you")
    print("truly need each record handed to the OS immediately. Durability (fsync)")
    print("is a further, even more expensive, step on top of this.")


if __name__ == "__main__":
    main()
