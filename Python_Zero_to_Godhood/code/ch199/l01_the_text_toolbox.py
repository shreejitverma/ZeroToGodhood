"""Listing 199.1 - the text toolbox: str's verbs, difflib's diffs, textwrap's shapes.

Chapter 117 ended with regex earning its keep only on structure. This chapter
is the toolbox for everything else: the str methods that answer common
questions natively (and correctly, where naive slicing is a bug factory),
difflib for similarity and diffs, and textwrap for shaping prose. The theme
is verb-choice again: every block shows a question, the tool built for it,
and the subtle wrongness of the improvised alternative.
"""

import difflib
import textwrap


def main() -> None:
    print("--- str's verbs: the questions that never needed a regex ---")
    line = "timeout=45 # seconds"
    key, _, rest = line.partition("=")
    value, _, comment = rest.partition("#")
    print(f"  partition twice     : key={key!r}, value={value.strip()!r}, "
          f"comment={comment.strip()!r}")
    path = "v2.report.txt"
    print(f"  removesuffix        : {path.removesuffix('.txt')!r}"
          f"   (slicing [-4:] would eat 'txt' from 'v2.report')")
    print(f"  removeprefix chain  : "
          f"{'debug:net:timeout'.removeprefix('debug:')!r}")
    tricky = "a b\nc"          # LINE SEPARATOR, then newline
    print(f"  splitlines          : {tricky.splitlines()!r}")
    print(f"  split('\\n')         : {len(tricky.split(chr(10)))} parts "
          f"(blind to the Unicode break splitlines saw)")
    print(f"  casefold vs lower   : "
          f"{'Strasse'.casefold() == 'STRASSE'.casefold()} / "
          f"{'Strasse'.lower() == 'STRASSE'.lower()}"
          f"  (both true; but casefold also folds ß -> ss)")
    print(f"    'ß'.casefold() : {'ß'.casefold()!r}   "
          f"'ß'.lower() : {'ß'.lower()!r}")
    print("  partition never raises and always returns three parts; the")
    print("  remove* pair strips EXACT affixes (strip() strips a CHARACTER")
    print("  SET - the classic 'mystring'.strip('my') surprise); casefold is")
    print("  the comparison normaliser, lower the display one (Deep D)")

    print("--- difflib: similarity as longest matching blocks ---")
    a, b = "the quick brown fox", "the quiet brown fax"
    matcher = difflib.SequenceMatcher(None, a, b)
    print(f"  ratio({a!r}, {b!r}) : {matcher.ratio():.3f}")
    blocks = [(m.a, m.b, m.size) for m in matcher.get_matching_blocks()
              if m.size]
    print(f"  matching blocks     : {blocks}")
    candidates = ["timeout", "time_out", "timer", "teardown"]
    print(f"  get_close_matches('timout') : "
          f"{difflib.get_close_matches('timout', candidates)}")
    print("  ratio = 2*matched/total, from greedy longest-block matching -")
    print("  fast and usually right, not an edit distance; close_matches is")
    print("  the did-you-mean in every CLI, three lines from the stdlib")

    print("--- difflib: the diff every tool renders ---")
    old = ["retries = 3", "timeout = 45", "verbose = false"]
    new = ["retries = 5", "timeout = 45", "log_level = info"]
    for diff_line in difflib.unified_diff(old, new, "old.cfg", "new.cfg",
                                          lineterm=""):
        print(f"    {diff_line}")
    print("  unified_diff yields the format git popularised; ndiff adds")
    print("  intra-line detail; HtmlDiff renders review pages - the stdlib")
    print("  ships the whole diff stack, and it streams (Chapter 91)")

    print("--- textwrap: prose as a layout problem ---")
    speech = ("The engine backtracks, the groups record the settlement, "
              "and the benchmark keeps everyone honest.")
    for wrapped in textwrap.wrap(speech, width=44):
        print(f"    |{wrapped}|")
    print(f"  shorten to 40       : "
          f"{textwrap.shorten(speech, width=40, placeholder=' ...')!r}")
    code = "\n    def f():\n        return 1\n"
    print(f"  dedent removes the common margin : "
          f"{textwrap.dedent(code).splitlines()[1:]!r}")
    print("  wrap breaks on spaces (never inside words by default), shorten")
    print("  collapses whitespace THEN truncates at a word boundary, dedent")
    print("  strips only the COMMON leading whitespace - the docstring and")
    print("  heredoc normaliser (and why mixed tabs break it, Chapter 118's")
    print("  edges)")


if __name__ == "__main__":
    main()
