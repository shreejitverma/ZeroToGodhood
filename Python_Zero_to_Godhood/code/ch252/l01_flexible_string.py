"""Listing 252.1 - Python 3.3 (2012): PEP 393, the flexible string representation.

Before 3.3, CPython was compiled in one of two ways. A 'narrow' build stored
each str character in 2 bytes (UTF-16), which could not hold characters above
U+FFFF without error-prone surrogate PAIRS - so len() and indexing were wrong
for emoji and rare scripts. A 'wide' build stored 4 bytes per character always,
correct but wasteful: an all-ASCII string paid 4x. PEP 393 removed the choice.
A str now stores 1, 2, or 4 bytes per character depending ONLY on its LARGEST
code point: pure ASCII pays 1 byte, Basic-Multilingual-Plane text pays 2, and
only text with astral characters pays 4. It is both correct (len/indexing count
code points) and compact (the common case is cheapest). Deep D owns the text
model; this is the release that made str adaptive. This listing measures
per-character cost as a size DELTA, so the numbers are build-independent.
Verified on current interpreters.
"""

import sys


def bytes_per_char(char):
    """Per-char storage: growing the string cancels the fixed header."""
    base = sys.getsizeof(char * 100)
    more = sys.getsizeof(char * 200)
    return (more - base) // 100


def main() -> None:
    print("--- str storage adapts to the widest character (1, 2, or 4 bytes) ---")
    ascii_cost = bytes_per_char("a")             # U+0061 - ASCII
    bmp_cost = bytes_per_char("中")          # U+4E2D CJK - fits in the BMP
    astral_cost = bytes_per_char("\U0001F600")   # U+1F600 emoji - above the BMP
    print(f"  ASCII  ('a')     bytes/char : {ascii_cost}")
    print(f"  BMP    (CJK)     bytes/char : {bmp_cost}")
    print(f"  astral (emoji)   bytes/char : {astral_cost}")
    print("  the width is set by the LARGEST code point in the string: 1 byte")
    print("  for ASCII, 2 for Basic-Multilingual-Plane, 4 for astral. the")
    print("  common case (ASCII/Latin text) pays the least - the point of PEP 393")

    print("--- one astral character upgrades the WHOLE string's width ---")
    plain = "a" * 100
    with_emoji = "a" * 99 + "\U0001F600"         # 99 ASCII + 1 emoji
    print(f"  len(plain)      : {len(plain)}   size heavier? : "
          f"{sys.getsizeof(with_emoji) > sys.getsizeof(plain)}")
    print(f"  len(with_emoji) : {len(with_emoji)}   (still 100 code points)")
    print("  adding one emoji forces every character to 4 bytes, because the")
    print("  buffer is uniform-width. so the size jumps even though only one")
    print("  character changed - width is a property of the whole string")

    print("--- correctness: len and indexing count CODE POINTS, not units ---")
    emoji = "\U0001F600"
    print(f"  len('{emoji}') : {len(emoji)}   (ONE code point, not two)")
    text = "a\U0001F600b"
    print(f"  'a<emoji>b'[2] : {text[2]!r}   (indexing lands on 'b' correctly)")
    print("  on the old NARROW build an astral char counted as 2 units, so")
    print("  len() and indexing were wrong for emoji. PEP 393 stores whole code")
    print("  points, so counting and indexing are correct for ALL text")

    print("--- the two old builds, and why the choice is gone ---")
    print("  narrow build: 2 bytes/char, BROKE on astral chars (surrogate bugs)")
    print("  wide build  : 4 bytes/char always, correct but 4x on ASCII")
    print("  PEP 393     : per-string width - correct like wide, compact like")
    print("  narrow for the common case. there is no longer a narrow/wide flag")

    print("--- the constraint answered ---")
    print("  pre-3.3 you chose narrow (compact but buggy on astral text) or wide")
    print("  (correct but wasteful). PEP 393 made a string pick its width from")
    print("  its largest code point: ASCII pays 1 byte, BMP 2, astral 4, and")
    print("  len/indexing are always correct. str became both correct AND")
    print("  memory-adaptive - the everyday case the cheapest")


if __name__ == "__main__":
    main()
