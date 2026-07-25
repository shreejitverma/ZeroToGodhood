"""Listing 62.1 - str.translate: one table-driven pass for bulk char mapping.

To map or delete many characters, the obvious code chains str.replace: one call
per character, each scanning the whole string and allocating a new one. str.translate
does it in a SINGLE pass driven by a translation table (built with str.maketrans):
map characters to others, or to None to delete them. Same result, far less work.
This listing shows mapping and deletion; the benchmark shows the speed difference.
"""


def main() -> None:
    print("--- maketrans + translate: map characters in one pass ---")
    # map vowels to their uppercase, in one table
    table = str.maketrans("aeiou", "AEIOU")
    print(f"  'education'.translate  : {'education'.translate(table)!r}")

    print("--- delete characters: map them to None (third maketrans arg) ---")
    strip_punct = str.maketrans("", "", ",.!?;:")
    print(f"  strip punctuation      : {'a,b.c!d?e'.translate(strip_punct)!r}")

    print("--- map some, delete others, in the SAME table ---")
    combined = str.maketrans({"-": " ", "_": " ", "@": None})  # dict form
    print(f"  'a-b_c@d'.translate    : {'a-b_c@d'.translate(combined)!r}")

    print("--- equivalence with chained replace (translate does it in one pass) ---")
    text = "hello, world! a test."
    via_replace = text
    for p in ",.!?;:":
        via_replace = via_replace.replace(p, "")
    via_translate = text.translate(str.maketrans("", "", ",.!?;:"))
    print(f"  chained replace result : {via_replace!r}")
    print(f"  translate result       : {via_translate!r}")
    print(f"  identical              : {via_replace == via_translate}")


if __name__ == "__main__":
    main()
