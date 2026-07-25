# Chapter 80: Message Authentication with HMAC

A service accepts webhooks and trusts them because they arrive at a secret URL. Anyone who learns the URL, from
a log, a proxy, a leaked config, can forge a webhook, because a URL is not proof of *who* sent the payload. A
hash does not help: `sha256(payload)` proves the payload was not *corrupted*, but *anyone* can recompute it, so
it proves nothing about *origin*. What you need is a **message authentication code**: `HMAC` mixes a *shared
secret key* into the hash, so only a party with the key can produce a valid MAC, and the receiver, recomputing
the HMAC and comparing it in constant time (Chapter 77), knows the message came from a key-holder *and* was not
altered. Any tampering, to the message or the MAC, or a wrong key, fails verification. And it is cheap: an HMAC
costs about **4x** a bare hash (~1 microsecond for a short message), negligible for authenticating every
request.

This chapter continues **Deep O**, completing the crypto quartet, hashing (76), comparison (77), randomness (78),
and now authentication (80), with HMAC: what it proves that a hash does not, why the HMAC construction is correct
where a naive `hash(key + message)` is not, and the small cost of authenticating everything.

## Section index

- **80.1** Authenticity, not just integrity
- **80.2** Why HMAC, not `hash(key + message)`
- **80.3** Measurement: the cost of authentication
- **80.4** Edges and failure modes
- **80.5** Connections
- **80.6** Exercises
- **80.7** Summary and cross-references

Listings live under `code/ch080/` and are re-executed by `make verify` on both interpreters.

---

## 80.1 Authenticity, not just integrity

```python
# code/ch080/l01_hmac.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- sign: an HMAC binds the message to the key ---
  HMAC-SHA256 (first 16) : 183288ed108b3e48
  deterministic          : True
--- verify: only a valid (key, message, mac) triple passes ---
  valid triple           : True
  tampered message       : False
  tampered mac           : False
  wrong key              : False
--- the rule ---
  authenticate messages/tokens/webhooks with HMAC (shared key)
  verify with compare_digest; a plain hash proves integrity, not origin
  (a naive hash(key+msg) is NOT a secure MAC: use hmac)
```

`hmac.new(key, message, sha256)` produces a MAC that *binds the message to the key*: it is deterministic (same
key and message give the same MAC) but *unforgeable* without the key. Verification recomputes the HMAC and
compares with `compare_digest` (constant-time, Chapter 77, so a valid MAC leaks no timing). The verify block is
the whole guarantee: the valid `(key, message, mac)` triple passes, and *every* deviation fails, a tampered
message, a tampered MAC, or a wrong key. So a receiver that shares the key with the sender can trust that a
message with a valid MAC (a) came from someone holding the key (**authenticity**) and (b) was not modified in
transit (**integrity**), which a plain hash gives only the second of, and only against accidental corruption,
not a deliberate attacker (who would just recompute the hash).

This is the difference between a *checksum* and a *signature-with-a-shared-secret*. A hash is a checksum: it
catches accidental corruption but not intentional forgery, because it has no secret. HMAC adds the secret, and
with it, proof of origin.

---

## 80.2 Why HMAC, not `hash(key + message)`

The intuitive way to add a key to a hash, `sha256(key + message)`, *looks* like it should authenticate, and it
is *insecure*. The reason is a property of the common Merkle-Damgard hash functions (MD5, SHA-1, SHA-256): they
are vulnerable to **length-extension**. Given `hash(key + message)` and the length of `key + message`, an
attacker can compute `hash(key + message + padding + extra)` for arbitrary `extra`, *without knowing the key*,
producing a valid MAC for a message they extended. So `hash(key + message)` lets an attacker *append* to your
message and forge a MAC for the result, catastrophic for something like `hash(key + "amount=100")` where the
attacker appends `"&amount=10000"`.

**HMAC** is the construction that fixes this. It is `hash(key XOR opad + hash(key XOR ipad + message))`, two
nested hashes with the key mixed in twice (with different constants `ipad`/`opad`). The nesting defeats length-
extension: an attacker cannot extend the *inner* hash's input without the key, and cannot recompute the *outer*
hash without it either. HMAC is a *vetted*, standardized construction (RFC 2104) proven secure under standard
assumptions, which is exactly why the standard library provides `hmac` and you should never hand-roll
`hash(key + message)`.

The rule: **authenticate with `hmac`, never with a bare `hash(key + message)`.** Use HMAC for anything crossing
a trust boundary where you must verify origin *and* integrity: webhook payloads, signed cookies/tokens, API
request signing, message-queue entries, inter-service messages. Verify with `compare_digest`. And keep the key
*secret* (it is the whole security) and *rotated*, an HMAC key is a credential, generated with `secrets`
(Chapter 78) and stored like one.

---

## 80.3 Measurement: the cost of authentication

**Methodology.** `code/ch080/bench_hmac.py`. A bare `sha256` versus an `HMAC-SHA256` of the same short message.
`min` per call; ratio relative to the bare hash. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| hash a short message | min per call | ratio |
|---|---|---|
| `sha256` (integrity only) | **237 ns** | 1.00x |
| `HMAC-SHA256` (authenticated) | **959 ns** | **4.05x** |

HMAC costs **~4x** a bare hash, ~960 ns versus ~237 ns, because it does two hash passes (inner and outer) plus
key setup. In *absolute* terms it is under a microsecond for a short message, cheap enough to authenticate
*every* message. For a service handling thousands of requests per second, HMAC-verifying each adds ~1 ms per
thousand requests, invisible against the real work of handling them.

The rule: **authenticate everything that crosses a trust boundary; the cost is negligible.** There is no
performance reason to skip HMAC on untrusted input, ~1 us per message is nothing against parsing, database, or
network cost, and the security it buys, unforgeable proof of origin and integrity, is essential wherever you
would otherwise be trusting the *channel* (a URL, an IP, a network position) instead of a *credential*. As with
the rest of Deep O's crypto, the small, fixed cost is the price of a real guarantee, and skipping it to save a
microsecond trades a real security property for nothing measurable.

---

## 80.4 Edges and failure modes

**`hash(key + message)` as a MAC.** §80.2. Vulnerable to length-extension; an attacker can append and forge. Use
`hmac`.

**Verifying with `==`.** §80.1 and Chapter 77. Comparing MACs with `==` leaks timing. Verify with
`hmac.compare_digest`.

**A weak or reused key.** The HMAC key is a credential: generate it with `secrets` (Chapter 78), keep it secret,
give each trust relationship its own key, and rotate it. A guessable or leaked key makes the MAC forgeable.

**Authenticate-then-... ordering.** For encrypted *and* authenticated data, the order matters (encrypt-then-MAC
is the safe default); MAC-then-encrypt and encrypt-and-MAC have pitfalls. For combined confidentiality+integrity,
prefer an authenticated-encryption mode (AES-GCM, `cryptography`'s Fernet) over composing HMAC and a cipher by
hand.

**MAC over the wrong bytes.** Authenticate the *exact* bytes you act on (the raw body), not a re-serialized or
normalized form, if you HMAC the parsed-then-reserialized JSON, an attacker can craft a body that reserializes
differently and slips past. Compute and verify the MAC over the raw payload.

**Truncating the MAC.** Using only part of the HMAC output weakens it. Compare the full digest; do not truncate
to "save space" without understanding the security cost.

---

## 80.5 Connections

**Backward.** The hash HMAC is built on is the fast-hashing side of Chapter 76 (correct here, because HMAC's key
provides the security, not slowness). The constant-time `compare_digest` used to verify is Chapter 77. The
`secrets`-generated key is Chapter 78. The `bytes`/hex of the MAC are Chapters 37 and 7.

**Forward.** Authenticated encryption (AES-GCM, Fernet), asymmetric signatures (Ed25519, RSA), and key management
are Deep P. Signed tokens (JWT and its pitfalls) and webhook verification are Deep O/Deep U application topics.
Testing that the auth path rejects tampering is Deep O's security-testing material.

**Across books.** HMAC is a trust boundary Book II enforces on data entering from **Book III** and beyond. A
**Book III** system verifies webhook and inter-service message signatures with HMAC over the raw payload, using
`secrets`-generated per-relationship keys and `compare_digest` verification, so it trusts *credentials*, not
*channels*. The §80.1 tamper detection is precisely what stops a forged request from a leaked URL or a
compromised network position, the attack that trusting-the-channel invites, which **Deep U** guards against at
the ingress seam. **Deep P** owns the broader crypto.

---

## 80.6 Exercises

**1. Authenticate and tamper.** Reproduce §80.1: sign a message, verify it, then tamper the message, the MAC, and
the key, and confirm each fails. Explain what authenticity adds over a plain hash.

**2. Break the naive MAC.** Explain (or, with a length-extension tool, demonstrate) how `hash(key + message)` can
be forged by extension, and why HMAC's nesting prevents it. State why you must never hand-roll a MAC.

**3. Measure the cost.** Run §80.3's benchmark and confirm HMAC is a few times a bare hash but still ~1 us.
Explain the two-pass construction and why the cost is negligible per request.

**4. MAC the right bytes.** Show that HMAC-ing a re-serialized form of a payload (vs the raw bytes) can be
bypassed by a body that reserializes differently. Explain why you authenticate the exact received bytes.

**5. The design question.** A hash gives integrity; HMAC gives integrity *and* authenticity by adding a key.
Argue when you need which, and why `hash(key + message)` is not a substitute for HMAC. Your answer must use the
§80.3 cost, the length-extension weakness, and the trust-the-credential-not-the-channel principle.

---

## 80.7 Summary and cross-references

- A **hash proves integrity** (no accidental corruption) but not **origin** (anyone can recompute it). **HMAC**
  mixes a **shared secret key** into the hash, so only a key-holder can produce a valid MAC, proving both
  authenticity and integrity.
- **Verify with `compare_digest`** (constant-time); any tampering (message or MAC) or wrong key fails.
- **Use `hmac`, never `hash(key + message)`**, which is vulnerable to length-extension; HMAC's nested construction
  (RFC 2104) is the vetted fix. Keep the key secret (a `secrets`-generated credential), per-relationship, rotated.
- **Measured:** HMAC costs **~4x** a bare hash (~960 ns vs ~237 ns), under a microsecond, cheap enough to
  authenticate every message crossing a trust boundary.

**Cross-references.** Hashing → Chapter 76. Constant-time comparison → Chapter 77. Key generation (`secrets`) →
Chapter 78. `bytes`/hex → Chapters 37, 7. Authenticated encryption, signatures, key management → Deep P. The
ingress/auth seam → Deep U.
