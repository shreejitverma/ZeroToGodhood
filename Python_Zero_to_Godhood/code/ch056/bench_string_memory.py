"""Benchmark 56.1 - one astral character quadruples a large string's memory.

A realistic case: a ~1,000,000-character text document. Pure ASCII it costs ~1 MB
(1 byte/char). Append a single emoji and PEP 393 must store the WHOLE string at 4
bytes/char, so it jumps to ~4 MB, for one extra character. This measures the
footprint of the same-length string at each representation width via
sys.getsizeof (deterministic), so the 4x blowup is visible at scale.

Memory via sys.getsizeof (deterministic). See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 1_000_000


def main():
    print("=== 56.1  string memory by representation width (1,000,000 chars) ===")
    print(provenance())
    print()

    ascii_doc = "a" * N
    bmp_doc = "世" * N
    astral_doc = "\U0001f600" * N
    ascii_plus_one = "a" * (N - 1) + "\U0001f600"

    rows = [
        ("pure ASCII", ascii_doc),
        ("BMP (2-byte)", bmp_doc),
        ("astral (4-byte)", astral_doc),
        ("ASCII + 1 emoji", ascii_plus_one),
    ]
    for label, s in rows:
        size = sys.getsizeof(s)
        print(f"  {label:16} len={len(s):>9,}  {size:>10,} bytes  ({size / N:.1f}/char)")

    ascii_size = sys.getsizeof(ascii_doc)
    plus_one_size = sys.getsizeof(ascii_plus_one)
    print(f"  blowup from one emoji : {plus_one_size / ascii_size:.1f}x "
          f"({ascii_size:,} -> {plus_one_size:,} bytes for one extra character)")

    print()
    print("Reading this. PEP 393 stores a str at the narrowest width that fits its")
    print("widest codepoint, so a pure-ASCII megabyte costs ~1 MB, but a single")
    print("astral character (an emoji) forces the whole string to 4 bytes/char and")
    print("~4 MB. This matters when holding large mostly-ASCII text that may contain")
    print("stray wide characters: memory can quadruple unexpectedly. For bulk text")
    print("storage, keep it as utf-8 bytes (variable-width, ~1 byte/ASCII char) and")
    print("decode to str only the spans you operate on.")


if __name__ == "__main__":
    main()
