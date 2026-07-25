"""Listing 39.1 - array: a compact typed sequence, and a buffer-protocol bridge.

A list of ints is a container of POINTERS to separate int objects: 8 bytes per
slot plus ~32 bytes per int object. An array.array stores the raw values inline,
one fixed-width field per element, no per-element object. That makes it far
smaller and lets it export its memory via the buffer protocol (zero-copy to
memoryview, struct, and NumPy). This listing shows the typed nature, the buffer
bridge, and the constraint (one type, checked on insert).
"""

import array


def main() -> None:
    print("--- a typed sequence: one typecode, fixed-width elements ---")
    arr = array.array("q", [10, 20, 30])   # 'q' = signed 64-bit int
    print(f"  array('q')          : {arr.tolist()}")
    print(f"  typecode / itemsize : {arr.typecode} / {arr.itemsize} bytes")
    arr.append(40)
    print(f"  after append(40)    : {arr.tolist()}")

    print("--- the type is enforced (unlike a list) ---")
    try:
        arr.append(3.14)                   # a float into an int array
    except TypeError as e:
        print(f"  append(3.14) -> {type(e).__name__}: {e}")

    print("--- buffer protocol: zero-copy view onto the raw memory ---")
    mv = memoryview(arr)
    print(f"  memoryview format   : {mv.format} (itemsize {mv.itemsize})")
    mv[0] = 99                             # writes through to the array
    print(f"  after mv[0] = 99    : {arr.tolist()}")

    print("--- frombytes/tobytes: the raw little- or big-endian layout ---")
    raw = arr.tobytes()
    print(f"  tobytes() length    : {len(raw)} bytes ({len(arr)} x {arr.itemsize})")
    arr2 = array.array("q")
    arr2.frombytes(raw)
    print(f"  round-trip equal    : {arr2 == arr}")


if __name__ == "__main__":
    main()
