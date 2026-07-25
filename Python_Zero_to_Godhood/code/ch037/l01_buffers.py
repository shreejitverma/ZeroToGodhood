"""Listing 37.1 - bytes, bytearray, memoryview, struct: binary data without copies.

bytes is immutable, bytearray is mutable, and memoryview is a zero-copy WINDOW
onto either (or any object exposing the buffer protocol). Slicing bytes copies
the slice; slicing a memoryview does not, it just adjusts offsets. struct
packs and unpacks fixed binary layouts (network protocols, file headers, C
structs). This listing shows the four working together.
"""

import struct


def main() -> None:
    print("--- bytes (immutable) vs bytearray (mutable) ---")
    b = b"hello"
    ba = bytearray(b"hello")
    ba[0] = ord("H")                 # mutation in place; bytes cannot do this
    print(f"  bytes     : {b!r} (immutable)")
    print(f"  bytearray : {bytes(ba)!r} (mutated in place)")

    print("--- memoryview: a zero-copy window; edits write through ---")
    buf = bytearray(b"AAAABBBB")
    mv = memoryview(buf)
    mv[0:4] = b"cccc"                # writes through to buf, no copy
    print(f"  after mv edit  : {bytes(buf)!r}")
    print(f"  mv[4:] slice   : {bytes(mv[4:])!r} (a view, not a copy)")

    print("--- struct: pack/unpack a fixed binary layout ---")
    # >  = big-endian; I = uint32, h = int16, f = float32
    packed = struct.pack(">Ihf", 65536, -3, 3.14)
    print(f"  packed ({len(packed)} bytes): {packed.hex()}")
    u = struct.unpack(">Ihf", packed)
    print(f"  unpacked        : {u}")
    print(f"  float32 note    : 3.14 came back as {u[2]!r}")


if __name__ == "__main__":
    main()
