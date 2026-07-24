"""Listing 7.1 - str is code points, bytes is octets, and the two never
implicitly convert.

Python 2's str was both a byte string and an ASCII text string, and the
interpreter silently decoded between them, which worked until a non-ASCII byte
appeared and then failed far from its cause. Python 3 makes any implicit mix an
immediate, local TypeError.
"""

print("--- implicit text/bytes mixing is a local TypeError, not a distant one ---")
try:
    b"data" + "string"
except TypeError as exc:
    print("  b'data' + 'string' ->", type(exc).__name__ + ":", exc)

print()
print("--- str is a sequence of code points, not code units ---")
emoji = "\U0001F600"                 # a single astral code point
print("  len('grinning face emoji') :", len(emoji), "(one code point)")
print("  Java would report length 2 (two UTF-16 code units)")

print()
print("--- the encoding is not part of the str; it exists only in bytes ---")
text = "café"
print("  text (str)          :", repr(text), "len", len(text))
print("  text.encode('utf-8'):", text.encode("utf-8"), "len", len(text.encode("utf-8")))
print("  text.encode('latin1'):", text.encode("latin1"), "len", len(text.encode("latin1")))
print()
print("Decode at input, work in str, encode at output: the Unicode sandwich.")
