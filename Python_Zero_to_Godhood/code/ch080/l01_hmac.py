"""Listing 80.1 - HMAC: prove a message is authentic and unmodified.

A hash tells you a message was not corrupted; it does NOT tell you WHO sent it,
anyone can recompute a plain hash. An HMAC (hash-based message authentication
code) mixes a SHARED SECRET KEY into the hash, so only someone with the key can
produce a valid MAC. The receiver recomputes the HMAC and compares (in constant
time, Chapter 77): a match proves the message came from a key-holder and was not
altered; any tampering, to the message or the MAC, fails. HMAC is the CORRECT
construction; a naive hash(key + message) is insecure (length-extension attacks).
This listing shows authentication and tamper detection (deterministic MAC).
"""

import hashlib
import hmac


def sign(key, message):
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def verify(key, message, mac):
    expected = hmac.new(key, message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, mac)   # constant-time (Chapter 77)


def main() -> None:
    key = b"shared-secret-key"
    message = b"transfer $100 to alice"

    print("--- sign: an HMAC binds the message to the key ---")
    mac = sign(key, message)
    print(f"  HMAC-SHA256 (first 16) : {mac[:16]}")
    print(f"  deterministic          : {sign(key, message) == mac}")

    print("--- verify: only a valid (key, message, mac) triple passes ---")
    print(f"  valid triple           : {verify(key, message, mac)}")
    print(f"  tampered message       : {verify(key, b'transfer $100 to eve', mac)}")
    print(f"  tampered mac           : {verify(key, message, '00' + mac[2:])}")
    print(f"  wrong key              : {verify(b'attacker-guess', message, mac)}")

    print("--- the rule ---")
    print(f"  authenticate messages/tokens/webhooks with HMAC (shared key)")
    print(f"  verify with compare_digest; a plain hash proves integrity, not origin")
    print(f"  (a naive hash(key+msg) is NOT a secure MAC: use hmac)")


if __name__ == "__main__":
    main()
