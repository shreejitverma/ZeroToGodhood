"""Benchmark 62.1 - translate (one pass) vs chained replace (N passes).

Removing a set of punctuation characters from text, two ways: chained str.replace
(one call per character, each a full scan and a new allocation) versus a single
str.translate with a deletion table. translate does one pass regardless of how
many characters are removed, so its advantage grows with the size of the character
set.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
text = "hello, world! this is a test string with punctuation. " * 100
puncts = ",.!?;:"
table = str.maketrans("", "", puncts)

def via_replace():
    s = text
    for p in puncts:
        s = s.replace(p, "")
    return s

def via_translate():
    return text.translate(table)
"""


def main() -> None:
    results = [
        measure("translate (1 pass)", "via_translate()", SETUP, number=20000),
        measure("chained replace (6 passes)", "via_replace()", SETUP, number=20000),
    ]
    report("62.1  removing punctuation: translate vs chained replace",
           results, baseline="translate (1 pass)")

    print()
    print("Reading this. translate walks the string once, mapping each character")
    print("through a table, and allocates one result. Chained replace walks the")
    print("string once PER character removed and allocates a new string each time,")
    print("so its cost grows with the size of the character set. For mapping or")
    print("deleting many characters, use str.translate with str.maketrans; reserve")
    print("str.replace for one or two specific substrings (translate is per-")
    print("character, not per-substring).")


if __name__ == "__main__":
    main()
