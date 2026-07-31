"""Listing 261.1 - Python 3.6 (2016): the secrets module, randomness safe for tokens.

For years people generated password-reset tokens, session IDs, and API keys with
the random module - and that is a security hole. random is a Mersenne Twister: a
fast, REPRODUCIBLE pseudo-random generator seeded from a small state, designed
for simulations, not secrecy. Observe enough of its output and you can predict
the rest, and random.seed(0) makes it fully deterministic. Python 3.6's PEP 506
added the secrets module: a cryptographically strong generator (drawing from the
OS entropy source) with token helpers built for exactly this. Deep volumes own
no crypto mechanism; this is the release that gave 'generate an unguessable
token' a correct, obvious home so nobody reaches for random by mistake. This
listing checks structure and the predictability CONTRAST, never raw secret
values. Verified on current interpreters.
"""

import random
import secrets


def main() -> None:
    print("--- the danger: random is REPRODUCIBLE, so its output is guessable ---")
    random.seed(0)
    a = random.random()
    random.seed(0)
    b = random.random()
    print(f"  random.seed(0); random.random() twice equal? : {a == b}")
    print("  seeding random with the same value gives the SAME sequence - by")
    print("  design, for reproducible simulations. for a token that means: know")
    print("  the seed (or enough outputs) and you can reproduce every 'secret'")

    print("--- secrets has no seed: its output cannot be reproduced ---")
    print(f"  secrets module has a seed() function? : {hasattr(secrets, 'seed')}")
    print("  secrets draws from the OS cryptographic entropy source, so there is")
    print("  nothing to seed and nothing to reproduce. that unpredictability is")
    print("  the whole point - it is the correct tool for anything secret")

    print("--- token helpers: the right output shapes for real uses ---")
    hex_token = secrets.token_hex(16)            # 16 bytes -> 32 hex chars
    url_token = secrets.token_urlsafe(16)        # URL-safe base64 text
    raw = secrets.token_bytes(16)
    print(f"  token_hex(16)     length : {len(hex_token)}   (32 hex chars = 16 bytes)")
    print(f"  token_hex is all hex digits : {all(c in '0123456789abcdef' for c in hex_token)}")
    print(f"  token_urlsafe(16) type   : {type(url_token).__name__}")
    print(f"  token_bytes(16)   length : {len(raw)} bytes")
    print("  token_hex for a hex string, token_urlsafe for a URL/cookie value,")
    print("  token_bytes for raw bytes - the shapes session IDs and reset tokens")
    print("  actually need, each cryptographically strong")

    print("--- secrets.choice / randbelow for secure selection ---")
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous 0/O/1/I
    code = "".join(secrets.choice(alphabet) for _ in range(8))
    print(f"  an 8-char secure code drew from the alphabet : "
          f"{all(c in alphabet for c in code)}")
    n = secrets.randbelow(100)
    print(f"  secrets.randbelow(100) is in [0, 100) : {0 <= n < 100}")
    print("  choice() and randbelow() are the secure analogues of random's -")
    print("  use them when the SELECTION must be unpredictable (a one-time code,")
    print("  a temporary password), not just statistically random")

    print("--- compare_digest: constant-time comparison against timing attacks ---")
    good = secrets.compare_digest("expected-token", "expected-token")
    bad = secrets.compare_digest("expected-token", "wrong-token123")
    print(f"  compare_digest(equal)   : {good}")
    print(f"  compare_digest(unequal) : {bad}")
    print("  == on secrets can leak via TIMING: it returns early at the first")
    print("  differing byte, so response time reveals how much of a guess was")
    print("  right. compare_digest takes constant time regardless, closing that")
    print("  side channel - use it to check tokens and signatures")

    print("--- the constraint answered ---")
    print("  the random module is reproducible pseudo-randomness for simulations,")
    print("  and using it for tokens is a real vulnerability. secrets (3.6) gave")
    print("  cryptographically strong generation an obvious home: token_hex/")
    print("  urlsafe/bytes for IDs, choice/randbelow for secure selection, and")
    print("  compare_digest for safe checking. 'unguessable token' got a correct default")


if __name__ == "__main__":
    main()
