"""Listing 78.1 - secrets, not random, for tokens: random is predictable.

random uses the Mersenne Twister, a fast DETERMINISTIC pseudo-random generator:
seed it the same way and it reproduces the exact same sequence, and its entire
internal state (hence all future output) can be reconstructed from a few hundred
observed outputs. That is fine for simulations and sampling, and fatal for
security: a token, password, salt, key, or nonce made with random is predictable.
secrets (and os.urandom) draw from the operating system's cryptographically secure
RNG: unpredictable, unseeded, unreconstructable. This listing shows random's
reproducibility and secrets' unpredictability.
"""

import random
import secrets


def main() -> None:
    print("--- random is deterministic: the same seed reproduces the sequence ---")
    random.seed(42)
    first = [random.randint(0, 999) for _ in range(5)]
    random.seed(42)
    again = [random.randint(0, 999) for _ in range(5)]
    print(f"  seed(42) run 1 : {first}")
    print(f"  seed(42) run 2 : {again}")
    print(f"  identical      : {first == again}  (predictable: bad for secrets)")

    print("--- secrets is unpredictable: no seed, never reproduces ---")
    t1 = secrets.token_hex(8)
    t2 = secrets.token_hex(8)
    print(f"  two tokens differ           : {t1 != t2}")
    print(f"  tokens are 16 hex chars each: {len(t1) == 16 and len(t2) == 16}")
    print(f"  (cannot be reproduced or predicted; drawn from the OS CSPRNG)")

    print("--- the right tool for each job ---")
    print(f"  security (tokens, salts, keys, nonces, passwords) -> secrets / os.urandom")
    print(f"  simulation/sampling/shuffling (reproducibility ok) -> random")
    print(f"  secrets.token_urlsafe / token_hex / token_bytes / choice / randbelow")


if __name__ == "__main__":
    main()
