"""Benchmark 58.1 - normalize has a fast path for already-normalized text.

A worry about "always normalize on input" is cost. But unicodedata.normalize
detects already-normalized text quickly and returns fast, so normalizing text
that is already NFC is far cheaper than normalizing text that actually needs
recomposition. Since most real text is already NFC, defensive normalization on
the input boundary is cheap in the common case and does real work only when it
must.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import unicodedata as ud
already_nfc = "the quick brown fox jumps over the lazy dog " * 20
# decomposed: 'e' + combining acute, repeated
needs_work = ("caf" + "e\\u0301 ") * 100
"""


def main() -> None:
    results = [
        measure("normalize already-NFC", "ud.normalize('NFC', already_nfc)", SETUP, number=50000),
        measure("normalize decomposed", "ud.normalize('NFC', needs_work)", SETUP, number=50000),
    ]
    report("58.1  unicodedata.normalize: already-NFC vs needs recomposition",
           results, baseline="normalize already-NFC")

    print()
    print("Reading this. normalize is much cheaper on text that is already NFC,")
    print("because it detects that quickly and returns without recomposing. Text")
    print("that actually needs work (decomposed accents) costs several times more,")
    print("but even then it is microseconds. Since most real-world text is already")
    print("NFC, normalizing user input on the boundary is cheap in the common case")
    print("and correct in every case. Normalize on input; do not skip it for fear")
    print("of cost, and do not guard it with is_normalized (normalize's own fast")
    print("path already handles the already-normalized case).")


if __name__ == "__main__":
    main()
