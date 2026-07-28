"""Benchmark 160.1 - what a view costs and what a copy costs.

Slicing `bytes` allocates and copies the slice. Slicing a `memoryview` allocates a small
view object and copies nothing. At one byte of difference that is invisible; at a
megabyte it is the difference between O(1) and O(n), and in the classic incremental-parse
loop - strip a header, keep the rest, repeat - it is the difference between O(n) and
O(n^2).

Three measurements:

  160.1a  one slice of a large buffer: the constant-versus-linear difference.
  160.1b  the parse loop: 1,000 successive header strips over the same buffer.
  160.1c  what it costs to stop borrowing: bytes(view) materialises the copy you
          avoided, which is the honest other half of the story.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

MB = 1 << 20
STRIPS = 1_000
HEADER = 16

SETUP = f"""
MB = {MB}
STRIPS = {STRIPS}
HEADER = {HEADER}

data = bytes(MB)
view = memoryview(data)
small = bytes(64)
small_view = memoryview(small)


def strip_bytes(buf):
    for _ in range(STRIPS):
        buf = buf[HEADER:]
    return len(buf)


def strip_view(buf):
    with memoryview(buf) as mv:
        for _ in range(STRIPS):
            mv = mv[HEADER:]
        return len(mv)
"""


def main():
    one_slice = [
        measure("bytes[1:]   1 MB", "data[1:]", SETUP, repeat=9, number=2_000),
        measure("view[1:]    1 MB", "view[1:]", SETUP, repeat=9, number=2_000),
        measure("bytes[1:]   64 B", "small[1:]", SETUP, repeat=9, number=2_000),
        measure("view[1:]    64 B", "small_view[1:]", SETUP, repeat=9, number=2_000),
    ]
    report("160.1a  one slice: the copy is linear, the view is constant",
           one_slice, baseline="view[1:]    1 MB")

    print()
    parse = [
        measure(f"{STRIPS} strips over bytes", "strip_bytes(data)", SETUP, repeat=5, number=2),
        measure(f"{STRIPS} strips over a view", "strip_view(data)", SETUP, repeat=5, number=2),
    ]
    report(f"160.1b  the parse loop: strip a {HEADER}-byte header {STRIPS:,} times",
           parse, baseline=f"{STRIPS} strips over a view")

    print()
    materialise = [
        measure("bytes(view)  1 MB", "bytes(view)", SETUP, repeat=9, number=2_000),
        measure("view.tobytes()  1 MB", "view.tobytes()", SETUP, repeat=9, number=2_000),
        measure("view[1:]  (no copy)", "view[1:]", SETUP, repeat=9, number=2_000),
    ]
    report("160.1c  the other half: materialising what you borrowed",
           materialise, baseline="view[1:]  (no copy)")

    print()
    print("Reading this. A memoryview slice is a fixed cost - allocate a small object,")
    print("record an offset and a length - and it does not grow with the buffer. A bytes")
    print("slice allocates and memcpy's the slice, so it grows with what you sliced. At")
    print("64 bytes the two are within a small factor and the view is not worth the")
    print("complexity. At a megabyte the difference is three orders of magnitude, and in")
    print("a loop that repeatedly slices the tail it is an algorithmic difference, not a")
    print("constant one: each bytes slice copies what remains, so the loop is quadratic.")
    print("The last table is the honest caveat: the copy did not disappear, it moved to")
    print("wherever you finally need a real bytes object. A view is worth using when the")
    print("consumer can take a buffer - a socket send, a struct.unpack_from, a C call -")
    print("and worth nothing when the consumer needs bytes and you have to materialise.")


if __name__ == "__main__":
    main()
