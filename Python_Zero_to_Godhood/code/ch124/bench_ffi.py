"""Benchmark 124.1 - the FFI boundary has real per-call overhead.

Every ctypes call marshals the Python arguments into C types, calls the C function,
and marshals the result back. For a tiny function that boundary cost DOMINATES: a
ctypes call to libc's abs is much slower than Python's builtin abs, even though abs
in C is a single machine instruction. This measures both, to place ctypes correctly:
it is for calling INTO existing C libraries, not for speeding up small hot-loop calls.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import ctypes
import ctypes.util
import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 5_000_000


def main():
    print("=== 124.1  FFI call overhead: ctypes libc.abs vs builtin abs ===")
    print(provenance())
    print()

    libc = ctypes.CDLL(ctypes.util.find_library("c"))
    libc.abs.restype = ctypes.c_int
    libc.abs.argtypes = [ctypes.c_int]

    t_c = min(timeit.repeat(lambda: libc.abs(-42), number=N, repeat=5)) / N
    t_py = min(timeit.repeat(lambda: abs(-42), number=N, repeat=5)) / N

    print(f"  builtin abs(-42)    : {t_py * 1e9:6.1f} ns   1.0x")
    print(f"  ctypes libc.abs(-42): {t_c * 1e9:6.1f} ns   {t_c / t_py:.1f}x")

    print()
    print("Reading this. The ctypes call is much slower than the builtin, not because")
    print("C's abs is slow (it is one instruction) but because each call marshals the")
    print("argument Python int -> C int, invokes the foreign function, and marshals")
    print("the result back. That boundary cost is fixed per call, so it dominates for")
    print("tiny functions. The implication: use ctypes to call INTO existing C")
    print("libraries (a codec, a crypto primitive, a hardware driver) where each call")
    print("does substantial work that amortizes the boundary, not to replace a small")
    print("Python operation call-by-call. To move a hot LOOP into C, pass the whole")
    print("buffer once (the buffer protocol, Deep Q) so one call does all the work.")


if __name__ == "__main__":
    main()
