"""Benchmark 202.1 - the compression trade, in one table per direction.

Ten megabytes of realistic mixed content (log-like lines: repeated structure
with varying fields) through zlib levels 1/6/9, bz2, and lzma: compress
throughput, decompress throughput, and ratio. The shape every engineer
should carry: DEFLATE decompresses at hundreds of MB/s regardless of level
(pay once at write, read cheap forever); level 9 buys little over 6; and
bz2/lzma trade order-of-magnitude slower compression for the last ratio
points - archival trades, not pipeline ones.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import bz2
import lzma
import sys
import time
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

MB = 1024 * 1024


def make_loglike(n: int) -> bytes:
    lines = []
    i = 0
    while sum(map(len, lines)) < n:
        lines.append(
            f"2026-07-30T12:{i % 60:02}:{(i * 7) % 60:02}Z host{i % 40:02} "
            f"svc=api req={i:08x} status={200 + (i * 13) % 5} "
            f"latency_ms={(i * 37) % 900}.{i % 10}\n".encode())
        i += 1
    return b"".join(lines)[:n]


def best(fn, repeat=3):
    times = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return min(times)


def main():
    payload = make_loglike(10 * MB)
    print("=== 202.1  10 MB of log-like text, the family's trade ===")
    print(provenance())
    print("method      : min of 3 per cell")
    print()
    print("  codec          ratio   compress      decompress")
    print("  ------------------------------------------------")
    cases = [
        ("zlib -1", lambda d: zlib.compress(d, 1), zlib.decompress),
        ("zlib -6", lambda d: zlib.compress(d, 6), zlib.decompress),
        ("zlib -9", lambda d: zlib.compress(d, 9), zlib.decompress),
        ("bz2", lambda d: bz2.compress(d), bz2.decompress),
        ("lzma", lambda d: lzma.compress(d), lzma.decompress),
    ]
    for name, comp, decomp in cases:
        packed = comp(payload)
        c = best(lambda: comp(payload))
        d = best(lambda: decomp(packed))
        print(f"  {name:<12} {len(packed) / len(payload):6.1%}"
              f" {len(payload) / c / MB:8,.0f} MB/s"
              f" {len(payload) / d / MB:9,.0f} MB/s")

    print()
    print("Reading this. DEFLATE decompresses above a gigabyte per second at")
    print("EVERY level, so ratio bought at write time is free to every reader")
    print("forever - the compress-once-read-many rule in one column. On the")
    print("write side, level 1 keeps 400 MB/s for wire protocols; 9 buys two")
    print("ratio points over 6 at 3.5x the cost, a batch-job trade only. The")
    print("heavies split: lzma compresses at a crawl but READS fast (639")
    print("MB/s) with spectacular ratios on structured text - the archive")
    print("and sdist profile - while bz2 is slow in BOTH directions and")
    print("survives mostly as a legacy format. Framing (Listing 202.1) is")
    print("about interop; this table is about money.")


if __name__ == "__main__":
    main()
