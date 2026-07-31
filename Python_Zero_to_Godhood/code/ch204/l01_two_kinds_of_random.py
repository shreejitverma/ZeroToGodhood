"""Listing 204.1 - randomness: reproducible or unpredictable, never both.

Two modules answer two opposite questions. `random` (Mersenne Twister) is a
DETERMINISTIC sequence with a seed: perfect for simulations, tests, and this
book's own harness - every seeded line below verifies byte-identically on
three interpreters, which IS the reproducibility guarantee, demonstrated.
`secrets` asks the opposite: bits an adversary cannot predict, so its values
cannot appear verbatim in a verified book at all - the listing prints their
PROPERTIES instead, which is the same lesson from the other side.
"""

import random
import secrets
import string


def main() -> None:
    print("--- seeded means reproducible - this page is the proof ---")
    rng = random.Random(42)
    print(f"  Random(42).random() x3 : "
          f"{[round(rng.random(), 6) for _ in range(3)]}")
    print(f"  randrange(1000) x5     : "
          f"{[rng.randrange(1000) for _ in range(5)]}")
    deck = list(range(10))
    rng.shuffle(deck)
    print(f"  shuffle(range(10))     : {deck}")
    print(f"  gauss(0, 1) x3         : "
          f"{[round(rng.gauss(0, 1), 4) for _ in range(3)]}")
    print("  same seed, same sequence, on every interpreter in the matrix -")
    print("  the property simulations and tests build on, and the property")
    print("  that makes these lines verifiable at all")

    print("--- instances, not the module globals ---")
    a, b = random.Random(7), random.Random(7)
    print(f"  two Random(7) agree      : "
          f"{[a.random() for _ in range(3)] == [b.random() for _ in range(3)]}")
    random.seed(7)
    x1, x2 = random.random(), random.random()
    random.seed(7)
    random.random()                      # some OTHER component consumes one
    hijacked = random.random()
    print(f"  module-level, after an interloping call, your first draw")
    print(f"  equals what should have been your SECOND : {hijacked == x2}")
    print("  module functions share ONE hidden global generator: any library")
    print("  that also calls random.random() shifts your sequence. pass a")
    print("  Random(seed) instance through your code; the module namespace is")
    print("  for throwaway scripts")

    print("--- weighted and sampled, still reproducible ---")
    rng = random.Random(3)
    print(f"  choices(ABC, weights=[5,3,1], k=8) : "
          f"{''.join(rng.choices('ABC', weights=[5, 3, 1], k=8))}")
    print(f"  sample(range(100), 5)              : {rng.sample(range(100), 5)}")
    print("  choices draws WITH replacement (weights allowed); sample draws")
    print("  WITHOUT (a k-subset) - mixing them up is the off-by-one of")
    print("  probability code")

    print("--- secrets: the values cannot be on this page ---")
    token = secrets.token_urlsafe(32)
    print(f"  token_urlsafe(32) length : {len(token)} chars "
          f"(43 = ceil(32 * 4/3), Chapter 120's arithmetic)")
    alphabet = set(string.ascii_letters + string.digits + "-_")
    print(f"  alphabet is urlsafe-b64  : {set(token) <= alphabet}")
    tokens = {secrets.token_hex(16) for _ in range(1000)}
    print(f"  1,000 tokens, all unique : {len(tokens) == 1000}")
    print(f"  randbelow(10) in range   : {0 <= secrets.randbelow(10) < 10}")
    print("  secrets reads the OS entropy pool (os.urandom): no seed, no")
    print("  sequence, no reproduction - which is the entire point, and why")
    print("  only PROPERTIES of its output can appear in a verified book")

    print("--- the decision, in one question ---")
    print("  'if someone guessed the next value, would it matter?'")
    print("  no  -> random.Random(seed), passed explicitly, reproducible")
    print("  yes -> secrets (tokens, keys, resets, anything an adversary")
    print("         benefits from predicting) - and Mersenne is RECOVERABLE")
    print("  from 624 outputs, so 'random but it is just a session id' is")
    print("  how prediction attacks begin (Chapter 124 owns the discipline)")


if __name__ == "__main__":
    main()
