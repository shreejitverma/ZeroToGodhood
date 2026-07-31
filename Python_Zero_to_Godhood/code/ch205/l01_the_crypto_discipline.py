"""Listing 205.1 - the crypto discipline, and the volume closed.

Deep P has minted digests (122), entropy (123), and authentication codes
(Chapter 80's HMAC). This chapter is the discipline that makes them safe to
USE, and the decision procedure that ends the volume. Four rules, each a
one-liner in the stdlib and a CVE without it: compare secrets in CONSTANT
TIME (== leaks the answer through timing); store passwords through a slow,
salted KDF, never a fast hash; authenticate ciphertext (a MAC over the bytes
you will act on); and know what the stdlib does NOT give you (there is no
`encrypt()` - that is a deliberate boundary). Deterministic where it can be,
property-checked where it cannot.
"""

import hashlib
import hmac
import secrets


def main() -> None:
    print("--- compare secrets in constant time ---")
    real = hashlib.sha256(b"the-true-tag").digest()
    guess_right = hashlib.sha256(b"the-true-tag").digest()
    guess_wrong = hashlib.sha256(b"a-forgery").digest()
    print(f"  compare_digest(real, right) : "
          f"{hmac.compare_digest(real, guess_right)}")
    print(f"  compare_digest(real, wrong) : "
          f"{hmac.compare_digest(real, guess_wrong)}")
    print("  '==' on bytes returns at the FIRST differing byte, so an")
    print("  attacker measures how far their guess got and walks the secret")
    print("  in one byte at a time. compare_digest takes the same time")
    print("  whatever differs - the benchmark makes the leak visible")

    print("--- store passwords through a slow, salted KDF ---")
    password = b"correct horse battery staple"
    salt = secrets.token_bytes(16)
    stored = hashlib.pbkdf2_hmac("sha256", password, salt, 200_000)
    print(f"  pbkdf2 derives {len(stored)} bytes from password+salt+iterations")
    ok = hmac.compare_digest(
        stored, hashlib.pbkdf2_hmac("sha256", password, salt, 200_000))
    bad = hmac.compare_digest(
        stored, hashlib.pbkdf2_hmac("sha256", b"wrong", salt, 200_000))
    print(f"  verify correct password : {ok}")
    print(f"  verify wrong password   : {bad}")
    print("  the salt makes two identical passwords store differently (no")
    print("  rainbow tables, no 'these two accounts share a password' leak);")
    print("  the 200,000 iterations make each guess EXPENSIVE - the opposite")
    print("  of Chapter 122's 3 GB/s, on purpose (scrypt/argon2 go further)")

    print("--- authenticate the bytes you will act on ---")
    key = secrets.token_bytes(32)
    message = b"transfer:1500:to:ACME"
    tag = hmac.new(key, message, hashlib.sha256).digest()

    def receive(msg, provided_tag):
        expected = hmac.new(key, msg, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, provided_tag):
            return "REJECTED (bad tag)"
        return f"accepted: {msg.decode()}"

    print(f"  genuine message : {receive(message, tag)}")
    print(f"  tampered message: {receive(b'transfer:9999:to:EVIL', tag)}")
    print("  a MAC binds message to key: without the key you cannot forge a")
    print("  tag, and verification is constant-time (rule 1 again). this is")
    print("  Chapter 80's HMAC applied - authenticate BEFORE you parse or")
    print("  act, never after")

    print("--- what the stdlib deliberately does NOT give you ---")
    print("  there is no hashlib.encrypt / no AES in the standard library:")
    print("  symmetric encryption's footguns (mode choice, nonce reuse,")
    print("  padding oracles) are too sharp for a batteries-included default,")
    print("  so the stdlib ships HASHING, MACS, and KDFs - verify and derive -")
    print("  and points at `cryptography` (PyCA) for encrypt/decrypt")

    print("--- Deep P, closed: the decision procedure ---")
    steps = (
        ("need content identity / integrity?  -> hashlib (122)", ""),
        ("need message authentication?        -> hmac (80, here)", ""),
        ("need to store a password?           -> pbkdf2/scrypt, salted", ""),
        ("need an unguessable value?          -> secrets (123)", ""),
        ("need reproducible randomness?       -> random.Random(seed) (123)", ""),
        ("comparing anything secret?          -> compare_digest, always", ""),
        ("need to ENCRYPT?                     -> leave the stdlib (PyCA)", ""),
    )
    for step, _ in steps:
        print(f"  {step}")
    print("  117 regex, 118 text, 119 csv, 120 codecs, 121 compression,")
    print("  122 hashing, 123 randomness, 124 this: the text-and-bytes")
    print("  toolbox, and the rule under all of it - measure, name your")
    print("  algorithm, and compare secrets in constant time")


if __name__ == "__main__":
    main()
