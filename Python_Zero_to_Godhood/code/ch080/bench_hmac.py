"""Benchmark 80.1 - HMAC costs about two hashes; authentication is cheap.

HMAC computes hash(key XOR opad + hash(key XOR ipad + message)), two hash passes
over (roughly) the message plus a block, so it costs on the order of a plain hash,
low microseconds for a short message. This measures a bare sha256 versus an
HMAC-SHA256 of the same message, so the (small) overhead of authentication is
visible: it is cheap enough to authenticate every message, request, or webhook.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import hashlib, hmac
key = b"shared-secret-key"
msg = b"transfer $100 to alice"
"""


def main() -> None:
    results = [
        measure("sha256 (integrity only)", "hashlib.sha256(msg).digest()", SETUP, number=200000),
        measure("HMAC-SHA256 (authenticated)", "hmac.new(key, msg, hashlib.sha256).digest()", SETUP, number=200000),
    ]
    report("80.1  a plain hash vs an authenticated HMAC of a short message",
           results, baseline="sha256 (integrity only)")

    print()
    print("Reading this. HMAC does two hash passes (an inner and an outer), so it")
    print("costs on the order of a plain hash, roughly a microsecond for a short")
    print("message. That is cheap enough to authenticate EVERY message: a webhook")
    print("payload, an API request, a signed cookie, a queue message. A plain hash")
    print("proves only that data was not corrupted (anyone can recompute it); an")
    print("HMAC proves it came from a key-holder and was not altered. Since the")
    print("cost is negligible, there is no performance reason to skip authentication")
    print("on data that crosses a trust boundary.")


if __name__ == "__main__":
    main()
