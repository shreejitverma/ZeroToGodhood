"""Benchmark 125.1 - one C call over a whole buffer vs a Python per-element loop.

The amortization principle of Chapter 43, measured. Zeroing 1,000,000 bytes two
ways: a single libc.memset call (one boundary crossing; C runs the loop at memory
speed) versus a Python loop writing each byte (a million interpreter iterations).
The single-call version is dramatically faster, this is why the correct FFI pattern
for a hot loop is 'pass the whole buffer once', not 'call C per element'.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import ctypes
import ctypes.util
import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 1_000_000


def main():
    print(f"=== 125.1  zero {N:,} bytes: one C memset vs a Python byte loop ===")
    print(provenance())
    print()

    libc = ctypes.CDLL(ctypes.util.find_library("c"))
    buf = (ctypes.c_char * N)()

    def one_c_call():
        libc.memset(buf, 0, N)           # ONE crossing; C fills the whole buffer

    def python_loop():
        for i in range(N):               # a million interpreter iterations
            buf[i] = 0

    t_c = min(timeit.repeat(one_c_call, number=200, repeat=5)) / 200
    t_py = min(timeit.repeat(python_loop, number=3, repeat=3)) / 3

    print(f"  one C memset call : {t_c * 1e6:9.1f} us   1x")
    print(f"  Python byte loop  : {t_py * 1e3:9.1f} ms   {t_py / t_c:.0f}x slower")

    print()
    print("Reading this. The single memset crosses the FFI boundary ONCE and lets C")
    print("run the loop at memory-bandwidth speed; the Python version pays interpreter")
    print("overhead on every one of a million iterations (and, done via ctypes")
    print("per-element, would pay the ~10x boundary cost a million times over). This")
    print("is the whole architecture of the Python/C boundary: cross rarely with a")
    print("lot of work each time. It is exactly how NumPy and the buffer protocol")
    print("beat per-element Python, hand C (or vectorized code) the whole array and")
    print("let one call do everything. Chapter 43's ~10x per call and this ~8000x")
    print("whole-buffer win are two views of the same rule: amortize the crossing.")


if __name__ == "__main__":
    main()
