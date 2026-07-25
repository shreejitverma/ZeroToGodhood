"""Listing 124.2 - ctypes Structures and pointers: mirroring C memory layout.

Beyond calling functions, ctypes lets you build the DATA C expects: a
ctypes.Structure declares fields with C types, laid out exactly like the equivalent
C struct (contiguous, in order, with the platform's alignment). You can read/write
its fields, take its address, and pass it (or a pointer to it) to a C function.
Pointers (pointer/byref) let a C function write back into your memory, the standard
C idiom of "pass a pointer for the function to fill in". This listing builds a
struct, checks its layout, and dereferences a pointer.
"""

import ctypes


class Point(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
    ]


class Rect(ctypes.Structure):
    _fields_ = [
        ("topleft", Point),              # structs nest, like in C
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
    ]


def main() -> None:
    print("--- a Structure lays out fields exactly like a C struct ---")
    p = Point(3, 4)
    print(f"  Point(3, 4).x, .y : {p.x}, {p.y}")
    print(f"  sizeof(Point)     : {ctypes.sizeof(Point)} bytes   (two 4-byte ints)")

    print("--- fields are mutable, in place ---")
    p.x = 100
    print(f"  after p.x = 100   : {p.x}")

    print("--- structs nest and their size is the sum (plus any alignment) ---")
    r = Rect(Point(0, 0), 640, 480)
    print(f"  Rect.topleft.x, width, height : {r.topleft.x}, {r.width}, {r.height}")
    print(f"  sizeof(Rect)      : {ctypes.sizeof(Rect)} bytes   (Point + 2 ints)")

    print("--- pointers: pass a pointer so C can read/write your memory ---")
    n = ctypes.c_int(10)
    ptr = ctypes.pointer(n)
    print(f"  ptr.contents.value       : {ptr.contents.value}")
    ptr.contents.value = 20              # write through the pointer
    print(f"  after *ptr = 20, n.value : {n.value}")

    print("--- the rule ---")
    print(f"  ctypes.Structure mirrors C struct layout (contiguous, typed fields);")
    print(f"  pointers let C functions fill in your memory, the standard C idiom")


if __name__ == "__main__":
    main()
