"""Listing 160.1 - memoryview: the Python-side handle on someone else's memory.

Chapter 44 handed whole buffers to C. This is the object that makes that safe from the
Python side. A memoryview is not a container; it is a BORROWED VIEW of memory that some
other object owns, plus the metadata C needs to interpret it: format, itemsize, shape,
strides, and whether it is writable and contiguous.

Four properties matter and each is observable:

  ZERO COPY     - slicing a memoryview produces another view; slicing bytes copies.
  REINTERPRET   - .cast() re-reads the same bytes under a different C type.
  NON-CONTIGUOUS- a strided view is legal in Python and NOT directly usable by C.
  EXPORTS       - the owner counts its live views and refuses to move memory while any
                  exist, which is why bytearray.append can raise BufferError.

The last one is the whole safety argument: a borrowed pointer into a buffer that can be
reallocated is a dangling pointer, and CPython prevents it by counting exports rather
than by copying.
"""


def main() -> None:
    print("--- a memoryview borrows; writing through it mutates the owner ---")
    owner = bytearray(b"abcdef")
    view = memoryview(owner)
    view[0] = ord("A")
    print(f"  owner after view[0] = 'A' : {bytes(owner)!r}")
    print(f"  view and owner share memory: {view.obj is owner}")

    print("--- slicing a memoryview is a VIEW; slicing bytes is a COPY ---")
    middle = view[2:5]
    middle[0] = ord("C")
    print(f"  owner after middle[0] = 'C' : {bytes(owner)!r}")
    copied = bytes(owner)[2:5]
    copied_is_independent = copied == b"Cde"
    print(f"  bytes(owner)[2:5] is a copy : {copied_is_independent}")

    print("--- format, itemsize, shape: the metadata C needs ---")
    numbers = bytearray(range(8))
    raw = memoryview(numbers)
    print(f"  raw.format / itemsize / shape : {raw.format} / {raw.itemsize} / {raw.shape}")
    print(f"  raw.nbytes                    : {raw.nbytes}")

    print("--- .cast() reinterprets the SAME bytes under another C type ---")
    words = raw.cast("H")                       # unsigned short, 2 bytes
    quads = raw.cast("Q")                       # unsigned long long, 8 bytes
    print(f"  as 'H' : itemsize {words.itemsize}, shape {words.shape}, nbytes {words.nbytes}")
    print(f"  as 'Q' : itemsize {quads.itemsize}, shape {quads.shape}, nbytes {quads.nbytes}")
    print(f"  no copy was made: same nbytes  : {raw.nbytes == words.nbytes == quads.nbytes}")

    print("--- a strided view is legal in Python and NOT contiguous for C ---")
    every_other = raw[::2]
    print(f"  raw.c_contiguous         : {raw.c_contiguous}")
    print(f"  raw[::2].c_contiguous    : {every_other.c_contiguous}")
    print(f"  raw[::2].tolist()        : {every_other.tolist()}")
    try:
        every_other.cast("H")
    except TypeError as exc:
        print(f"  casting a strided view   : TypeError: {exc}")

    print("--- readonly views: bytes exports one, and it refuses writes ---")
    frozen = memoryview(b"immutable")
    print(f"  memoryview(b'...').readonly : {frozen.readonly}")
    try:
        frozen[0] = 65
    except TypeError as exc:
        print(f"  writing to it               : TypeError: {exc}")
    print(f"  .toreadonly() on a writable view : {memoryview(bytearray(b'ab')).toreadonly().readonly}")

    print("--- the safety mechanism: the owner counts live exports ---")
    grow = bytearray(b"xy")
    grow.append(ord("z"))                       # fine: nothing is looking
    print(f"  append with no view outstanding : {bytes(grow)!r}")
    held = memoryview(grow)
    try:
        grow.append(ord("!"))                   # would reallocate under a live pointer
    except BufferError as exc:
        print(f"  append while a view is live     : BufferError: {exc}")
    held.release()
    grow.append(ord("!"))
    print(f"  append after view.release()     : {bytes(grow)!r}")

    print("--- release is what `with` does, and using a released view raises ---")
    with memoryview(bytearray(b"scoped")) as scoped:
        first = scoped[0]
    try:
        scoped[0]
    except ValueError as exc:
        print(f"  first byte inside the block : {first}")
        print(f"  after the block             : ValueError: {exc}")

    print("--- the rule ---")
    print("  a memoryview is a borrowed pointer plus its metadata; the owner refuses to")
    print("  move memory while a view is live, so release views you are done with")


if __name__ == "__main__":
    main()
