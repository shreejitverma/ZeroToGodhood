# Chapter 77: Constant-Time Comparison

Chapter 76 ended on a warning: verify a password (or a token, or an HMAC) with `hmac.compare_digest`, not `==`.
This chapter is why. When you compare two byte strings with `==`, Python **short-circuits**: it returns `False`
at the *first* differing byte. That is a fine optimization for ordinary data and a security hole for secrets,
because the *time* `==` takes reveals *how many leading bytes matched*. An attacker submitting guesses against a
secret token can measure that timing, keep the guess that took longest (matched the most prefix), and recover the
secret one byte at a time, a **timing attack**, without ever seeing the secret. `hmac.compare_digest` closes the
hole by comparing in **constant time**: it always examines every byte regardless of where they differ, so its
duration is independent of the contents and leaks nothing. The cost of that guarantee is small and measurable,
`compare_digest` is **3.6x** a `==` (27 ns versus 7.5 ns), a few nanoseconds to make the comparison timing-safe.

This chapter continues **Deep O** with constant-time comparison: why `==` leaks timing, how `compare_digest`
prevents it, and the small price of safety. It is the verification counterpart to Chapter 76's hashing, together
they are how secrets are stored and checked without leaking.

## Section index

- **77.1** `==` short-circuits; `compare_digest` does not
- **77.2** How the timing leak becomes an attack
- **77.3** Measurement: the price of constant time
- **77.4** Edges and failure modes
- **77.5** Connections
- **77.6** Exercises
- **77.7** Summary and cross-references

Listings live under `code/ch077/` and are re-executed by `make verify` on both interpreters.

---

## 77.1 `==` short-circuits; `compare_digest` does not

```python
# code/ch077/l01_compare_digest.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- compare_digest gives the correct answer, in constant time ---
  compare_digest(secret, correct)    : True
  compare_digest(secret, wrong_last) : False
  compare_digest(secret, wrong_first): False
--- == gives the same ANSWER but leaks timing (short-circuits) ---
  secret == correct     : True
  secret == wrong_first : False  (== stops at byte 0)
  secret == wrong_last  : False  (== scanned all 8 bytes)
  same results, but == returns FASTER for wrong_first than wrong_last
--- the rule ---
  compare secrets (tokens, HMACs, digests, API keys) with compare_digest
  never with ==, which reveals the match length through its timing
  (compare_digest requires equal-length inputs of the same type)
```

Both `==` and `compare_digest` give the *same answers*: `True` for the equal value, `False` for either wrong
one. The difference is *timing*. `secret == wrong_first`, which differs at byte 0, returns as soon as `==` sees
that first mismatch. `secret == wrong_last`, which matches the first seven bytes and differs only at the last,
makes `==` scan all eight before returning. So `==` is *faster* for a value that differs early and *slower* for
one that matches a long prefix, and that timing difference is a signal about the secret. `compare_digest`
examines every byte in both cases, so its timing is the same whether the mismatch is at byte 0 or byte 7.

The listing uses fixed bytes for reproducibility, but in the real use, one side is a *secret* the attacker is
trying to guess. `compare_digest` (in both `hmac` and `secrets`) requires the two inputs to be the *same type*
and, for the constant-time guarantee, the same length, comparing different lengths still returns the right
answer but can leak the length.

---

## 77.2 How the timing leak becomes an attack

A timing attack turns "faster when it matches more" into a byte-by-byte recovery. Suppose a server checks an
API token with `submitted == real_token`. The attacker submits `AAAA...`, then `BAAA...`, and so on, measuring
the server's response time for each. Because `==` short-circuits, the guess whose *first byte* matches the real
token's first byte makes `==` proceed to the *second* byte before failing, taking *slightly longer* than guesses
that fail at byte 0. The attacker keeps the byte that was slowest, now they know byte 0, and repeats for byte 1,
then byte 2, recovering the whole token in *linear*, not exponential, tries. The timing difference per byte is
tiny (nanoseconds), but with enough samples and statistics it is measurable, and over a network the classic
result is that even ~100 ns differences are exploitable with sufficient averaging.

`compare_digest` defeats this by making the comparison time *independent of the data*: it XORs corresponding
bytes and accumulates the differences, examining all of them, so whether the inputs match at byte 0 or byte 31,
the work, and the time, is identical. There is no per-byte timing signal to measure, so the byte-by-byte
recovery is impossible. This is the same principle as the slow KDF of Chapter 76 (deny the attacker an
efficiency), applied to *comparison* rather than *hashing*.

The rule: **compare any secret, an API token, a session ID, an HMAC/signature, a password digest, a CSRF token,
with `compare_digest`, never `==`.** The moment one side of a comparison is a secret an attacker can probe by
submitting guesses, `==`'s short-circuit is a vulnerability. For non-secret data (comparing two user-visible
strings, sorting, dict lookups), `==` is correct and its speed is a feature, the timing of comparing public data
reveals nothing worth hiding.

---

## 77.3 Measurement: the price of constant time

**Methodology.** `code/ch077/bench_compare.py`. `==` versus `hmac.compare_digest` on 32-byte values that differ
at the first byte. `min` per call; ratio relative to `==`. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| compare 32 bytes | min per call | ratio |
|---|---|---|
| `==` (short-circuits) | **7.5 ns** | 1.00x |
| `compare_digest` (constant-time) | **27 ns** | **3.59x** |

`compare_digest` is **3.6x** a `==`, 27 ns versus 7.5 ns, because `==` short-circuits at the first differing
byte (here byte 0, so it barely starts) while `compare_digest` always processes all 32 bytes. The 3.6x looks
large as a ratio but is ~20 nanoseconds in absolute terms, and, crucially, it is a *fixed* cost per comparison,
not per byte of secret, so it does not scale with anything an attacker controls.

The rule: **pay the constant-time cost for any secret comparison; it is negligible and it is the whole defense.**
A login or token check happens once per request, so ~20 ns of extra comparison time is nothing against the
request's real work, and it removes an entire class of attack. The `==` speed advantage is precisely the leak
(faster-when-it-matches-less), so "optimizing" a secret comparison back to `==` reintroduces the vulnerability.
This is the security inversion again, as with the slow KDF of Chapter 76, the *variable* timing that makes `==`
fast is the thing you must give up. Use `compare_digest` and treat its small, constant overhead as the price of
not leaking.

---

## 77.4 Edges and failure modes

**Comparing a secret with `==`.** §77.2. Its short-circuit leaks the match length via timing, enabling byte-by-
byte recovery. Use `compare_digest`.

**Different-length inputs to `compare_digest`.** The constant-time guarantee holds for equal-length inputs;
comparing different lengths returns the correct answer but can leak the length (and mixing `str` and `bytes`
raises `TypeError`). Compare fixed-length digests/tokens; hash variable-length secrets to a fixed length first.

**Constant-time comparison, variable-time everything else.** `compare_digest` only fixes the *comparison*. If the
surrounding code branches on the secret (an early `return` on a length mismatch, a different code path for
invalid tokens) it can leak timing elsewhere. Keep the whole verification path data-independent.

**Comparing after a fast operation that already leaked.** Comparing the *hash* of a secret is common and fine
(hash both sides, `compare_digest` the digests), but if the hashing itself is data-dependent or you compared the
raw secret earlier with `==`, the leak already happened. Audit the full path.

**Assuming `==` is safe for "internal" secrets.** A secret compared only server-side can still be timing-attacked
if an attacker can trigger the comparison and measure the response (most tokens are attacker-triggerable). Do not
assume internal means safe; use `compare_digest` for all secret comparisons.

**Over-applying constant-time comparison.** For *non-secret* data (public identifiers, user strings, keys of a
dict), `==` is correct and faster, and constant-time comparison is pure waste. Apply it only where one side is a
secret an attacker probes.

---

## 77.5 Connections

**Backward.** The password digests this compares are Chapter 76; the `bytes` being compared are Chapter 37. The
short-circuit behavior of `==` is the string/bytes comparison of Chapter 7 (and the `==` fast path of Chapter
61). The security-inversion framing (give up the efficiency) is Chapter 76.

**Forward.** HMAC (message authentication, whose signatures you verify with `compare_digest`) and the crypto
toolkit are Deep P. `secrets` for generating the tokens you later compare is a Deep O topic. Testing that a
verification path is constant-time (and free of secret-dependent branches) is Deep O's security-testing material.

**Across books.** Constant-time comparison is a security boundary Book II enforces on every secret check before
**Book III**. A **Book III** service verifying API keys, session tokens, or webhook signatures uses
`compare_digest` throughout, so an attacker cannot recover a credential by timing the auth endpoint, and reserves
`==` for the non-secret comparisons that dominate the rest of the code. The §77.2 attack is exactly the kind of
subtle leak that passes functional tests (the answers are correct) yet compromises the system, which **Deep U**
guards against at the auth seam. **Deep P** owns the primitives.

---

## 77.6 Exercises

**1. Confirm the mechanism.** Reproduce §77.1: show `==` and `compare_digest` agree on results but that `==`
scans a long matching prefix while stopping early on an early mismatch. Explain what timing information `==`
leaks.

**2. Sketch the attack.** Describe, step by step, how an attacker recovers a token byte-by-byte from `==`'s
timing. Explain why `compare_digest` makes each guess take the same time.

**3. Measure the cost.** Run §77.3's benchmark and confirm `compare_digest` costs more than `==`. Explain why the
overhead is fixed per comparison and negligible for a per-request check.

**4. Find a leak beyond comparison.** Write a verification function that uses `compare_digest` but `return`s early
on a length mismatch, and explain how that early return can still leak. Fix it to be data-independent.

**5. The design question.** `==` is fast because it short-circuits, which is exactly the leak. Argue why secret
comparison must give up that speed. Your answer must use the §77.3 measurement, the §77.2 attack, and state
precisely which comparisons need constant time and which do not.

---

## 77.7 Summary and cross-references

- **`==` on bytes/str short-circuits** at the first differing byte, so its *timing leaks how many leading bytes
  matched*, enabling a **timing attack** that recovers a secret byte-by-byte.
- **`hmac.compare_digest`/`secrets.compare_digest`** compare in **constant time** (examine every byte), leaking
  nothing about the contents. Use them for any comparison where one side is a secret (tokens, HMACs, digests, API
  keys).
- **Measured:** `compare_digest` is **3.6x** a `==` (27 ns vs 7.5 ns), a fixed ~20 ns per comparison, negligible
  for a per-request check and the entire defense.
- **Edges:** compare equal-length, same-type values; keep the whole verification path data-independent (no
  secret-dependent early returns); use `==` for non-secret data.

**Cross-references.** Password digests → Chapter 76. `bytes` → Chapter 37. `==` comparison and its fast path →
Chapters 7, 61. HMAC and crypto → Deep P. `secrets` token generation → Deep O. The auth seam → Deep U.
