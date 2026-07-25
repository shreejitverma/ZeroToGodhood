"""Listing 125.1 - sharing whole buffers with C: one call does the loop.

Chapter 43 showed the FFI boundary costs ~10x per call, so the way to use C for a
hot LOOP is to cross ONCE with the whole buffer, not per element. ctypes gives the
pieces:
  - a ctypes array (c_int * n) is a contiguous C block you can hand to a C function.
  - one call operates on the WHOLE array (libc.qsort sorts it, libc.memset fills it).
  - from_buffer wraps an existing Python buffer (a bytearray) with ZERO COPY, so a C
    function writes directly into your memory.
This listing shows each. (Note: qsort takes a Python COMPARATOR callback, which
re-crosses the boundary per comparison, a caveat discussed in the chapter.)
"""

import ctypes
import ctypes.util


def main() -> None:
    libc = ctypes.CDLL(ctypes.util.find_library("c"))

    print("--- a ctypes array is a contiguous C block ---")
    IntArray = ctypes.c_int * 5
    arr = IntArray(5, 3, 1, 4, 2)
    print(f"  array   : {list(arr)}")
    print(f"  sizeof  : {ctypes.sizeof(arr)} bytes   (5 x 4-byte int)")

    print("--- ONE C call sorts the whole array (libc.qsort) ---")
    CmpFunc = ctypes.CFUNCTYPE(
        ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)
    )

    def compare(a, b):
        return a[0] - b[0]

    libc.qsort(arr, len(arr), ctypes.sizeof(ctypes.c_int), CmpFunc(compare))
    print(f"  after qsort : {list(arr)}   (one crossing sorted all 5)")

    print("--- ONE C call fills a whole block (libc.memset) ---")
    buf = (ctypes.c_char * 8)()
    libc.memset(buf, ord("A"), 8)
    print(f"  after memset(_, 'A', 8) : {bytes(buf)}")

    print("--- from_buffer: C writes directly into a Python bytearray (ZERO COPY) ---")
    data = bytearray(b"\x00" * 8)
    shared = (ctypes.c_char * 8).from_buffer(data)   # shares data's memory, no copy
    libc.memset(shared, ord("Z"), 8)
    print(f"  the C memset wrote into our bytearray : {bytes(data)}")
    print(f"  (data and the C view are the SAME memory, nothing was copied)")

    print("--- the rule ---")
    print(f"  hand C a whole contiguous buffer and let ONE call do the loop; use")
    print(f"  from_buffer to share Python memory with C zero-copy")


if __name__ == "__main__":
    main()
