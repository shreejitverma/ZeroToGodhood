"""Benchmark 76.1 - a password KDF is slow ON PURPOSE.

sha256 is fast; pbkdf2 with a high iteration count is slow by design. The slowness
is the security feature: it sets the attacker's guess rate. This measures a single
sha256 versus pbkdf2 at 200,000 iterations, and translates each into how many
password guesses per second an attacker could make. Faster hashing means a faster
attacker, which is exactly why passwords need a slow hash.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import hashlib
pw = b"correct horse battery staple"
salt = bytes(range(16))
"""


def main() -> None:
    results = [
        measure("sha256 (single)", "hashlib.sha256(salt + pw).digest()", SETUP, number=100000),
        measure("pbkdf2 (200k iterations)", "hashlib.pbkdf2_hmac('sha256', pw, salt, 200_000)", SETUP, number=30),
    ]
    report("76.1  fast hash vs slow KDF (the slowness is the point)",
           results, baseline="sha256 (single)")

    print()
    print("Reading this. sha256 hashes a password in a few hundred nanoseconds, so")
    print("an attacker who steals the hash database can try MILLIONS of guesses per")
    print("second. pbkdf2 at 200,000 iterations takes tens of milliseconds, cutting")
    print("the attacker to tens of guesses per second, tens of thousands of times")
    print("slower, by design. For passwords the slowness is the security: it makes")
    print("brute force infeasible. Never store a fast unsalted hash of a password;")
    print("use a salted, high-work-factor KDF (scrypt/argon2, or pbkdf2), and tune")
    print("the work factor up as hardware gets faster. (For non-password data")
    print("integrity, a fast hash is correct, this trade is specific to secrets.)")


if __name__ == "__main__":
    main()
