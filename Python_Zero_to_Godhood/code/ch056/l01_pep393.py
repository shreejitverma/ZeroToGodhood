"""Listing 56.1 - PEP 393: a str picks 1, 2, or 4 bytes per character.

Since Python 3.3 (PEP 393, "flexible string representation") a str stores its
characters using the NARROWEST width that fits its widest codepoint: 1 byte if
every character is Latin-1 (<= U+00FF), 2 bytes if the widest is in the Basic
Multilingual Plane (<= U+FFFF), 4 bytes if any character is astral (> U+FFFF,
e.g. most emoji). The width is a property of the WHOLE string, so a single
astral character makes every character in the string cost 4 bytes. This listing
shows the per-width footprint via sys.getsizeof (deterministic).
"""

import sys


def main() -> None:
    n = 1000
    print("--- footprint scales with the widest codepoint, not the content ---")
    for label, s in [
        ("ASCII (a)", "a" * n),
        ("Latin-1 (é)", "é" * n),   # U+00E9, fits 1 byte
        ("BMP (世)", "世" * n),       # U+4E16, needs 2 bytes
        ("astral (😀)", "\U0001f600" * n),  # U+1F600, needs 4 bytes
    ]:
        size = sys.getsizeof(s)
        print(f"  {label:12} len={len(s)} getsizeof={size:5} bytes ({size / n:.1f}/char + header)")

    print("--- one astral character widens the ENTIRE string ---")
    pure_ascii = "a" * 1000
    one_emoji = "a" * 999 + "\U0001f600"
    print(f"  1000 ASCII chars        : {sys.getsizeof(pure_ascii):5} bytes")
    print(f"  999 ASCII + 1 emoji     : {sys.getsizeof(one_emoji):5} bytes (4x: the emoji widened all 1000)")

    print("--- len() is characters, not bytes; indexing is O(1) at any width ---")
    s = "a😀b"
    print(f"  'a😀b' len (characters) : {len(s)}")
    print(f"  utf-8 encoded bytes     : {len(s.encode('utf-8'))} (variable-width on disk)")
    print(f"  s[1] is the emoji       : {s[1] == '\U0001f600'}")


if __name__ == "__main__":
    main()
