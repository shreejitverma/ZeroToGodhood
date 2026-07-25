"""Listing 58.1 - Unicode normalization: visually equal is not code-point equal.

The same visible text can have different code points. 'e-acute' can be one
precomposed character (U+00E9) or two (plain 'e' + U+0301 combining acute). They
look identical but are DIFFERENT strings: different length, unequal, different
hash, so a dict keyed by one form misses the other. unicodedata.normalize maps
both to a canonical form: NFC (composed) for equality, NFKC (compatibility)
also folds ligatures, fullwidth, and super/subscripts. Normalize user text on
the boundary before comparing, hashing, deduplicating, or using it as a key.

The two forms are built explicitly from code points so the source is unambiguous.
"""

import unicodedata as ud


def main() -> None:
    composed = "caf\u00e9"        # 'caf' + precomposed 'e-acute' (U+00E9)
    decomposed = "cafe\u0301"     # 'cafe' + combining acute accent (U+0301)

    print("--- two strings, one appearance, different code points ---")
    print(f"  composed   len={len(composed)}  codepoints={[f'U+{ord(c):04X}' for c in composed]}")
    print(f"  decomposed len={len(decomposed)}  codepoints={[f'U+{ord(c):04X}' for c in decomposed]}")
    print(f"  equal?              : {composed == decomposed}")
    print(f"  same hash?          : {hash(composed) == hash(decomposed)}")

    print("--- a dict keyed by one form misses the other ---")
    table = {composed: "found"}
    print(f"  lookup decomposed   : {table.get(decomposed)}")

    print("--- NFC makes them canonically equal ---")
    nfc_c = ud.normalize("NFC", composed)
    nfc_d = ud.normalize("NFC", decomposed)
    print(f"  NFC(composed) == NFC(decomposed): {nfc_c == nfc_d}")
    print(f"  normalized length   : {len(nfc_d)}")

    print("--- NFKC also folds compatibility variants ---")
    print(f"  ligature   'ﬁ'  (U+FB01) -> {ud.normalize('NFKC', 'ﬁ')!r}")
    print(f"  superscript '2' (U+00B2) -> {ud.normalize('NFKC', '2²')!r}")
    print(f"  fullwidth  'A'  (U+FF21) -> {ud.normalize('NFKC', 'Ａ')!r}")


if __name__ == "__main__":
    main()
