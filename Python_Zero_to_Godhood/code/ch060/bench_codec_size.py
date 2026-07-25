"""Benchmark 60.1 - codec choice is a size trade that depends on the script.

Encoding the same 100,000-character document in UTF-8, UTF-16, and UTF-32, for
three scripts. UTF-8 is smallest for ASCII/Latin (1-2 bytes/char) but LARGER than
UTF-16 for CJK (3 vs 2 bytes/char). UTF-32 is always 4 bytes/char. This measures
the encoded byte size (deterministic), so the per-script trade is visible.

Sizes via len(encoded) (deterministic). See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 100_000


def main():
    print("=== 60.1  encoded size by codec and script (100,000 chars) ===")
    print(provenance())
    print()

    docs = [
        ("ASCII", "a" * N),
        ("Latin (é)", "é" * N),
        ("CJK (世)", "世" * N),
    ]
    print(f"  {'script':12} {'utf-8':>10} {'utf-16':>10} {'utf-32':>10}  smallest")
    for name, s in docs:
        u8 = len(s.encode("utf-8"))
        u16 = len(s.encode("utf-16-le"))
        u32 = len(s.encode("utf-32-le"))
        smallest = min([("utf-8", u8), ("utf-16", u16), ("utf-32", u32)], key=lambda t: t[1])[0]
        print(f"  {name:12} {u8:>10,} {u16:>10,} {u32:>10,}  {smallest}")

    print()
    print("Reading this. UTF-8 is smallest for ASCII and Latin text (1-2 bytes per")
    print("character) and is ASCII-compatible with no byte-order concern, which is")
    print("why it is the default for the web, files, and interchange. But for CJK")
    print("text UTF-8 uses 3 bytes/char where UTF-16 uses 2, so UTF-16 is more")
    print("compact for predominantly-CJK content. UTF-32 is always 4 bytes/char,")
    print("simple to index but wasteful, so it is an in-memory form, not a storage")
    print("one. Default to UTF-8; consider UTF-16 only for large CJK-heavy corpora.")


if __name__ == "__main__":
    main()
