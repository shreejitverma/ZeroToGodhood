"""Listing 124.1 - ctypes: calling C functions, with C's fixed-width types.

ctypes is the standard library's FFI (foreign function interface): it loads a shared
C library and calls its functions directly, no compilation, no C extension. The
essential discipline is TYPES. Python has one unbounded int and one float; C has many
fixed-width types (c_int is 32-bit, c_uint8 is an 8-bit wrapping byte, c_double is
64-bit). To call a C function correctly you declare its argument and return types
(argtypes/restype) so ctypes marshals Python values to the right C representation and
back. This listing calls libc functions and shows C's fixed-width, wrapping arithmetic.
"""

import ctypes
import ctypes.util


def main() -> None:
    libc = ctypes.CDLL(ctypes.util.find_library("c"))

    print("--- call C functions from libc, declaring their signatures ---")
    libc.strlen.restype = ctypes.c_size_t
    libc.strlen.argtypes = [ctypes.c_char_p]
    print(f"  libc.strlen(b'hello') : {libc.strlen(b'hello')}")

    libc.abs.restype = ctypes.c_int
    libc.abs.argtypes = [ctypes.c_int]
    print(f"  libc.abs(-42)         : {libc.abs(-42)}")

    print("--- C types have FIXED widths (unlike Python's unbounded int) ---")
    print(f"  sizeof(c_int)    : {ctypes.sizeof(ctypes.c_int)} bytes")
    print(f"  sizeof(c_double) : {ctypes.sizeof(ctypes.c_double)} bytes")
    print(f"  sizeof(c_uint8)  : {ctypes.sizeof(ctypes.c_uint8)} byte")

    print("--- C arithmetic WRAPS at the type's width (no arbitrary precision) ---")
    v = ctypes.c_uint8(255)
    v.value += 1                         # 255 + 1 in an 8-bit unsigned type
    print(f"  c_uint8(255).value + 1 = {v.value}   (wraps to 0; Python int would be 256)")
    signed = ctypes.c_int8(127)
    signed.value += 1
    print(f"  c_int8(127).value + 1  = {signed.value}   (wraps to -128, two's complement)")

    print("--- the rule ---")
    print(f"  ctypes calls C directly; declare argtypes/restype so values marshal")
    print(f"  correctly, and remember C types are fixed-width and wrap on overflow")


if __name__ == "__main__":
    main()
