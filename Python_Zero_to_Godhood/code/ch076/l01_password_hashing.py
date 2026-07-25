"""Listing 76.1 - password hashing: you want a SLOW hash, not a fast one.

For data integrity, a fast hash (SHA-256) is good. For passwords it is a
liability: if the hash database leaks, an attacker with a fast hash can try
millions of guesses per second. A password hash must be DELIBERATELY SLOW, a
key-derivation function (pbkdf2, scrypt, argon2) with a high work factor, so each
guess costs milliseconds and brute force becomes infeasible. It must also be
SALTED (a unique random salt per password) so identical passwords hash
differently and precomputed rainbow tables are useless. This listing shows the
digests (deterministic) and the salt effect; the benchmark shows the speed
difference that is the whole point.
"""

import hashlib


def main() -> None:
    password = b"correct horse battery staple"
    salt = bytes(range(16))          # fixed here for a reproducible digest

    print("--- a fast hash (SHA-256): fine for integrity, WRONG for passwords ---")
    fast = hashlib.sha256(salt + password).hexdigest()
    print(f"  sha256(salt+pw)[:16] : {fast[:16]}")

    print("--- a slow KDF (pbkdf2): deliberately expensive per guess ---")
    slow = hashlib.pbkdf2_hmac("sha256", password, salt, 200_000).hex()
    print(f"  pbkdf2 200k iters[:16]: {slow[:16]}")
    print(f"  same password, but far costlier to compute (the benchmark shows it)")

    print("--- salt: identical passwords hash DIFFERENTLY with different salts ---")
    salt_a = bytes([1]) + bytes(15)
    salt_b = bytes([2]) + bytes(15)
    h_a = hashlib.pbkdf2_hmac("sha256", password, salt_a, 1000).hex()
    h_b = hashlib.pbkdf2_hmac("sha256", password, salt_b, 1000).hex()
    print(f"  same pw, salt A [:16] : {h_a[:16]}")
    print(f"  same pw, salt B [:16] : {h_b[:16]}")
    print(f"  digests differ        : {h_a != h_b}  (rainbow tables defeated)")

    print("--- the rule ---")
    print(f"  store salt + slow-KDF digest; never a fast unsalted hash of a password")
    print(f"  (use scrypt/argon2 or pbkdf2 with a high work factor; verify with compare_digest)")


if __name__ == "__main__":
    main()
