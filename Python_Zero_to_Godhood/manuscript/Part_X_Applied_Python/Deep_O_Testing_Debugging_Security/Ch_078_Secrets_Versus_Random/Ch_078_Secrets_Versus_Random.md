# Chapter 78: `secrets` versus `random`

A developer generates password-reset tokens with `random.randint` or `"".join(random.choice(chars) ...)`,
because `random` is the obvious module and it works, the tokens look random. They are not. `random` uses the
**Mersenne Twister**, a fast *deterministic* pseudo-random generator: seed it the same way and it reproduces the
*exact* same sequence, and its entire internal state, and therefore all of its future output, can be
reconstructed from a few hundred observed outputs. So an attacker who sees a handful of your "random" tokens can
predict the next one, and take over the next account whose reset token you issue. The fix is `secrets` (or
`os.urandom`), which draws from the operating system's **cryptographically secure** RNG: unpredictable,
unseeded, unreconstructable. `secrets` is slower, ~**20x** measured, because it consults the OS entropy source
rather than a fast in-process PRNG, but for a token you generate rarely, that cost is nothing, and the
unpredictability is everything.

This chapter continues **Deep O** with the RNG choice: why `random` is predictable and unsafe for secrets, why
`secrets` is unpredictable and slower, and the clean split between them. It is the generation counterpart to
Chapter 76 (hashing) and Chapter 77 (comparison), together, how secrets are made, stored, and checked.

## Section index

- **78.1** Predictable vs unpredictable
- **78.2** Why `random` is unsafe for secrets
- **78.3** Measurement: the cost of a secure draw
- **78.4** Edges and failure modes
- **78.5** Connections
- **78.6** Exercises
- **78.7** Summary and cross-references

Listings live under `code/ch078/` and are re-executed by `make verify` on both interpreters.

---

## 78.1 Predictable vs unpredictable

```python
# code/ch078/l01_secrets_vs_random.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- random is deterministic: the same seed reproduces the sequence ---
  seed(42) run 1 : [654, 114, 25, 759, 281]
  seed(42) run 2 : [654, 114, 25, 759, 281]
  identical      : True  (predictable: bad for secrets)
--- secrets is unpredictable: no seed, never reproduces ---
  two tokens differ           : True
  tokens are 16 hex chars each: True
  (cannot be reproduced or predicted; drawn from the OS CSPRNG)
--- the right tool for each job ---
  security (tokens, salts, keys, nonces, passwords) -> secrets / os.urandom
  simulation/sampling/shuffling (reproducibility ok) -> random
  secrets.token_urlsafe / token_hex / token_bytes / choice / randbelow
```

`random` is **deterministic**: `random.seed(42)` followed by the same draws produces the identical sequence
`[654, 114, 25, 759, 281]` every time, on both runs and both interpreters. That reproducibility is a *feature*
for simulations (you can replay an experiment), and a *fatal flaw* for secrets, because anything reproducible
from a seed is predictable to whoever knows or recovers the seed or state.

`secrets` is **unpredictable**: it has no seed, and two `token_hex(8)` calls produce different tokens that cannot
be reproduced. It draws from the OS cryptographically secure RNG (`/dev/urandom`, `getrandom`, `CryptGenRandom`),
seeded from hardware entropy and designed so that observing outputs reveals nothing about past or future ones.
The bottom block is the whole chapter in three lines: **use `secrets`/`os.urandom` for anything a security
depends on, tokens, salts, keys, nonces, passwords, and `random` only where predictability is acceptable**, and
`secrets` provides the ready-made helpers (`token_urlsafe`, `token_hex`, `token_bytes`, `choice`, `randbelow`).

---

## 78.2 Why `random` is unsafe for secrets

The Mersenne Twister is an excellent *statistical* generator, its output passes randomness tests, has a huge
period, and is fast, but it is not *cryptographically* secure, and the two properties are different. Statistical
randomness means the output *looks* random (no detectable bias or short cycles). Cryptographic security means an
attacker who sees some output *cannot predict the rest*. The Mersenne Twister fails the second: its state is 624
32-bit words, and once an attacker observes 624 consecutive outputs, they can reconstruct the *entire* state and
compute every future (and past) value exactly. Even without 624 outputs, a *seed* chosen predictably (the
current time, a small integer, a PID) can be brute-forced.

So `random`-generated secrets are guessable in ways that have caused real breaches: session tokens predicted from
a few observed ones, "random" passwords reconstructed from the seed, shuffles reversed. The vulnerability is not
that `random` is *biased*, it is that it is *predictable*, and a secret's only job is to be unpredictable.
`secrets` and `os.urandom` are built for exactly this: no user-visible seed, backed by the OS CSPRNG, with a
security guarantee that outputs are computationally infeasible to predict. `random.SystemRandom` is the same OS
source wearing the `random` API, if you need `random`'s interface with `secrets`' security.

The rule: **the moment a value must be unguessable by an attacker, generate it with `secrets` (or
`os.urandom`).** Tokens (reset, session, CSRF, API), salts, keys, IVs/nonces, one-time codes, temporary
passwords, all `secrets`. Reserve `random` for simulations, sampling, shuffling, procedural generation, and
tests, where predictability is harmless and reproducibility (via a seed) is often *desirable*. Choosing `random`
for a secret is not a performance optimization; it is a vulnerability.

---

## 78.3 Measurement: the cost of a secure draw

**Methodology.** `code/ch078/bench_rng.py`. A 64-bit draw from `random.getrandbits` (Mersenne Twister) versus
`secrets.randbits` (OS CSPRNG). `min` per call; ratio relative to `random`. The `secrets` draw involves the OS
entropy source, whose latency is variable, so this is noisier than a pure in-process microbenchmark. CPython
3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| 64-bit draw | min per call | ratio |
|---|---|---|
| `random.getrandbits(64)` | **~32 ns** | 1.00x |
| `secrets.randbits(64)` | **~780 ns** | **~20x** |

`random` draws in **~32 ns** (a fast in-process state update); `secrets` takes **~780 ns**, roughly **20x** more
(and noisy, the OS RNG latency varies), because it consults the operating system's CSPRNG rather than an
in-process PRNG. The ratio is real but the *absolute* cost is sub-microsecond, and it is paid *per secret
generated*, which is rare: you mint a token once per login or reset, not millions of times in a loop.

The rule inverts the usual optimization, as with the rest of Deep O: **pay the ~20x for unpredictability; it is
negligible and it is the point.** The `random` speed advantage is irrelevant to token generation (a per-request
sub-microsecond cost) and buys nothing but a predictable secret. If you are generating so many secure random
values that ~780 ns each matters (a rare, high-throughput case), draw a larger block from `os.urandom` at once
rather than reaching for the insecure `random`. Match the generator to the requirement: unpredictable secrets
from `secrets`, fast reproducible pseudo-randomness from `random`, and never confuse "looks random" (statistical)
with "unguessable" (cryptographic).

---

## 78.4 Edges and failure modes

**`random` for tokens/keys/salts.** §78.2. Predictable; a few outputs (or a guessable seed) recover the whole
sequence. Use `secrets`/`os.urandom`.

**Seeding for "extra randomness".** Seeding `random` with the time or a counter makes it *more* predictable (the
seed is guessable). Never seed a generator you use for secrets; use `secrets`, which has no seed.

**`random.shuffle` for a security-sensitive order.** Shuffling a deck for real-money play, or ordering anything
an attacker benefits from predicting, with `random` is exploitable. Use `random.SystemRandom().shuffle` or a
`secrets`-based shuffle.

**Small token space.** `secrets` is only as strong as the number of bits you draw. A 4-digit `secrets`-generated
code is still brute-forceable (10^4 values); use enough entropy (`token_urlsafe(32)` for a strong token) and
rate-limit short codes.

**Reusing a nonce/IV.** A cryptographic nonce must be unique per use; even from `secrets`, reusing one breaks the
cryptosystem. Generate a fresh one each time, and ensure the space is large enough to avoid collisions.

**`os.urandom` vs `secrets` confusion.** Both draw from the OS CSPRNG; `secrets` is the higher-level convenience
(`token_*`, `choice`, `randbelow`) built on it. Use `secrets` for the ergonomics; `os.urandom` when you need raw
bytes.

---

## 78.5 Connections

**Backward.** The salts this generates feed the password hashing of Chapter 76; the tokens it makes are compared
with the constant-time comparison of Chapter 77, the three Deep O chapters form the secret lifecycle (generate,
store, verify). The `bytes`/hex of tokens are Chapters 37 and 7. The OS entropy source is a Deep R (OS) topic.

**Forward.** HMAC, symmetric/asymmetric crypto, and key management (which all need secure randomness) are Deep P.
Rate-limiting and abuse prevention around tokens are Deep O/Deep U. Testing that no security path uses `random`
is Deep O's security-testing material.

**Across books.** Secure randomness is a boundary Book II enforces wherever it mints something an attacker must
not guess, before it reaches **Book III**. A **Book III** service generates API keys, session tokens, and salts
with `secrets`, and uses `random` (seeded, for reproducibility) only in its *simulations, sampling, and tests*,
data augmentation, stochastic sampling of model outputs, shuffling training data, where predictability is fine or
wanted. The §78.1 predictability of `random` is exactly the trap that makes "random" tokens forgeable, which
**Deep U** guards against at the auth seam. **Deep P** owns the crypto that consumes this randomness.

---

## 78.6 Exercises

**1. Show the predictability.** Reproduce §78.1: seed `random` twice and confirm it repeats, then show `secrets`
tokens differ. Explain what "reproducible from a seed" means for a secret.

**2. Reason about the attack.** Explain how an attacker recovers Mersenne Twister state from observed outputs (or
brute-forces a time-based seed) and predicts the next token. Explain why `secrets` prevents this.

**3. Measure the cost.** Run §78.3's benchmark and confirm `secrets` is slower than `random`. Explain the OS
CSPRNG source and why the per-token cost is negligible.

**4. Pick the tool.** For several needs (a session token, a shuffled deck for a game with stakes, a
reproducible simulation, a sampled subset for a test), choose `secrets` or `random` and justify each. Explain
the predictability requirement in each.

**5. The design question.** `random` is fast and reproducible; `secrets` is slower and unpredictable. Argue why
both exist and why using the wrong one is a security bug, not a performance choice. Your answer must use the
§78.3 measurement, the §78.2 predictability, and distinguish statistical randomness from cryptographic security.

---

## 78.7 Summary and cross-references

- **`random`** (Mersenne Twister) is a **deterministic** PRNG: seed-reproducible, and its state (all future
  output) is recoverable from a few hundred outputs. **Predictable, unsafe for secrets.**
- **`secrets`/`os.urandom`** draw from the **OS CSPRNG**: unseeded, unpredictable, unreconstructable. Use for
  tokens, salts, keys, nonces, passwords, anything an attacker must not guess.
- **Measured:** a secure `secrets` draw is **~20x** a `random` draw (~780 ns vs ~32 ns, and noisy) because it
  consults the OS entropy source; negligible per secret. **Pay it for unpredictability.**
- **Use `random` only where predictability is acceptable** (simulations, sampling, shuffling, tests), where
  reproducibility is often desirable. "Looks random" (statistical) is not "unguessable" (cryptographic).

**Cross-references.** Salts and password hashing → Chapter 76; constant-time token comparison → Chapter 77.
`bytes`/hex → Chapters 37, 7. OS entropy → Deep R. Crypto consuming randomness → Deep P. The auth seam → Deep U.
