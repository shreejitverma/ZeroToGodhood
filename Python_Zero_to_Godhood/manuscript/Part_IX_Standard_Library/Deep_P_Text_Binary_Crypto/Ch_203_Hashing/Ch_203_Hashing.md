# Chapter 122: Hashing

The volume has been *spending* digests for five chapters, RECORD hashes (109), lockfile pins (114), the entropy chain that fixed Chapter 121's listing, and this is the chapter that mints them. A cryptographic hash maps any bytes to a fixed-size digest such that collisions and preimages are computationally out of reach; content addressing, integrity checking, and dedup keys are corollaries of that one property, and the trust chain of Chapter 116 rests on the distinction the listing states first: **md5 and sha1 are broken for collision resistance**, fine as checksums, disqualified wherever an adversary chooses inputs.

The listing measures what is usually hand-waved. The **avalanche**: change one digit of a payment amount and **49.2% of the 256 digest bits flip**, digests carry no locality, which is exactly why they can stand for content (Chapter 114's tamper test) and exactly why they are useless as similarity measures (that job was Chapter 118's). The **three interfaces**, one-shot, incremental `update` (Chapter 91's streaming shape, gigabytes in fixed memory), and 3.11's `file_digest`, produce the identical digest, proven by equality. And **blake2's batteries**: `key=` makes it a MAC by construction (Chapter 80 built HMAC for hashes that lack this), and `person=` separates *domains*, the same bytes yielding unrelated identifiers for `invoice-v1` and `receipt-v1`, the built-in fix for cross-protocol digest collisions.

The benchmark ends an era politely: on a modern core, sha1 and sha256 ride hardware to **3.1 GB/s** while **md5 is the slowest algorithm measured** (0.69 GB/s), its last excuse, "at least it's fast", gone.

**This is a Deep P chapter.**
Chapter 80 (Deep O) owns HMAC's construction and use; Chapter 124 owns comparisons, KDFs, and the discipline around secrets. This chapter owns the digest itself.

## Section index

- **122.1** The digest, measured for its properties
- **122.2** The model: what the properties buy, and blake2's extras
- **122.3** Measurement: bulk and small-message budgets
- **122.4** Edges and failure modes
- **122.5** Connections
- **122.6** Exercises
- **122.7** Summary and cross-references

Listings live under `code/ch203/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 122.1 The digest, measured for its properties

```python
# code/ch203/l01_hashing.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- one document, the standard digests ---
  md5        128 bits  1f3a3b40dbac07a04ef012ce2e756592...
  sha1       160 bits  43b1c4fe9955897059ee126e4963704d...
  sha256     256 bits  2d5f9e2b26f9b53b252653f03438268e...
  sha3_256   256 bits  ebd74aa609d84394f3a808622f48180d...
  blake2b    512 bits  c317eaa007365b2a86d2ebea11dfb8a3...
  same input, fixed sizes, hex spellings of Chapter 120. md5 and
  sha1 are BROKEN for collision resistance - fine as checksums,
  disqualified wherever an adversary chooses inputs (Chapter 116's
  whole trust chain rests on that distinction)
--- the avalanche, counted ---
  change one digit of the amount; differing digest bits : 49.2%
  ~half of all 256 bits flip for a one-character edit: digests
  carry NO locality, which is why they can stand for content
  (Chapter 114's tamper test) and why they are useless as
  similarity measures (Chapter 118's difflib is that tool)
--- three interfaces, one digest ---
  one-shot == incremental == file_digest : True
  update() carries state (Chapter 91's streaming shape), so
  gigabyte files hash in fixed memory; file_digest (3.11+) wraps
  the chunk loop everyone wrote by hand, buffer-sized correctly
--- blake2: the digest with the batteries ---
  keyed digest    : 8ceea207dd599799e6db8b3186c5a36b
  unkeyed differs : True
  person='invoice-v1' : 9fb385093ab3628c
  person='receipt-v1' : c040d3b214fcb360
```

**The digest table is Chapter 120's hex on Chapter 122's mathematics.**
Five algorithms, one document, fixed output sizes regardless of input length; the hexdigest is just `hexlify` over the raw digest, and every content-address in this book has been these two chapters composed. The broken/unbroken line drawn under md5/sha1 is the operational one: *collision* resistance is what adversarial contexts need (an attacker who can present two colliding artifacts defeats Chapter 114's whole model), and checksumming your own backups is a different threat model where even md5 still functions.

**49.2% is the avalanche property as a number.**
One character of the amount changed; essentially half the bits flipped, the expectation for an ideal hash, met. The consequence runs both ways: digests can *stand for* content because nearby inputs share nothing, and digests can never *rank* content, similarity is a locality property, and hashes are locality's negation.

**The interface equality is the streaming license**: `update` carries state, so `file_digest`'s buffered chunk loop (the one everyone wrote by hand for twenty years, now stdlib with correct buffer sizing) produces the one-shot digest exactly, gigabyte artifacts verified in fixed memory at Chapter 114's measured 2.3 GB/s.

**And the blake2 block replaces two constructions with keyword arguments.**
`key=` yields a proper MAC without the HMAC wrapper (for hashes with length-extension immunity, of which blake2 is one); `person=` (and its sibling `salt=`) gives *domain separation*, `invoice-v1` and `receipt-v1` identifiers over identical bytes sharing no relationship, which is the principled fix for every system that ever confused a digest minted in one protocol with the same digest meant in another.

---

## 122.2 The model: what the properties buy, and blake2's extras

**Three properties, three prices, one budget.**
Preimage resistance (given a digest, no finding an input) protects commitments and stored verifiers. Second-preimage resistance (given input A, no forging B with A's digest) protects content addresses against substitution, Chapter 114's tamper test formalised. Collision resistance (no finding *any* two colliding inputs) is the strongest and the first to fall (md5 1996-2004, sha1 2017), and it is the one adversarial publishing needs, which is why "which property does my use case need" is the first question and "sha256" is almost always a sufficient answer today.

**Length extension is the classic footgun the API shapes around.**
For Merkle-Damgard hashes (md5, sha1, sha2), `H(secret + message)` lets an attacker *extend* the message without knowing the secret, the reason HMAC exists (Chapter 80) and the reason `blake2(key=...)` and sha3 (a sponge, immune) are the modern spellings. The rule is mechanical: keyed hashing goes through `hmac` or `blake2's key=`, never through concatenation.

**Domain separation is cheap and chronically skipped.**
Any digest reused across contexts invites cross-protocol confusion (a signature over "the hash" of one thing accepted as covering another). `person=`/`salt=` in blake2, or explicit prefixes (`sha256(b"invoice-v1:" + doc)`), cost nothing and close the class; the listing's two eight-byte identifiers are the pattern to copy.

**And `hashlib` itself is a facade over two engines**: built-in implementations guarantee the core set everywhere (`algorithms_guaranteed`), OpenSSL supplies the rest (`algorithms_available`, environment-dependent, which is why the listing prints none of it), and `usedforsecurity=False` exists so FIPS-restricted environments can still spell md5-as-checksum. The digest you get is identical either way; the flag and the sets are deployment surface, not mathematics.

---

## 122.3 Measurement: bulk and small-message budgets

**Methodology.** `code/ch203/bench_digest_throughput.py`.
16 MB one-pass for bulk; 200,000 64-byte digests for small; `min` of 5; 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. Bulk (16 MB):**

| algorithm | throughput |
|---|---|
| sha1 | 3.11 GB/s |
| sha256 | **3.12 GB/s** |
| sha512 | 1.82 GB/s |
| blake2b | 1.40 GB/s |
| sha3_256 | 1.02 GB/s |
| md5 | **0.69 GB/s** |

**b. Small (64 bytes, per call):** blake2b 256 ns, sha256 332 ns (237 via the direct constructor, `new("sha256")`'s string lookup costs ~95 ns), sha1 333, sha512 369, md5 439, sha3_256 543.

**Bulk is a hardware story.**
The M3's SHA extensions push sha1/sha256 past 3 GB/s; sha512 leads the software tier; sha3 pays its sponge; and md5, unaccelerated because nobody builds hardware for broken hashes, finishes *last*. The consequence for this book's own machinery: verifying Chapter 114's artifacts is effectively free at any scale, and "hashing is too slow" stopped being true on this hardware for any I/O-shaped workload.

**Small messages invert the frame.**
Setup and finalisation dominate; the spread compresses to 2x; blake2b's software efficiency wins; and the constructor-versus-`new()` gap matters as much as algorithm choice. Token systems, cache keys, and per-request digests budget in ns-per-call from table b; artifact pipelines budget in GB/s from table a, two tables, two professions, and quoting the wrong one is how hashing folklore starts.

**Book I** adds SIMD blake3 and parallel tree hashing to the same two tables, moving the software tier's frontier without moving the shape, and the shared system's content addresses use sha256 on both sides for the least interesting and most correct reason: it is fast everywhere, unbroken, and universally spelled.

---

## 122.4 Edges and failure modes

**Hash the bytes, not the object.**
`hash(obj)` is Python's *equality* hash, randomised per process for strings, unrelated to `hashlib`, and never a content identity. Content addressing serialises first (with a canonical encoding, or the same dict serialised twice may differ) and digests the bytes; every "hash mismatch across machines" bug that is not corruption is a canonicalisation gap.

**Digests of secrets are not stored passwords.**
Fast is the enemy: at 3 GB/s an attacker brute-forces low-entropy inputs offline at billions per second. Password verifiers need deliberate slowness and salts, `pbkdf2_hmac`/`scrypt`, Chapter 124, and any `sha256(password)` in a codebase is a finding, not a style.

**Truncation is legitimate and must be stated.**
`blake2b(digest_size=8)` or slicing sha256 halves are fine for space-constrained identifiers, with collision expectations falling to the birthday bound of the *truncated* size (2^32 for 8 bytes), a budget decision to write down, not an accident of formatting.

**`file_digest` wants binary, unbuffered-friendly files.**
Text-mode files corrupt by decoding; the function requires a readable binary file object, and its buffer handling assumes real files, for sockets and pipes, the incremental `update` loop remains the tool.

**Comparing digests is Chapter 124's business already.**
Equality of *public* content addresses may use `==`; anything where one side is secret-derived (MAC tags, token digests) compares via `hmac.compare_digest`, the timing-safe spelling, the edge is recorded here because the leak happens at the comparison, not the hash.

**And algorithms age; name them.**
Chapter 114's lockfiles spell `sha256=` for a reason: digests are versioned artifacts, and systems outlive algorithms (git's sha1-to-sha256 migration is the industry's worked example). Store the name with the digest, and design the migration path before the break, not after.

---

## 122.5 Connections

**Backward.**
Hex spellings and urlsafe transport of digests, Chapter 120. The consumers this chapter mints for: RECORD (109), lockfiles and the 2.3 GB/s verification bill (114), the trust chain (116), the entropy source for Chapter 121's law. HMAC's construction and message authentication, Chapter 80. Streaming state, Chapter 91.

**Forward.**
Randomness, where digests meet entropy (and `secrets` mints tokens), Chapter 123. KDFs, timing-safe comparison, and the crypto discipline that closes the volume, Chapter 124.

**Across books.**
**Book I** hashes with the same primitives through OpenSSL and adds blake3's tree parallelism for its artifact store; both books converge on the same three sentences: sha256 by default, name your algorithm, and never let a fast hash near a password.

---

## 122.6 Exercises

**1. Canonicalise or diverge.** Digest the same dict via `json.dumps` with and without `sort_keys`, across two interpreters; produce the mismatch, then write the canonical-bytes function your systems should share.

**2. Truncation budgets.** For 8-, 12-, and 16-byte truncated identifiers, compute expected collision counts at 10^6, 10^9, and 10^12 objects (birthday bound); pick a size for a real system you know and defend it in two lines.

**3. Length-extension in anger.** Against `sha256(secret + msg)` used as a toy MAC, implement the extension attack (any hashpump-style tool or by hand with an SHA implementation exposing state); then show `blake2b(key=)` and `hmac` refusing it. File the exercise under why constructions beat concatenation.

**4. Domain separation audit.** Grep a codebase for `sha256(` and classify each use by domain; find two domains sharing a digest space and add `person=`/prefix separation without breaking stored values (the migration is the exercise).

**5. Two budgets, one service.** For a service hashing 10 KB uploads and 64-byte session tokens, compute daily CPU from both tables at 10^8 requests; identify which table dominates and what blake2b would save.

**6. The design question.** `hashlib` guarantees a core set and passes through OpenSSL for the rest, `algorithms_available` varies by machine. Argue this two-tier design against a pure-builtin one (portability, FIPS realities, the `usedforsecurity` flag's existence) and against a pure-OpenSSL one (bootstrap, platforms without it), then decide where blake3 should land when it arrives, and what `algorithms_guaranteed`'s stability promise is actually worth to Chapter 114-style formats.

---

## 122.7 Summary and cross-references

- **A digest is a fixed-size stand-in for content**, valuable exactly for preimage/second-preimage/collision resistance; md5 and sha1 are collision-broken, checksums at best, disqualified wherever adversaries choose inputs, and the avalanche is real and measured: **one digit changed, 49.2% of bits flipped**, no locality, by design.
- **Three interfaces, one digest, proven equal**: one-shot, streaming `update` (fixed memory at any size), and `file_digest`'s stdlib chunk loop.
- **blake2 ships the batteries**: `key=` is a MAC by construction (length-extension immune; HMAC remains the spelling for sha2), `person=`/`salt=` give domain separation, the cheap fix for cross-protocol digest confusion.
- **Measured**: hardware sha1/sha256 at **3.1 GB/s** (verification is free at artifact scale), sha512 leads software, sha3 pays its sponge, and **md5 finishes last**, its speed excuse retired; small messages invert to a 2x spread where constructor-vs-`new()` (~95 ns) rivals algorithm choice.
- **The disciplines**: canonical bytes before hashing, names stored with digests, truncation as a written budget, KDFs, not digests, for passwords, and timing-safe comparison the moment secrets touch equality.

**Cross-references.** Hex and transport → Chapter 120. RECORD, lockfiles, the trust chain → Chapters 109, 114, 116. HMAC → Chapter 80. Streaming → Chapter 91. Randomness and tokens → Chapter 123. KDFs and comparisons → Chapter 124.
