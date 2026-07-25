"""Benchmark 82.1 - catastrophic backtracking is exponential in the input length.

The vulnerable regex (a+)+$ takes roughly DOUBLE the time for each extra character
of a crafted near-match, exponential growth. The de-nested equivalent a+$ (which
accepts the SAME strings) is polynomial, at these input sizes, effectively instant.
This measures both at the same increasing lengths (bounded so the benchmark cannot
hang), so the vulnerable regex's doubling is visible next to the safe one's
flatness.

(Note: a+$ with .search() is still O(n^2) on very large adversarial input, because
search retries each start position, so bounding input length and anchoring matter
too, see the chapter. But it is never exponential.)

Does its own timing, with a hard cap on n, guarded by __main__. See _harness/bench.py.
"""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

VULN = re.compile(r"(a+)+$")     # nested quantifier: EXPONENTIAL backtracking
SAFE = re.compile(r"a+$")        # de-nested equivalent: polynomial (fast here)


def best(pattern, text, reps=1):
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        pattern.search(text)
        times.append(time.perf_counter() - t0)
    return min(times)


def main():
    print("=== 82.1  (a+)+$ (exponential) vs a+$ (polynomial) on a near-match ===")
    print(provenance())
    print()

    print(f"  {'n':>3}  {'(a+)+$ vuln':>14}  {'factor':>7}  {'a+$ safe':>12}")
    prev = None
    for n in range(14, 23):          # capped at 22 so the bench stays bounded
        s = "a" * n + "!"
        vt = best(VULN, s)
        st = best(SAFE, s)
        factor = f"{vt / prev:4.1f}x" if prev else "    -"
        print(f"  {n:>3}  {vt * 1000:11.2f} ms  {factor:>7}  {st * 1e6:9.1f} us")
        prev = vt

    print()
    print("Reading this. Each extra 'a' roughly DOUBLES the vulnerable regex's time:")
    print("it is exponential, so n=22 is already ~0.2 s, n=30 would be minutes, n=40")
    print("hours. An attacker who can send a ~30-character string to a service using")
    print("such a regex can hang a worker indefinitely, a denial-of-service (ReDoS).")
    print("The de-nested a+$ stays in microseconds at the same lengths. Fixes: avoid")
    print("nested/overlapping quantifiers ((a+)+, (a|a)*, (.*)*); ALSO bound input")
    print("length and anchor (^...$), since even a+$ with search is O(n^2) on huge")
    print("input; set a timeout; or use a linear-time engine (re2). Never run an")
    print("untrusted-input regex that can backtrack catastrophically.")


if __name__ == "__main__":
    main()
