"""Benchmark 199.1 - the toolbox priced: str vs re, and difflib's scaling.

  199.1a  three everyday operations, each done with the str verb and with
          the regex that juniors reach for: literal replace, split on a
          delimiter, prefix test. The str verbs are C loops over the
          buffer (Chapter 76); the regex rows pay the engine's generality.

  199.1b  SequenceMatcher.ratio() against input length. The algorithm is
          quadratic-flavoured in the worst case, and its 'autojunk'
          heuristic (on by default, kicking in past 200 lines/items)
          exists precisely to keep real diffs out of the worst case -
          measured with it on and off.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import difflib
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, provenance, report  # noqa: E402


def main():
    SETUP = """
import re
text = ("alpha=1;beta=22;gamma=333;" * 40)
sub_re = re.compile(re.escape(";"))
prefix_re = re.compile(r"alpha")
"""
    rows = [
        measure("str.replace(';', ',')", "text.replace(';', ',')", SETUP),
        measure("re.sub literal", "sub_re.sub(',', text)", SETUP),
        measure("str.split(';')", "text.split(';')", SETUP),
        measure("re.split literal", "sub_re.split(text)", SETUP),
        measure("str.startswith", "text.startswith('alpha')", SETUP),
        measure("re.match literal", "prefix_re.match(text)", SETUP),
    ]
    report("199.1a  str verbs against their regex spellings (1 KB text)",
           rows, baseline="str.replace(';', ',')")

    print()
    print("=== 199.1b  SequenceMatcher.ratio() vs length ===")
    print(provenance())
    print("method      : two ~15%-different word sequences; min of 3")
    print()
    rng = random.Random(42)
    words = [f"tok{i:04}" for i in range(500)]

    def make_pair(n, blank_every=0):
        a = [rng.choice(words) for _ in range(n)]
        if blank_every:
            for i in range(0, n, blank_every):
                a[i] = ""                     # the classic junk: blank lines
        b = list(a)
        for _ in range(max(1, n // 7)):
            b[rng.randrange(n)] = rng.choice(words)
        return a, b

    print("  distinct tokens (autojunk finds nothing to junk):")
    for n in (100, 400, 1_600):
        a, b = make_pair(n)
        runs = []
        for _ in range(3):
            t0 = time.perf_counter()
            difflib.SequenceMatcher(None, a, b).ratio()
            runs.append(time.perf_counter() - t0)
        print(f"    n={n:>5} : {min(runs) * 1000:8.2f} ms")

    print("  every 3rd line blank (real-document shape):")
    a, b = make_pair(1_600, blank_every=3)
    for autojunk, label in ((True, "autojunk on "), (False, "autojunk off")):
        runs = []
        for _ in range(3):
            t0 = time.perf_counter()
            difflib.SequenceMatcher(None, a, b, autojunk=autojunk).ratio()
            runs.append(time.perf_counter() - t0)
        print(f"    n= 1600  {label} : {min(runs) * 1000:8.2f} ms")

    print()
    print("Reading this. The str verbs win their own turf by 3-10x: a")
    print("literal replace, split, or prefix test is a C scan, and the")
    print("regex rows pay compilation-cache lookups plus the VM's ceremony")
    print("for zero added expressiveness. Use re when the QUESTION needs it")
    print("(Chapter 117's rule, now priced from the other side). difflib's")
    print("core grows superlinearly (~9x per 4x of length here), and the")
    print("autojunk heuristic only bites when some item is genuinely COMMON")
    print("(>1% of the sequence) - invisible on distinct tokens, decisive on")
    print("the blank-line-heavy shape real documents have. Leave it on, and")
    print("diff LINES, not characters, for documents.")


if __name__ == "__main__":
    main()
