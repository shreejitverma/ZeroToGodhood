# Chapter 76: Password Hashing

Everywhere else in this book, faster is better. Password hashing is the one place where **slower is the entire
point**, and getting this backwards is a catastrophic, common security bug. A developer stores password hashes
with `hashlib.sha256(password)`, fast, standard, and reasons that a fast hash means a fast login. It does, and
it also means that when the hash database leaks, as databases do, an attacker can try **millions of guesses per
second** against it. Measured, `sha256` hashes a password in ~240 nanoseconds; a proper key-derivation function,
`pbkdf2` at 200,000 iterations, takes ~19 milliseconds, **79,000x slower**, *by design*. That slowness cuts the
attacker from ~4 million guesses per second to ~50. For passwords, the cost of the hash is the security of the
system, and a fast hash is a vulnerability.

This chapter opens **Deep O** (testing, debugging, observability, security) with password hashing: why a
password hash must be deliberately slow and salted, and the measurement that makes the counterintuitive rule
concrete. It is the security counterpart to the book's usual performance thrust, here the goal is to make an
operation *expensive*.

## Section index

- **76.1** Slow, and salted
- **76.2** Why slowness is the security
- **76.3** Measurement: fast hash vs slow KDF
- **76.4** Edges and failure modes
- **76.5** Connections
- **76.6** Exercises
- **76.7** Summary and cross-references

Listings live under `code/ch076/` and are re-executed by `make verify` on both interpreters.

---

## 76.1 Slow, and salted

```python
# code/ch076/l01_password_hashing.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a fast hash (SHA-256): fine for integrity, WRONG for passwords ---
  sha256(salt+pw)[:16] : 3d3ecd0750760383
--- a slow KDF (pbkdf2): deliberately expensive per guess ---
  pbkdf2 200k iters[:16]: 45fea9d79f583c56
  same password, but far costlier to compute (the benchmark shows it)
--- salt: identical passwords hash DIFFERENTLY with different salts ---
  same pw, salt A [:16] : b15618ab59447ee6
  same pw, salt B [:16] : 80d6f27306d7b885
  digests differ        : True  (rainbow tables defeated)
--- the rule ---
  store salt + slow-KDF digest; never a fast unsalted hash of a password
  (use scrypt/argon2 or pbkdf2 with a high work factor; verify with compare_digest)
```

A correct password hash has two properties. It is **slow**: `pbkdf2_hmac("sha256", pw, salt, 200_000)` runs the
underlying hash 200,000 times, so computing the digest is deliberately expensive (§76.3). And it is **salted**:
a unique random salt per password is mixed in, so the *same* password produces *different* digests under
different salts, the listing's `salt A` and `salt B` give different hashes for the identical password. The salt
defeats **rainbow tables** (precomputed hash-to-password lookups): with a unique salt per user, an attacker
cannot precompute anything, they must attack each password's salt separately.

The digests are deterministic given a fixed salt (shown here for reproducibility), but in real use the salt is
**random** (`secrets.token_bytes(16)`) and stored *alongside* the hash, salt is not secret, it just needs to be
unique. The contrast in the first two blocks is the chapter: the same password hashed fast (`sha256`) and slow
(`pbkdf2`) both produce a digest, but one is cheap to attack and the other is not.

---

## 76.2 Why slowness is the security

The threat model is a *leaked hash database*. Assume the attacker has the hashes (breaches happen), so the only
defense left is making each *guess* expensive. Password hashing is an *offline* attack: the attacker runs guesses
on their own hardware, as fast as the hash allows, so the hash's speed *is* the attacker's guess rate.

With a **fast** hash (`sha256`), a guess costs ~240 ns, so a single machine tries ~4 million guesses per second,
and a GPU cluster does billions; every common password, and most human-chosen ones, falls in hours. With a
**slow** KDF (`pbkdf2` at 200k iterations), a guess costs ~19 ms, ~50 guesses per second per core, so the same
brute force takes tens of thousands of times longer, pushing it from "hours" to "infeasible" for a strong
password. The legitimate server pays the ~19 ms *once* per login (imperceptible to a user); the attacker pays it
*per guess* across billions of guesses (fatal to the attack). That asymmetry, one slow hash per login versus one
per guess, is the entire mechanism.

The **work factor** (iteration count, or scrypt/argon2 memory/time parameters) is the tuning knob: set it as high
as your login latency budget allows (tens of milliseconds), and *increase it over time* as hardware gets faster,
today's recommendation is far above `pbkdf2`'s old defaults, and `scrypt`/`argon2` (memory-hard, resisting GPU/
ASIC attacks) are preferred over `pbkdf2` for new systems. The rule: **use a salted, high-work-factor KDF
(argon2/scrypt, or pbkdf2) for passwords; never a fast hash.** The fast hash is correct for *data integrity* (a
checksum, a content address), where you *want* speed and there is no secret to protect, the trade is specific to
secrets an attacker will brute-force.

---

## 76.3 Measurement: fast hash vs slow KDF

**Methodology.** `code/ch076/bench_kdf.py`. A single `sha256` of a password versus `pbkdf2_hmac` at 200,000
iterations. `min` per call; ratio relative to `sha256`. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| hash a password | min per call | ratio | attacker guesses/sec |
|---|---|---|---|
| `sha256` (single) | **238 ns** | 1.00x | **~4,000,000** |
| `pbkdf2` (200k iterations) | **~19 ms** | **~79,000x** | **~50** |

`sha256` computes in **238 ns**, so an attacker with the leaked hash tries ~4 million guesses per second per
core. `pbkdf2` at 200k iterations takes **~19 ms**, **79,000x** slower, cutting the attacker to ~50 guesses per
second. That factor is the security: the same brute-force campaign that would crack a database of `sha256`
hashes in hours takes ~79,000x longer against `pbkdf2`. The work factor is chosen precisely to make this ratio
large while keeping the *legitimate* per-login cost tolerable (~19 ms is invisible to a user logging in once).

The rule inverts the book's usual optimization: **for password hashing, make it slow, and keep making it slower
as hardware improves.** Pick a work factor targeting tens of milliseconds per hash on your hardware, use a salt
per password, prefer a memory-hard KDF (argon2/scrypt) for new systems, and verify with a constant-time
comparison (the next Deep O topic). And keep the distinction sharp: this deliberate slowness applies *only* to
secrets under offline brute-force attack, everywhere else in the book, and for non-secret data integrity, fast
is still right. Password hashing is the exception that proves how context-dependent "faster is better" is.

---

## 76.4 Edges and failure modes

**A fast hash for passwords.** §76.2. `sha256`/`md5`/`sha1` of a password is crackable at millions of guesses/
sec. Use a slow KDF (argon2/scrypt/pbkdf2). This is the core bug.

**No salt (or a shared salt).** §76.1. Unsalted (or same-salt) hashes let one rainbow table or one cracking run
attack all passwords at once. Use a unique random salt per password (`secrets.token_bytes`), stored beside the
hash.

**Too low a work factor.** A KDF with too few iterations (or too little argon2 memory) is only nominally slow.
Tune the work factor to ~tens of ms on your hardware, and raise it over time; a decade-old default is now too
low.

**Rolling your own KDF.** Home-grown "hash it 1000 times" schemes miss subtleties (length-extension, weak salt
mixing). Use a vetted KDF from `hashlib` (`scrypt`, `pbkdf2_hmac`) or a library (argon2-cffi); do not invent one.

**Comparing digests with `==`.** Verifying a password by `stored == computed` with `==` can leak timing (the
next chapter). Use `hmac.compare_digest` / `secrets.compare_digest` for constant-time comparison.

**Encrypting instead of hashing passwords.** Passwords must be *hashed* (one-way), not *encrypted* (reversible).
An encrypted password can be decrypted if the key leaks; a KDF digest cannot be reversed. Never store recoverable
passwords.

**Using a KDF where a fast hash is correct.** For a content address, checksum, or cache key (no secret, no brute-
force threat), a fast hash is right, a slow KDF there is pure waste. Match the tool to the threat.

---

## 76.5 Connections

**Backward.** The `bytes` and hex encoding of digests are Chapters 37 and 7. The hashing that also underlies dict
keys (a *fast* hash, correctly) is Deep P. The measurement discipline (min-of-many, the attacker-rate framing) is
the book's method throughout.

**Forward.** Constant-time comparison (`compare_digest`) and the timing-attack it prevents are the next Deep O
chapter. `secrets` for generating salts and tokens (versus `random`) is a Deep O topic. HMAC for message
authentication, and the broader crypto toolkit, are Deep P. Testing that security invariants hold is Deep O's
testing material.

**Across books.** Correct password hashing is a security boundary Book II enforces before user data reaches
**Book III**. A **Book III** application storing credentials uses a salted, high-work-factor KDF and constant-
time verification, so a database breach does not immediately yield plaintext passwords, and it reserves fast
hashes for non-secret content addressing (embedding cache keys, deduplication). The §76.3 asymmetry, slow per
login, ruinous per guess, is the reason the auth path deliberately spends milliseconds. **Deep U** owns the
credential-storage seam; **Deep P** owns the crypto primitives.

---

## 76.6 Exercises

**1. Measure the asymmetry.** Reproduce §76.3: time `sha256` and `pbkdf2`, and translate each into attacker
guesses per second. Explain why the hash's speed is the attacker's guess rate.

**2. Tune the work factor.** Time `pbkdf2` at several iteration counts and find the count that gives ~50 ms on
your hardware. Explain the trade between login latency and attack resistance.

**3. Show the salt effect.** Hash the same password with two different salts and confirm the digests differ.
Explain how a per-password salt defeats rainbow tables and shared-run cracking.

**4. Pick the right tool.** For several use cases (store a password, checksum a file, a cache key, a content
address), choose a fast hash or a slow KDF and justify each by the threat model. Explain when slowness is
security and when it is waste.

**5. The design question.** Password hashing deliberately inverts the book's "faster is better". Argue why. Your
answer must use the §76.3 measurement and attacker-rate framing, explain salting and the work factor, and state
precisely which operations should be slow (secrets under brute force) and which fast (non-secret integrity).

---

## 76.7 Summary and cross-references

- A **password hash must be deliberately slow and salted.** A fast hash (`sha256`) is a liability: a leaked
  database is brute-forced at millions of guesses/sec.
- **Measured:** `pbkdf2` at 200k iterations is **~79,000x** slower than `sha256` (19 ms vs 238 ns), cutting an
  attacker from **~4,000,000** to **~50** guesses/sec. **The slowness is the security.**
- **Use a salted, high-work-factor KDF** (argon2/scrypt preferred, or pbkdf2); a **unique random salt per
  password** (stored beside the hash) defeats rainbow tables; **raise the work factor** as hardware improves;
  verify with **constant-time comparison**.
- **Fast hashes are correct for non-secret data integrity** (checksums, content addresses); the slow-is-secure
  trade is specific to passwords/secrets under offline brute force.

**Cross-references.** `bytes`/hex → Chapters 37, 7. Fast hashing for dict keys → Deep P. Constant-time comparison
and timing attacks → the next Deep O chapter. `secrets` and salts → Deep O. HMAC and crypto → Deep P. The
credential-storage seam → Deep U.
