"""Listing 40.1 - files: text vs binary, encoding, buffering, and the with-block.

open() returns a file object layered over an OS file descriptor. Three choices
define its behavior: mode ('r'/'w'/'a' and 't'/'b'), encoding (text mode only),
and buffering (how much is batched before a write syscall). The with-statement
guarantees the buffer is flushed and the descriptor closed. This listing shows
the round-trips and the invariants; the benchmark shows what buffering costs.
"""

import io
import tempfile
from pathlib import Path


def main() -> None:
    d = Path(tempfile.mkdtemp())

    print("--- text mode: str in, str out, via an encoding ---")
    p = d / "text.txt"
    p.write_text("café\nnaïve\n", encoding="utf-8")
    print(f"  read back           : {p.read_text(encoding='utf-8')!r}")
    print(f"  on disk (bytes)     : {p.read_bytes()!r}")   # utf-8: é is 2 bytes

    print("--- binary mode: bytes in, bytes out, no encoding ---")
    pb = d / "data.bin"
    pb.write_bytes(b"\x00\x01\x02\xff")
    print(f"  read back           : {pb.read_bytes()!r}")

    print("--- the buffering parameter: what is batched before a syscall ---")
    # buffering=0 is only legal in binary mode; it is unbuffered
    with open(d / "raw.bin", "wb", buffering=0) as f:
        n = f.write(b"unbuffered")
        print(f"  unbuffered write    : {n} bytes, no batching")
    # default text mode is block-buffered; line-buffered flushes on newline
    with open(d / "line.txt", "w", buffering=1) as f:
        print(f"  line-buffered       : flushes to the OS on every newline")

    print("--- newline translation is a text-mode behavior ---")
    raw = (d / "nl.txt")
    with open(raw, "w", newline="") as f:      # newline='' disables translation
        f.write("a\nb\n")
    print(f"  newline='' bytes    : {raw.read_bytes()!r}")

    print("--- with-block guarantees flush + close even on error ---")
    buf = io.StringIO()
    with buf:                                   # same protocol as a file
        buf.write("in-memory file")
        print(f"  StringIO value      : {buf.getvalue()!r}")


if __name__ == "__main__":
    main()
