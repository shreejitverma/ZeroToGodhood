# Chapter 124: The Crypto Discipline

Deep P has minted digests (122), entropy (123), and, back in Chapter 80, authentication codes. This closing chapter is the *discipline* that makes them safe to use, four rules that are each a one-liner in the stdlib and a CVE without it, and the decision procedure that ends the volume.

The chapter's star is a measurement most books only assert: a **timing side channel, shown in pure Python**. Comparing a 4 KB secret against guesses that differ at byte 0, 1024, 2048, 3072, and 4055, `==` takes **20, 41, 71, 89, 116 ns**, rising monotonically with the shared prefix because it scans until bytes differ, while `hmac.compare_digest` stays **flat at ~1140 ns**. That climb *is* the leak: an attacker who can measure it walks the secret one byte at a time, averaging away the noise over enough requests. The demonstration works only because the 4 KB secret makes the byte scan outweigh interpreter jitter, which is itself the lesson, the leak is smaller in normal code but **never zero**, so "the strings are short" is not a defence.

The other three rules follow: store passwords through a **slow, salted KDF** (`pbkdf2` at 200,000 iterations costs 31 ms, the deliberate inverse of Chapter 122's 3 GB/s); **authenticate the bytes you act on** with a MAC, before you parse them; and know what the stdlib **deliberately withholds**, there is no `encrypt()`, because symmetric encryption's footguns are too sharp for a batteries-included default.

**This is a Deep P chapter, and it closes Deep P.**
Chapter 80 built HMAC; Chapters 122 and 123 minted the digests and entropy. This chapter is their safe use, and the volume's decision procedure.

## Section index

- **124.1** The four rules, demonstrated
- **124.2** The model: constant time, deliberate slowness, and the boundary
- **124.3** Measurement: the leak made visible, the KDF dial priced
- **124.4** Edges and failure modes
- **124.5** Connections, and the volume closed
- **124.6** Exercises
- **124.7** Summary and cross-references

Listings live under `code/ch205/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 124.1 The four rules, demonstrated

```python
# code/ch205/l01_the_crypto_discipline.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- compare secrets in constant time ---
  compare_digest(real, right) : True
  compare_digest(real, wrong) : False
  '==' on bytes returns at the FIRST differing byte, so an
  attacker measures how far their guess got and walks the secret
  in one byte at a time. compare_digest takes the same time
  whatever differs - the benchmark makes the leak visible
--- store passwords through a slow, salted KDF ---
  pbkdf2 derives 32 bytes from password+salt+iterations
  verify correct password : True
  verify wrong password   : False
  the salt makes two identical passwords store differently (no
  rainbow tables, no 'these two accounts share a password' leak);
  the 200,000 iterations make each guess EXPENSIVE - the opposite
  of Chapter 122's 3 GB/s, on purpose (scrypt/argon2 go further)
--- authenticate the bytes you will act on ---
  genuine message : accepted: transfer:1500:to:ACME
  tampered message: REJECTED (bad tag)
  a MAC binds message to key: without the key you cannot forge a
  tag, and verification is constant-time (rule 1 again). this is
  Chapter 80's HMAC applied - authenticate BEFORE you parse or
  act, never after
--- what the stdlib deliberately does NOT give you ---
  there is no hashlib.encrypt / no AES in the standard library:
  symmetric encryption's footguns (mode choice, nonce reuse,
  padding oracles) are too sharp for a batteries-included default,
  so the stdlib ships HASHING, MACS, and KDFs - verify and derive -
  and points at `cryptography` (PyCA) for encrypt/decrypt
--- Deep P, closed: the decision procedure ---
  need content identity / integrity?  -> hashlib (122)
  need message authentication?        -> hmac (80, here)
  need to store a password?           -> pbkdf2/scrypt, salted
  need an unguessable value?          -> secrets (123)
  need reproducible randomness?       -> random.Random(seed) (123)
  comparing anything secret?          -> compare_digest, always
  need to ENCRYPT?                     -> leave the stdlib (PyCA)
  117 regex, 118 text, 119 csv, 120 codecs, 121 compression,
  122 hashing, 123 randomness, 124 this: the text-and-bytes
  toolbox, and the rule under all of it - measure, name your
  algorithm, and compare secrets in constant time
```

**Rule one is the one that hides in `==`.**
Both `compare_digest` results are boolean-correct, unremarkable until §124.3 times them; the leak is *only* observable in the clock, which is exactly why it survives code review and fails penetration tests. The rule is absolute and admits no size exception: **every comparison where one side is secret-derived** (MAC tags, token digests, password verifiers) goes through `compare_digest`.

**Rule two inverts Chapter 122 on purpose.**
`pbkdf2_hmac` derives a verifier from password, salt, and an iteration count. The salt makes two identical passwords store *differently*, killing rainbow tables and the "these two accounts share a password" inference; the 200,000 iterations make each guess *expensive*, the deliberate opposite of a fast hash, and the reason `sha256(password)` is a finding. (scrypt and argon2 go further, adding memory-hardness the listing names as the next rung.)

**Rule three is order, not just algorithm.**
The MAC binds message to key, so tampering is rejected, and the verification is `compare_digest` (rule one, again). The load-bearing word is *before*: authenticate the bytes **before you parse or act on** them, because a parser run on unauthenticated input is an attack surface (the padding-oracle and deserialization-RCE families both live in "acted before verifying").

**And rule four is the boundary that defines the volume's scope.**
No `encrypt()` in the stdlib is a *decision*: mode selection, nonce uniqueness, and padding oracles are too easy to get catastrophically wrong for a default battery, so Python ships verify-and-derive (hashing, MACs, KDFs) and points at PyCA `cryptography` for secrecy. Knowing where the stdlib stops is itself part of the discipline.

---

## 124.2 The model: constant time, deliberate slowness, and the boundary

**Constant-time comparison removes the data-dependent branch.**
`compare_digest` accumulates differences across the *whole* input (a running OR of XORed bytes) and returns once, so its time depends on length, never on *where* or *whether* bytes match. That is the general shape of side-channel defence, make the observable (time, power, cache state) independent of the secret, and Python exposes exactly the one primitive most code needs, because the language cannot make user comparisons constant-time for you. (It also length-pads to avoid leaking length for equal-length digests; comparing different-length secrets still leaks length, so compare *digests*, which are fixed-length, not raw secrets.)

**KDF slowness is a symmetric tax you set to be asymmetric in effect.**
Each iteration costs you once per legitimate login and the attacker once per guess; tuning iterations so one verification is a few milliseconds (tolerable to a user) makes a billion offline guesses cost centuries (intolerable to an attacker). The dial is calibrated to *your* hardware and re-tuned as hardware improves, which is why the count is stored *with* the hash (like Chapter 122's algorithm names, versioned parameters), and why memory-hard KDFs (scrypt, argon2) exist: they tax the attacker's *specialised* hardware, not just their time.

**Authentication is a precondition, not a postcondition.**
The secure pattern is decrypt-and-verify as *verify-then-decrypt* (encrypt-then-MAC), and parse-after-authenticate everywhere: the MAC gates whether the bytes are trustworthy input at all. This reframes a lot of code, a webhook handler authenticates the raw body before `json.loads`, a token is verified before its claims are read, and the volume's serialization warnings (pickle as RCE, Chapter 42) are special cases of "acted on unauthenticated bytes".

**The stdlib boundary is a taxonomy of trust.**
What Python ships, hashing (identity), MACs (authenticity), KDFs (password storage), CSPRNG (unpredictability), are the primitives whose *misuse is bounded*: a wrong hash is slow or weak, not silently plaintext. Encryption's failure modes (a reused nonce can expose plaintext or forge messages) are unbounded, so the language declines the default and names the specialist library, an honest boundary that this chapter treats as content, because "which library" is a decision engineers must make correctly.

---

## 124.3 Measurement: the leak made visible, the KDF dial priced

**Methodology.** `code/ch205/bench_timing_leak.py`.
A 4 KB secret so the byte scan dominates interpreter noise; `min` over 5 batches of 200,000 compares; 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. The timing leak, by mismatch position:**

| first differing byte | `==` | `compare_digest` |
|---|---|---|
| 0% (byte 0) | 20 ns | 1,137 ns |
| 25% (1024) | 41 ns | 1,144 ns |
| 50% (2048) | 71 ns | 1,138 ns |
| 75% (3072) | 89 ns | 1,154 ns |
| 99% (4055) | **116 ns** | 1,181 ns |

**b. The KDF dial:** pbkdf2-sha256 at 50k / 100k / 200k / 400k iterations costs **7.9 / 15.7 / 31.6 / 63.0 ms** per verification.

**Table a is a real side channel, in pure Python, which is the point.**
`==`'s time rises almost linearly with the shared prefix, 20 ns to 116 ns, because `memcmp` returns at the first differing byte; `compare_digest` is flat because it scans everything. An attacker who can measure the difference (locally trivial, over a network via statistical averaging) recovers the secret byte by byte: guess byte 0, keep the value that made the comparison slowest, move to byte 1. The demonstration needs a 4 KB secret to lift the signal above interpreter jitter, and *that requirement is the lesson*, in ordinary code the per-byte leak is a few nanoseconds, invisible per request and fully recoverable over millions, so the defence is unconditional. (It reproduces identically on 3.14 and the free-threaded build; the channel is `memcmp`, below the interpreter.)

**Table b is the same physics inverted into a defence you control.**
Every doubling of iterations doubles the attacker's cost and yours equally; 31 ms per login is imperceptible to a user and ruinous to an offline cracker at scale. The number is not universal, it is *this* CPU today, re-tuned as hardware improves and stored beside each hash, and the migration path (raise iterations, re-derive on next login) is the KDF version of Chapter 122's "name your algorithm".

**Book I** shows the identical `memcmp`-slope leak in C++ (with the compiler's own optimisations sometimes *reintroducing* a branch the programmer removed) and reaches this chapter's exact conclusion: constant-time comparison is a primitive you call, never a property you assume, and password storage is deliberate slowness, tuned and versioned. Both volumes close their crypto material on the same sentence, security is not the algorithm, it is the correct use of it.

---

## 124.4 Edges and failure modes

**`==` on secrets is the bug the whole chapter exists for.**
Not just tags, any equality where one operand derives from a secret: session token lookups (`token == stored`), signature checks, coupon codes with value. Grep for it; the fix is one function name, and the review that catches it beats the pentest that finds it.

**`compare_digest` leaks length, so compare fixed-length digests.**
Different-length inputs return early; comparing raw secrets of varying length reintroduces a (smaller) channel. Compare *digests* (fixed size) or HMAC tags, never variable-length plaintext secrets, the reason authentication compares tags, not messages.

**KDF parameters are per-hash state, and defaults age.**
Store salt and iteration count with each verifier; a global constant becomes a liability the day it is too low, and a stored parameter lets you raise the cost per user on next login. Hardcoding "200000" in 2026 is the 2016 "10000" of a codebase that never revisited it.

**Pepper, salt, and their scopes differ.**
Salt is per-hash and stored with it (defeats rainbow tables); a pepper is a secret key applied to *all* hashes and stored *separately* (defeats offline cracking even with the database), and conflating them, storing the pepper next to the hashes, discards its only benefit.

**Authenticate before you deserialize, always.**
The volume's pickle-as-RCE and padding-oracle warnings converge here: any code path that parses, decompresses, or deserializes attacker-controlled bytes *before* verifying a MAC over them is exploitable regardless of the parser's quality. Verify, then parse; the order is the mitigation.

**The stdlib boundary is not a limitation to route around.**
"There's no AES so I'll XOR with a key" is how homebrew crypto disasters start; the absence is a signpost to PyCA `cryptography` (or `pynacl`), whose misuse-resistant APIs (`Fernet`, AEAD constructions) exist precisely because the primitives are dangerous. Crossing the boundary means adopting a vetted library, not reimplementing it.

**And nothing here survives key mishandling.**
A perfect MAC with a key in the source repo, a token compared in constant time but logged in plaintext (Chapter 123's disclosure edge), a KDF whose salt is a constant, each defeats the primitive from outside. The discipline is end-to-end; this chapter secures the *comparison and derivation*, and Deep O's operational-security chapters secure the *handling*.

---

## 124.5 Connections, and the volume closed

**Backward, through Deep P.**
HMAC's construction, Chapter 80; the digests this chapter compares and derives, Chapter 122; the entropy behind salts, keys, and tokens, Chapter 123; the hex and base64 those secrets travel as, Chapter 120; the compress-then-encrypt ordering, Chapter 121; and the regex, text, and CSV chapters (117-119) that parse the inputs a MAC must gate. Deep P is the text-and-bytes toolbox, and this chapter is the safety rail along its most dangerous edge.

**Beyond the volume.**
Encryption proper, key management, TLS, and the PyCA ecosystem are Deep O's applied-security territory and beyond the stdlib's boundary. The serialization threats this chapter's "authenticate first" rule mitigates, pickle, deserialization, are Chapter 42 and Deep O. Operational secret handling, vaults, rotation, least privilege, is where "the discipline is end-to-end" continues.

**Across books, closing Deep P.**
The shared system authenticates every message crossing its language boundary with an HMAC compared in constant time on both sides, derives its at-rest verifiers with the same KDF discipline, and reaches for the *same* vetted encryption library from **Book I** and Book II rather than either language's temptation to roll its own. The decision procedure that closes this volume is language-independent because the threats are: identify what property you need, use the primitive built for it, compare in constant time, name and version your parameters, and encrypt only with a library you did not write.

---

## 124.6 Exercises

**1. Recover a secret by timing.** Extend the benchmark into an attack: given only a timing oracle over `==`, recover a 16-byte secret byte by byte. Then show it failing against `compare_digest`. This is the chapter, executed.

**2. Tune the KDF.** Calibrate pbkdf2 iterations to exactly 250 ms on your hardware; then measure how many offline guesses per second that permits an attacker with 100x your hardware, and decide whether to move to scrypt.

**3. Verify-then-parse.** Take a webhook handler that `json.loads` before checking the signature; exploit it (malformed JSON as DoS, or worse), then reorder to authenticate-first and show the exploit dying.

**4. Salt and pepper.** Build a password store with per-user salt and a separately-stored pepper; demonstrate that a database leak *without* the pepper resists cracking, and quantify the pepper's contribution.

**5. Audit for `==`.** Scan a real codebase for secret comparisons using `==` (tokens, signatures, API keys); count them, fix them, and write the one-line lint rule that would have caught each.

**6. The design question.** Python ships verify-and-derive but not encrypt, drawing a boundary at the primitives whose misuse is *unbounded*. Argue where that boundary should sit: should a misuse-resistant AEAD (like `Fernet`) be in the stdlib given how many teams need "just encrypt this safely", against the maintenance and agility cost of shipping cryptography in a slow-moving standard library (the reason `ssl` lags OpenSSL)? Decide, and defend it with this volume's evidence about what the stdlib's presence guarantees (Chapter 122's `algorithms_guaranteed`) versus what its absence delegates.

---

## 124.7 Summary and cross-references

- **Four rules, each a stdlib one-liner and a CVE without it**: compare secrets in constant time (`compare_digest`), store passwords through a slow salted KDF (`pbkdf2`/scrypt, never a fast hash), authenticate the bytes *before* you act on them (HMAC, Chapter 80), and know the stdlib withholds `encrypt()` by design.
- **The timing leak, shown in pure Python**: `==` on a 4 KB secret rises **20 to 116 ns** with the shared prefix (it scans to the first difference); `compare_digest` is **flat**. The 4 KB requirement is the lesson, the leak is smaller but never zero in real code, so the defence is unconditional, and it reproduces across the matrix because the channel is `memcmp`.
- **KDF slowness is a dial you own**: pbkdf2 costs 7.9 to 63 ms across 50k-400k iterations, tuned so one login is tolerable and a billion guesses are not, with salt and count stored per hash and re-tuned as hardware moves.
- **Authenticate before you parse**: the pickle-RCE and padding-oracle families are "acted on unauthenticated bytes"; verify-then-decrypt/parse is the order that is the mitigation.
- **Deep P, closed**: 117 regex, 118 text, 119 CSV, 120 codecs, 121 compression, 122 hashing, 123 randomness, 124 discipline, the text-and-bytes toolbox, under one rule, measure, name your algorithm, and compare secrets in constant time.

**Cross-references.** HMAC → Chapter 80. Digests → Chapter 122. Entropy, salts, tokens → Chapter 123. Transport encodings → Chapter 120. Compress-then-encrypt → Chapter 121. Deserialization threats → Chapter 42, Deep O. Encryption and key management → Deep O, PyCA `cryptography`.
