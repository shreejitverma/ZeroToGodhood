"""Listing 7.2 - PEP 393 stores each string in the narrowest width that fits its
largest code point.

Through Python 3.2 a build stored every string in one fixed width chosen at
compile time: a narrow build used 2 bytes/char (and mishandled astral
characters), a wide build used 4 (and made ASCII cost 4x). PEP 393 (3.3) picks
per string, at creation, from three kinds: 1 byte (Latin-1 range, with an ASCII
fast path), 2 bytes (BMP), or 4 bytes (full Unicode). The result is correct O(1)
indexing for all code points and compact memory, with no build-time tradeoff.

The C structs behind the three kinds are PyASCIIObject and
PyCompactUnicodeObject; their full layout is Deep D. Here we watch the size
change with the data.
"""

import sys

print("--- one non-ASCII code point promotes the whole string to a wider kind ---")
cases = [
    ("ASCII      'hello'", "hello"),          # max U+0068 -> 1 byte/char, ASCII header
    ("Latin-1    'hn~'",  "hñ"),         # max U+00F1 -> 1 byte/char, wider header
    ("BMP/UCS-2  'h+CJK'", "h你"),        # max U+4F60 -> 2 bytes/char
    ("Astral/UCS-4 'h+emoji'", "h\U0001F600"),  # max U+1F600 -> 4 bytes/char
]
for label, s in cases:
    print(f"  {label:24} len={len(s)} getsizeof={sys.getsizeof(s)}")
print(f"  {'empty str':24} len=0 getsizeof={sys.getsizeof('')}")

print()
print("Read the numbers: pure ASCII is cheapest (compact header + 1 byte/char +")
print("a NUL). A single non-ASCII code point promotes the ENTIRE string to a")
print("wider kind with a larger header. len() and indexing are always O(1) and")
print("always in code points, so there are no surrogate-pair surprises, but one")
print("emoji in a megabyte of ASCII promotes the whole megabyte to 4 bytes/char.")
