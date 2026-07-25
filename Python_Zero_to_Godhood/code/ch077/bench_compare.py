"""Benchmark 77.1 - constant-time comparison costs a little; timing safety is worth it.

== short-circuits at the first differing byte (fast, but its timing leaks the
match length). compare_digest always compares every byte (constant time, so its
timing leaks nothing). The constant-time guarantee costs a small, bounded overhead
per comparison. This measures both on 32-byte values, so the price of timing safety
is visible, and it is tiny next to the security it buys.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import hmac
a = bytes(range(32))
b = bytes(range(32))               # equal
c = bytes([255]) + bytes(range(1, 32))  # differs at byte 0
"""


def main() -> None:
    results = [
        measure("== (short-circuits)", "a == c", SETUP, number=1000000),
        measure("compare_digest (constant-time)", "hmac.compare_digest(a, c)", SETUP, number=1000000),
    ]
    report("77.1  comparing 32-byte values: == vs constant-time compare_digest",
           results, baseline="== (short-circuits)")

    print()
    print("Reading this. == is faster because it can stop at the first differing")
    print("byte, but that variable timing is exactly the leak: how long == takes")
    print("reveals how many leading bytes matched, letting an attacker recover a")
    print("secret byte by byte. compare_digest always scans every byte, so it costs")
    print("a bit more but its timing is independent of the contents. The overhead is")
    print("a few nanoseconds per comparison, nothing next to the security. Use")
    print("compare_digest for any comparison involving a secret; reserve == for")
    print("non-secret data where timing does not matter.")


if __name__ == "__main__":
    main()
