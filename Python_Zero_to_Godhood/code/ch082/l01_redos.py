"""Listing 82.1 - ReDoS: a regex can take EXPONENTIAL time on crafted input.

Python's re engine is a backtracking matcher. A regex with nested or overlapping
quantifiers, like (a+)+, has exponentially many ways to split the input, and on a
string that ALMOST matches but fails at the end, the engine tries them all before
giving up. So a ~30-character input can hang for minutes, a denial-of-service
(ReDoS). The vulnerable regex and a safe equivalent accept/reject the SAME strings;
they differ only in how long the vulnerable one takes to reject a crafted input.
This listing shows the equivalence on SMALL inputs (fast); the benchmark shows the
exponential blowup. It deliberately uses tiny inputs so it cannot hang.
"""

import re

VULN = re.compile(r"(a+)+$")     # nested quantifier: catastrophic backtracking
SAFE = re.compile(r"a+$")        # linear-time equivalent


def main() -> None:
    print("--- both regexes accept/reject the SAME strings ---")
    for s in ["aaaa", "aaab", "", "baaa"]:
        v = bool(VULN.search(s))
        f = bool(SAFE.search(s))
        print(f"  {s!r:8} vuln={v}  safe={f}  agree={v == f}")

    print("--- the difference is COST on a crafted near-match (small n here) ---")
    # "aaaa...!" almost matches a+ but the trailing ! breaks $, forcing backtracking
    for n in (4, 8, 12):
        s = "a" * n + "!"
        print(f"  'a'*{n}+'!' rejected by both : {not VULN.search(s) and not SAFE.search(s)}")

    print("--- the mechanism ---")
    print("  (a+)+ can split 'aaaa' as (aaaa), (aaa)(a), (aa)(aa), ... exponentially")
    print("  on a failing input the engine tries every split before giving up")
    print("  the de-nested a+$ has no nested quantifier: polynomial, not exponential")
    print("  fix: avoid nested/ambiguous quantifiers; bound input length; use timeouts")


if __name__ == "__main__":
    main()
