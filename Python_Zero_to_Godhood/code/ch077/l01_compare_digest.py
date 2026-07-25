"""Listing 77.1 - constant-time comparison: hmac.compare_digest, not ==.

Comparing bytes/str with == SHORT-CIRCUITS: it returns False at the first differing
byte. So the time == takes leaks HOW MANY leading bytes matched. An attacker
comparing guesses against a secret (a token, an HMAC, an API key) can measure that
timing and recover the secret one byte at a time, a timing attack. hmac.compare_digest
(also secrets.compare_digest) compares in CONSTANT TIME: it always examines every
byte regardless of where they differ, so its duration reveals nothing about the
contents. Use it for ANY comparison where one side is secret. This listing uses
fixed bytes (real use compares secrets) so the results are reproducible.
"""

import hmac


def main() -> None:
    secret = bytes.fromhex("a1b2c3d4e5f60718")
    correct = bytes.fromhex("a1b2c3d4e5f60718")   # equal
    wrong_last = bytes.fromhex("a1b2c3d4e5f60700")  # differs only in the LAST byte
    wrong_first = bytes.fromhex("00b2c3d4e5f60718")  # differs in the FIRST byte

    print("--- compare_digest gives the correct answer, in constant time ---")
    print(f"  compare_digest(secret, correct)    : {hmac.compare_digest(secret, correct)}")
    print(f"  compare_digest(secret, wrong_last) : {hmac.compare_digest(secret, wrong_last)}")
    print(f"  compare_digest(secret, wrong_first): {hmac.compare_digest(secret, wrong_first)}")

    print("--- == gives the same ANSWER but leaks timing (short-circuits) ---")
    print(f"  secret == correct     : {secret == correct}")
    print(f"  secret == wrong_first : {secret == wrong_first}  (== stops at byte 0)")
    print(f"  secret == wrong_last  : {secret == wrong_last}  (== scanned all 8 bytes)")
    print(f"  same results, but == returns FASTER for wrong_first than wrong_last")

    print("--- the rule ---")
    print(f"  compare secrets (tokens, HMACs, digests, API keys) with compare_digest")
    print(f"  never with ==, which reveals the match length through its timing")
    print(f"  (compare_digest requires equal-length inputs of the same type)")


if __name__ == "__main__":
    main()
