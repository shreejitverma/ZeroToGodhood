"""Benchmark 78.1 - secrets is slower than random, and that is the right trade.

random draws from a fast in-process PRNG (Mersenne Twister); secrets draws from
the OS cryptographically secure RNG (backed by an entropy source). So secrets is
slower per draw. But for security you need unpredictability, not speed, and the
per-token cost is negligible next to what a token protects. This measures a 64-bit
draw from each.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import random, secrets
"""


def main() -> None:
    results = [
        measure("random.getrandbits(64)", "random.getrandbits(64)", SETUP, number=500000),
        measure("secrets.randbits(64)", "secrets.randbits(64)", SETUP, number=500000),
    ]
    report("78.1  a 64-bit draw: fast PRNG (random) vs CSPRNG (secrets)",
           results, baseline="random.getrandbits(64)")

    print()
    print("Reading this. random is far faster because it is a simple in-process")
    print("pseudo-random generator; secrets draws from the operating system's")
    print("cryptographically secure RNG, which costs more per draw. For security")
    print("that cost is the right trade: you need UNPREDICTABILITY, and a token or")
    print("key is generated rarely, so hundreds of nanoseconds is nothing. Use")
    print("secrets (or os.urandom) for anything an attacker must not guess; use")
    print("random only where predictability is acceptable (simulations, sampling)")
    print("and reproducibility is often even desirable.")


if __name__ == "__main__":
    main()
