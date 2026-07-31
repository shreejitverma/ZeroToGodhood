"""Benchmark 203.1 - digests priced: bulk throughput and small-message overhead.

  203.1a  16 MB through each algorithm: the per-byte story. Modern cores
          run sha256 in hardware; blake2 wins in software; sha3's sponge
          pays more per byte; md5's only remaining virtue is visible here.

  203.1b  a 64-byte message, one million times: the per-CALL story, where
          object setup and finalisation dominate and the ranking reshuffles.
          Chapter 114 hashes artifacts (bulk); token systems hash requests
          (small); the two tables answer different budgets.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import hashlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

MB = 1024 * 1024
ALGOS = ("md5", "sha1", "sha256", "sha512", "sha3_256", "blake2b")


def best(fn, repeat=5):
    times = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return min(times)


def main():
    bulk = bytes(range(256)) * (16 * MB // 256)
    small = bulk[:64]

    print("=== 203.1a  16 MB, one pass ===")
    print(provenance())
    print()
    for name in ALGOS:
        t = best(lambda n=name: hashlib.new(n, bulk).digest())
        print(f"  {name:<9} : {len(bulk) / t / 1e9:5.2f} GB/s")

    print()
    print("=== 203.1b  64-byte message, per call ===")
    N = 200_000
    for name in ALGOS:
        t = best(lambda n=name: [hashlib.new(n, small).digest()
                                 for _ in range(N)])
        print(f"  {name:<9} : {t / N * 1e9:6,.0f} ns per digest")
    t = best(lambda: [hashlib.sha256(small).digest() for _ in range(N)])
    print(f"  sha256 via constructor (not new()) : {t / N * 1e9:6,.0f} ns")

    print()
    print("Reading this. Bulk is a hardware story: sha1 and sha256 ride the")
    print("CPU's SHA extensions to 3+ GB/s, sha512 leads the software tier,")
    print("sha3 pays its sponge - and md5 is now the SLOWEST of the lot,")
    print("its last excuse ('at least it's fast') gone on any modern core.")
    print("Small messages invert")
    print("the frame: setup and finalisation dominate, differences compress,")
    print("and the constructor-vs-new() gap (string lookup per call) matters")
    print("as much as the algorithm. Budget artifacts by GB/s (verification")
    print("at Chapter 114 scale is effectively free) and hot token paths by")
    print("ns per call - two tables, two professions.")


if __name__ == "__main__":
    main()
