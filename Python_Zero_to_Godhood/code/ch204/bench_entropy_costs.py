"""Benchmark 204.1 - the price of each kind of random.

  204.1a  per value: Mersenne draws against SystemRandom (the OS pool via
          the same API) against secrets' tokens. The PRNG is arithmetic;
          the system rows cross into the kernel; the gap is the cost of
          unpredictability, per value.

  204.1b  in bulk: getrandbits against os.urandom for a megabyte of bits.
          The kernel amortises beautifully in bulk - the per-call syscall
          tax, not entropy itself, is what 204.1a priced.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402


def main():
    SETUP = """
import os, random, secrets
mersenne = random.Random(42)
system = random.SystemRandom()
"""
    rows = [
        measure("mersenne.random()", "mersenne.random()", SETUP),
        measure("mersenne.randrange(1000)", "mersenne.randrange(1000)", SETUP),
        measure("system.random()", "system.random()", SETUP,
                repeat=9, number=5_000),
        measure("secrets.token_bytes(16)", "secrets.token_bytes(16)", SETUP,
                repeat=9, number=5_000),
        measure("secrets.token_urlsafe(16)", "secrets.token_urlsafe(16)",
                SETUP, repeat=9, number=5_000),
    ]
    report("204.1a  one value at a time", rows,
           baseline="mersenne.random()")

    print()
    MB = 1024 * 1024
    bulk = [
        measure("getrandbits(8M) [PRNG]",
                f"mersenne.getrandbits({8 * MB})",
                SETUP, repeat=7, number=5),
        measure("os.urandom(1 MB) [kernel]",
                f"os.urandom({MB})",
                SETUP, repeat=7, number=5),
    ]
    report("204.1b  a megabyte of bits", bulk,
           baseline="os.urandom(1 MB) [kernel]")

    print()
    print("Reading this. The Mersenne draw is tens of nanoseconds of pure")
    print("arithmetic; the system rows pay a kernel crossing per call, the")
    print("microsecond-class tax that IS the price of unpredictability at")
    print("retail. In bulk the kernel amortises to memory-ish speeds, so")
    print("the design rule is the grain rule yet again (Chapter 100): draw")
    print("secrets in sensible units (a 16-byte token is one crossing, not")
    print("sixteen), never loop secrets.choice for bulk material, and keep")
    print("simulations on seeded Mersenne instances where a value costs")
    print("less than the loop that wants it.")


if __name__ == "__main__":
    main()
