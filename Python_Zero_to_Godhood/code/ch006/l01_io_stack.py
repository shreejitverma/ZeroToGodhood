"""Listing 6.1 - open() builds a three-layer I/O stack, and each layer is
reachable.

PEP 3116 replaced Python 2's thin stdio wrapper with a composable stack: a raw
FileIO that issues one syscall per call, a BufferedWriter/Reader that batches
syscalls through an in-memory buffer, and a TextIOWrapper that adds the
str<->bytes codec and newline handling. Opening in text mode returns the top
layer; you reach down through .buffer and .buffer.raw.
"""

import io
import tempfile
import os

path = os.path.join(tempfile.mkdtemp(), "demo.txt")

with open(path, "w", encoding="utf-8") as f:
    print("--- the three layers of a text-mode file ---")
    print("  text layer    :", type(f).__name__)
    print("  buffered layer:", type(f.buffer).__name__)
    print("  raw layer     :", type(f.buffer.raw).__name__)
    print("  default buffer:", io.DEFAULT_BUFFER_SIZE, "bytes")
    f.write("hello")

print()
print("--- binary mode drops the text layer: you get bytes directly ---")
with open(path, "rb") as f:
    print("  binary top layer:", type(f).__name__)
    data = f.read()
    print("  read returns    :", type(data).__name__, "->", data)

os.remove(path)
print()
print("crossing the user/kernel boundary is the dominant cost in I/O; the")
print("buffered layer is what collapses many small reads into few syscalls.")
