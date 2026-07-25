"""Listing 59.1 - casefold, not lower, for caseless comparison.

str.lower() maps characters to lowercase for DISPLAY. str.casefold() applies the
Unicode caseless-matching fold, which is more aggressive: it maps the German ß
to 'ss' and the Greek final sigma to a plain sigma, so strings that should match
caselessly actually do. Using lower() to compare 'straße' and 'STRASSE' fails;
casefold() makes them equal. For any caseless comparison, search, or dedup, use
casefold (and normalize first, Chapter 58). This listing shows the difference.
"""

import unicodedata as ud


def caseless_equal(a, b):
    # the robust recipe: normalize, then casefold
    return ud.normalize("NFC", a).casefold() == ud.normalize("NFC", b).casefold()


def main() -> None:
    print("--- casefold folds more than lower ---")
    for s in ["Straße", "ΣΊΣΥΦΟΣ", "Σ"]:
        print(f"  {s!r:12} lower={s.lower()!r:12} casefold={s.casefold()!r}")

    print("--- the German sharp-s case ---")
    print(f"  'ß'.lower()          : {'ß'.lower()!r}  (unchanged)")
    print(f"  'ß'.casefold()       : {'ß'.casefold()!r}  (folds to 'ss')")

    print("--- caseless equality: lower fails, casefold works ---")
    a, b = "straße", "STRASSE"
    print(f"  a.lower() == b.lower()       : {a.lower() == b.lower()}")
    print(f"  a.casefold() == b.casefold() : {a.casefold() == b.casefold()}")

    print("--- Greek final sigma: lower keeps it, casefold folds it ---")
    word = "ΟΔΟΣ"        # ends in capital sigma
    print(f"  'ΟΔΟΣ'.lower()       : {word.lower()!r}  (final sigma form ς)")
    print(f"  'ΟΔΟΣ'.casefold()    : {word.casefold()!r}  (plain sigma σ)")

    print("--- the robust recipe: normalize + casefold ---")
    print(f"  caseless_equal('Straße','STRASSE') : {caseless_equal('Straße', 'STRASSE')}")


if __name__ == "__main__":
    main()
