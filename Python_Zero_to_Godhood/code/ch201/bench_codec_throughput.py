"""Benchmark 201.1 - the codecs priced: throughput and the expansion they buy.

One megabyte of bytes through each codec's encode and decode. All four are C
loops; the differences are per-symbol work and output size. The table's use
is dimensioning: at these speeds the codec is never the bottleneck of any
I/O path it serves - the EXPANSION is the cost that ships (wire bytes,
storage, JSON bloat), which is why the choice is a channel-and-ratio
decision, not a speed one.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

MB = 1024 * 1024


def main():
    SETUP = f"""
import base64, binascii, os
payload = os.urandom({MB})
hex_form = binascii.hexlify(payload)
b32_form = base64.b32encode(payload)
b64_form = base64.b64encode(payload)
b85_form = base64.b85encode(payload)
"""
    rows = [
        measure("hexlify", "binascii.hexlify(payload)", SETUP,
                repeat=7, number=20),
        measure("unhexlify", "binascii.unhexlify(hex_form)", SETUP,
                repeat=7, number=20),
        measure("b64encode", "base64.b64encode(payload)", SETUP,
                repeat=7, number=20),
        measure("b64decode", "base64.b64decode(b64_form)", SETUP,
                repeat=7, number=20),
        measure("b32encode", "base64.b32encode(payload)", SETUP,
                repeat=7, number=20),
        measure("b85encode", "base64.b85encode(payload)", SETUP,
                repeat=7, number=20),
    ]
    report("201.1  one megabyte through each codec", rows,
           baseline="b64encode")
    print()
    for r in rows:
        gbps = MB / r.min_ns
        print(f"  {r.label:<10} : {gbps:5.2f} GB/s")

    print()
    print("Reading this. The table splits into implementation tiers, not")
    print("alphabet tiers: hex and base64 ride C loops in binascii at")
    print("gigabyte-per-second class, while b32 and b85 are Python-level")
    print("chunk loops at ~25 MB/s - 40-50x out of class, a fact the docs")
    print("never mention and the measurement cannot miss. For digests and")
    print("tokens (bytes, not megabytes) all four are free; for bulk data,")
    print("b64/hex are never the budget line and b32/b85 genuinely can be.")
    print("The cost that always ships is EXPANSION - a 4/3 tax on every")
    print("stored blob and JSON-embedded payload, forever - so choose by")
    print("channel (what characters survive) and ratio, and let base85's 6%")
    print("saving argue against both its alphabet risks and its 40x encode")
    print("bill before believing it.")


if __name__ == "__main__":
    main()
