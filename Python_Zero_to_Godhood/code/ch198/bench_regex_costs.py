"""Benchmark 198.1 - where regex time goes: compilation, prefixes, and verbs.

  198.1a  the three ways to invoke one pattern: re.search(pattern, text)
          per call (cache lookup each time), a precompiled object, and - the
          baseline nobody benchmarks against - the str method that answers
          the same question. The folklore says "always precompile"; the
          table says the cache is decent, precompiling is better, and for
          plain substring questions `in` beats them all by an order.

  198.1b  the literal-skip optimisation, and what defeats it: the engine
          scans for required literals with a fast substring search before
          running the VM at all. A bare literal rides that path; a leading
          `.*` barely hurts (the engine still finds the literal first); and
          the innocent-looking \\b word boundary DEFEATS the skip, forcing
          per-position checks - the row nobody predicts until measured.

  198.1c  findall against finditer over a big haystack: the materialised
          list against the lazy Match stream (Chapter 91's trade, in re's
          own API).

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402


def main():
    SETUP = """
import re
line = ("x" * 180) + " ERROR code=500"
pair = re.compile(r"(\\w+)=(\\d+)")
error_re = re.compile(r"ERROR")
"""
    rows = [
        measure("'ERROR' in line (str)", "'ERROR' in line", SETUP),
        measure("re.search per call", "re.search(r'ERROR', line)", SETUP),
        measure("precompiled .search", "error_re.search(line)", SETUP),
    ]
    report("198.1a  one question, three invocations", rows,
           baseline="'ERROR' in line (str)")

    print()
    rows = [
        measure("r'ERROR'", "re.search(r'ERROR', line)", SETUP),
        measure(r"r'\bERROR\b'", r"re.search(r'\bERROR\b', line)", SETUP),
        measure("r'.*ERROR.*=(\\d+)'",
                r"re.search(r'.*ERROR.*=(\d+)', line)", SETUP),
    ]
    report("198.1b  the literal-skip path on a 196-char line", rows,
           baseline="r'ERROR'")

    print()
    BIG = """
import re
pair = re.compile(r"(\\w+)=(\\d+)")
haystack = "k=1 " * 20_000
"""
    rows = [
        measure("findall (materialise)", "pair.findall(haystack)",
                BIG, repeat=7, number=50),
        measure("finditer, consumed", "sum(1 for m in pair.finditer(haystack))",
                BIG, repeat=7, number=50),
        measure("finditer, first 10",
                "[m for m, _ in zip(pair.finditer(haystack), range(10))]",
                BIG, repeat=7, number=50),
    ]
    report("198.1c  20,000 matches: list vs stream", rows,
           baseline="findall (materialise)")

    print()
    print("Reading this. For a plain substring question, str's `in` wins -")
    print("regex earns its cost when the QUESTION needs structure (groups,")
    print("classes, alternation), never for literal lookup; and within re,")
    print("the module cache holds up while precompiling shaves the lookup.")
    print("The middle table is the one nobody predicts: the engine pre-scans")
    print("for required literals with a fast substring search, so the bare")
    print("literal and even the .*-dressed pattern ride that path, while the")
    print("innocent \\b boundary DEFEATS the skip and costs 6x - measured, not")
    print("guessed, which is this book's whole point (an earlier draft of")
    print("this file predicted the .* row would be the slow one). And")
    print("finditer's stream wins exactly where Chapter 91 said: early exit")
    print("(first-10 is ~free) and constant memory; findall's list is fine")
    print("until the day the haystack is a gigabyte.")


if __name__ == "__main__":
    main()
