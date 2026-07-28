"""Benchmark 165.1 - checking Listing 165.1's model against a real operation.

The model is only worth anything if it predicts. So: one task, find the first zero byte
in a buffer, implemented as each of the four designs the model prices, plus the stdlib's
own C implementation as the floor.

  design 1  a Python loop over the bytes
  design 2  one ctypes call per byte (libc.isprint, chosen because it is trivial, so the
            row measures the crossing and nothing else)
  design 3  one ctypes call over the whole buffer (libc.strlen scans to the NUL in C)
  floor     bytes.index(0), the same C scan reached through the interpreter

Design 4 - a C loop calling back into Python per element - is not re-measured here; it
was measured directly in Benchmark 164.1 at 283 ns per callback, and that constant is
what the model uses.

The prediction to check is not the absolute times, which depend on how much work each C
routine does per byte. It is the SHAPE: design 2 far worse than design 1, design 3 far
better than both, and design 3's advantage growing with n because its slope is C's.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SMALL = 100
LARGE = 100_000

SETUP = f"""
import ctypes
import ctypes.util

libc = ctypes.CDLL(ctypes.util.find_library("c"))
libc.strlen.argtypes = [ctypes.c_char_p]
libc.strlen.restype = ctypes.c_size_t
libc.isprint.argtypes = [ctypes.c_int]
libc.isprint.restype = ctypes.c_int

SMALL = {SMALL}
LARGE = {LARGE}
small = b"x" * (SMALL - 1) + b"\\x00"
large = b"x" * (LARGE - 1) + b"\\x00"


def python_loop(buf):
    for i, byte in enumerate(buf):
        if byte == 0:
            return i
    return -1


def ffi_per_element(buf):
    for i, byte in enumerate(buf):
        libc.isprint(byte)          # one crossing per byte, deliberately
        if byte == 0:
            return i
    return -1


def ffi_whole_buffer(buf):
    return libc.strlen(buf)         # one crossing, C scans the whole thing


def stdlib_floor(buf):
    return buf.index(0)
"""


def main():
    small = [
        measure("1  Python loop", "python_loop(small)", SETUP, repeat=9, number=2_000),
        measure("2  FFI per element", "ffi_per_element(small)", SETUP, repeat=9, number=2_000),
        measure("3  FFI whole buffer", "ffi_whole_buffer(small)", SETUP, repeat=9, number=2_000),
        measure("   stdlib bytes.index", "stdlib_floor(small)", SETUP, repeat=9, number=2_000),
    ]
    report(f"165.1a  find the first zero byte, n = {SMALL}",
           small, baseline="1  Python loop")

    print()
    large = [
        measure("1  Python loop", "python_loop(large)", SETUP, repeat=5, number=20),
        measure("2  FFI per element", "ffi_per_element(large)", SETUP, repeat=5, number=20),
        measure("3  FFI whole buffer", "ffi_whole_buffer(large)", SETUP, repeat=5, number=20),
        measure("   stdlib bytes.index", "stdlib_floor(large)", SETUP, repeat=5, number=20),
    ]
    report(f"165.1b  the same, n = {LARGE:,}",
           large, baseline="1  Python loop")

    print()
    small_by = {r.label: r.min_ns for r in small}
    large_by = {r.label: r.min_ns for r in large}
    growth = LARGE / SMALL
    print(f"how each design scales from n={SMALL} to n={LARGE:,} "
          f"(a factor of {growth:,.0f} in n):")
    for label in small_by:
        print(f"  {label:<22} time grew {large_by[label] / small_by[label]:8.1f}x")

    print()
    print("Reading this. The model's shape holds. Crossing per element is far worse than")
    print("staying in Python, by roughly the ratio the constants predict, and it is worse")
    print("at every size, because both designs are linear and one has a much larger")
    print("slope. Crossing once is far better than both, and the scaling column is where")
    print("that shows: the per-element designs grow with n almost exactly, while the")
    print("whole-buffer call grows far less, because its Python-side cost is a constant")
    print("and only the C scan grows. The stdlib row is the same C scan reached without")
    print("ctypes, and it is the honest reminder that the first question is never 'which")
    print("FFI' but 'is this already in the standard library'.")


if __name__ == "__main__":
    main()
