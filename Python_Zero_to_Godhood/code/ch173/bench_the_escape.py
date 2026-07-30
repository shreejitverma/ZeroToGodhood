"""Benchmark 173.1 - the escape, priced with the standard library only.

Two tasks, each climbed from a pure-Python loop to an executor that runs zero
Python instructions per element. Both escapes ship in the standard library, so
the measurement needs no third-party code; NumPy's version of the same move is
Deep T's subject, and writing your own C is Deep M's.

  173.1a  sum of squares, 100,000 ints: explicit loop -> genexp -> math.sumprod.
          sumprod (3.12+) walks both iterables in C: the elements are still
          Python ints, but the LOOP has no bytecode, no frame, no dispatch.

  173.1b  count zero bytes in 1 MB: a Python loop over the buffer against
          bytes.count. Here even the elements stop being Python objects: the
          C side scans raw memory, and the ratio changes in kind.

The pairing shows the two rungs of every escape: first the loop leaves Python
(the elements do not), then the DATA leaves Python (Chapter 89's packed
representations), and each rung is roughly an order of magnitude.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402


def main():
    SUM_SETUP = """
import math
N = 100_000
data = list(range(N))
"""
    sums = [
        measure("explicit loop", """
total = 0
for x in data:
    total += x * x
""", SUM_SETUP, repeat=7, number=200),
        measure("sum(x*x for x in data)", "sum(x * x for x in data)",
                SUM_SETUP, repeat=7, number=200),
        measure("math.sumprod(data, data)", "math.sumprod(data, data)",
                SUM_SETUP, repeat=7, number=200),
    ]
    report("173.1a  sum of squares, 100,000 ints: the loop leaves Python",
           sums, baseline="explicit loop")

    print()
    COUNT_SETUP = """
buffer = (b"x" * 255 + b"\\x00") * 4096      # 1 MB, one zero byte per 256
"""
    counts = [
        measure("Python loop over the buffer", """
count = 0
for b in buffer:
    if b == 0:
        count += 1
""", COUNT_SETUP, repeat=5, number=10),
        measure("buffer.count(0)", "buffer.count(0)",
                COUNT_SETUP, repeat=5, number=10),
    ]
    report("173.1b  count zero bytes in 1 MB: the data leaves Python too",
           counts, baseline="Python loop over the buffer")

    print()
    print("Reading this. In 173.1a the elements are unchanged - the same hundred")
    print("thousand Python ints get multiplied and added - only the loop moved to C:")
    print("no bytecode dispatch, no frame resumes, no LOAD/STORE per element.")
    print("That one move is worth several times, and it is available any time a")
    print("builtin or a C-implemented function expresses the whole loop.")
    print()
    print("In 173.1b the data moved as well: bytes.count scans raw memory in which")
    print("no element was ever a Python object, and the ratio multiplies again,")
    print("to sub-nanosecond per byte. That is the full escape, and it is Chapter")
    print("89's packed-representation rule seen from the time side: pack the data,")
    print("then hand the WHOLE buffer to something that consumes it (Chapter 84's")
    print("one-crossing-per-batch). NumPy industrialises this second rung for")
    print("arithmetic (Deep T); the standard library already ships it for bytes,")
    print("hashing, compression, and sorting.")


if __name__ == "__main__":
    main()
