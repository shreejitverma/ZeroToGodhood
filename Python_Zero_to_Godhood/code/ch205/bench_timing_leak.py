"""Benchmark 205.1 - the timing leak, made visible, and the KDF cost, priced.

  205.1a  the star measurement: compare a 32-byte secret against guesses that
          match it in the first 0, 8, 16, 24, or 32 bytes, timing both `==`
          and hmac.compare_digest across millions of trials. `==` returns at
          the first differing byte, so its time RISES with the shared prefix -
          a signal an attacker amplifies to recover the secret byte by byte.
          compare_digest stays FLAT. Timing side channels are famously hard
          to show in a high-level language; the trick here is a very long
          secret (a few KB) so the per-byte scan dominates interpreter noise.

  205.1b  the KDF cost, on purpose: pbkdf2 at rising iteration counts. Each
          doubling of iterations doubles an attacker's cost and yours
          equally - the dial is set so ONE verification is tolerable and a
          BILLION guesses are not.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import hashlib
import hmac
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

WIDTH = 4096          # long secret so the byte scan dominates
TRIALS = 200_000


def timed_compare(fn, secret, guess):
    best = None
    for _ in range(5):
        t0 = time.perf_counter()
        for _ in range(TRIALS):
            fn(secret, guess)
        dt = time.perf_counter() - t0
        best = dt if best is None or dt < best else best
    return best / TRIALS * 1e9


def main():
    secret = bytes([7]) * WIDTH
    print(f"=== 205.1a  compare a {WIDTH}-byte secret, by shared prefix ===")
    print(provenance())
    print(f"method      : min over 5 batches x {TRIALS:,} compares")
    print()
    print("  mismatch at byte   ==  (ns)   compare_digest (ns)")
    print("  --------------------------------------------------")
    # Every guess differs from the secret; only the POSITION of the first
    # differing byte changes. That position is what `==` leaks. (The full
    # match is not shown: an attacker never holds the whole secret, and
    # memcmp's equal-data path would muddy the trend anyway.)
    for frac in (0.0, 0.25, 0.5, 0.75, 0.99):
        cut = int(WIDTH * frac)
        guess = secret[:cut] + bytes([8]) * (WIDTH - cut)
        eq = timed_compare(lambda a, b: a == b, secret, guess)
        cd = timed_compare(hmac.compare_digest, secret, guess)
        print(f"  {int(frac * 100):>3}% ({cut:>4} B)  {eq:9.0f}   {cd:14.0f}")
    print("  == climbs with the shared prefix (it scans until bytes differ);")
    print("  compare_digest is flat. THAT climb is the side channel - over a")
    print("  network an attacker averages away the noise and reads the secret")

    print()
    print("=== 205.1b  pbkdf2 cost vs iterations (the deliberate slowness) ===")
    password, salt = b"pw", b"salt" * 4
    for iters in (50_000, 100_000, 200_000, 400_000):
        t0 = time.perf_counter()
        hashlib.pbkdf2_hmac("sha256", password, salt, iters)
        dt = (time.perf_counter() - t0) * 1000
        print(f"  {iters:>7,} iterations : {dt:6.2f} ms per verification")

    print()
    print("Reading this. The first table is a real timing side channel shown")
    print("in pure Python - possible only because the 4 KB secret makes the")
    print("byte scan outweigh interpreter noise, which is itself the lesson:")
    print("the leak is smaller in normal code but NEVER zero, and averaging")
    print("recovers it. Use compare_digest for every secret comparison, no")
    print("exceptions, because 'the strings are short' is not a defence. The")
    print("KDF table is the same idea inverted: slowness you IMPOSE. Tune")
    print("iterations so one login costs a few milliseconds (tolerable) and a")
    print("billion offline guesses cost centuries (the point). Deep P ends")
    print("where security always does - not on an algorithm, but on using it")
    print("correctly, in constant time, having named it.")


if __name__ == "__main__":
    main()
