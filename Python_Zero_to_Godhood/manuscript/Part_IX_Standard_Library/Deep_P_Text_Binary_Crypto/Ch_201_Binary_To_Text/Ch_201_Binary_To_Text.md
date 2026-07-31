# Chapter 120: Binary-to-Text

Deep D separated text from bytes; this chapter is the bridge back, for every channel built to carry only text: JSON documents, URLs, email bodies, log lines, filenames. A binary-to-text codec maps arbitrary bytes into a safe character subset and back, and each member of the `base64`/`binascii` family is one point on a three-way trade: **expansion ratio** (hex 2.00x, base32 1.81x*, base64 1.42x, base85 1.26x on the listing's payload), **alphabet safety** (which characters the channel might eat), and **readability** (hex is diffable by eye; base85 is line noise).

The listing works the family on one payload and lands three contracts. The **urlsafe treaty**: standard base64's alphabet contains `+` and `/`, which form-encoding and paths interpret, the pathological payload encodes to `b'++++'`, corrupted silently by one innocent unquote, and `urlsafe_b64encode` swaps in `-` and `_`. The **padding contract**: `=` pads groups to four, length mod 4 recovers it, so JWTs and Chapter 109's RECORD strip it, and every decoder of trimmed input re-pads with `'=' * (-len % 4)`. And **validation is opt-in**: the default decoder *discards* out-of-alphabet characters (MIME's line wrapping is why), while `validate=True` rejects them, the right setting at any boundary.

The benchmark found a tiering the docs never mention: hex and base64 ride C loops at **GB/s class** (1.15 GB/s encode), while **base32 and base85 are Python-level chunk loops at ~25 MB/s, 40 to 50x out of class**, free for digests, a genuine budget line for bulk.

**This is a Deep P chapter.**
Deep D owns character encodings (text-to-bytes); this chapter owns bytes-to-text, the inverse bridge, and its stdlib family.

## Section index

- **120.1** The family, on one payload
- **120.2** The model: alphabets as treaties, padding as arithmetic
- **120.3** Measurement: implementation tiers, not alphabet tiers
- **120.4** Edges and failure modes
- **120.5** Connections
- **120.6** Exercises
- **120.7** Summary and cross-references

Listings live under `code/ch201/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 120.1 The family, on one payload

```python
# code/ch201/l01_binary_to_text.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- one payload, four codecs, three trades ---
  payload (31 bytes) : b'\x00\n\x14\x1e(2<FPZdnx\x82\x8c\x96\xa0\xaa\xb4\xbe\xc8\xd2\xdc\xe6\xf0\xfa\xfb\xff>>?'
  hex (base16)  2.00x  000a141e28323c46505a646e78828c96a0aab4bec8d2...
  base32        1.81x  AAFBIHRIGI6EMUC2MRXHRAUMS2QKVNF6ZDJNZZXQ7L57...
  base64        1.42x  AAoUHigyPEZQWmRueIKMlqCqtL7I0tzm8Pr7/z4+Pw==...
  base85        1.26x  016ZyC^9@oP+DYec!G?UpsKXK$kN>A@cR4zK0ZG...
  hex doubles but survives anywhere and is diffable by eye;
  base64 is the 4/3 workhorse; base85 squeezes to 5/4 with a
  spikier alphabet; base32 spends 8/5 to stay case-insensitive
  (filesystems, DNS). the codec is a CHANNEL statement
--- the alphabet collision, and the urlsafe fix ---
  standard b64 : b'++++'   ('+' and '/' live in the alphabet)
  urlsafe  b64 : b'----'   ('-' and '_' instead)
  '+' means space in form-encoding and '/' is the path separator:
  standard base64 inside a URL corrupts SILENTLY on the way
  through one innocent unquote. same 64 symbols, different treaty
--- padding: the contract everyone trims ---
  b64(b'M'   ) = 'TQ=='
  b64(b'Ma'  ) = 'TWE='
  b64(b'Man' ) = 'TWFu'
  decode of trimmed 'TWE' after re-padding : b'Ma'
  '=' pads groups to 4; length mod 4 recovers it, which is why
  JWTs and Chapter 109's RECORD strip it - and why every decoder
  of trimmed input re-pads with '=' * (-len % 4) first
--- validation is opt-in, and the default is forgiving ---
  b64decode(noisy)             : b'Man'
  validate=True on 'T@Fu'      : Error(Only base64 data is allowed)
  the default DISCARDS characters outside the alphabet (newlines
  from MIME wrapping); validate=True rejects them - the right
  setting whenever the input is a boundary, not a mail body
```

**The ratio column is the price list, and the annotations are the channels.**
Hex: 2x, but every byte becomes two characters from `[0-9a-f]`, safe in *any* context, alignable in a diff, greppable, which is why RECORD-style content addresses often stay hex even at 2x. Base64: the 4/3 workhorse of MIME, JSON, and JWTs. Base85: 5/4, used where density matters (git binary diffs, PDF), with `<`, `>`, `&`, quotes in its alphabet, exactly the characters markup channels escape. Base32: *spends* ratio (8/5) to buy a case-insensitive, confusion-resistant alphabet for channels that fold case, filenames, DNS labels, human transcription.

**`b'++++'` is the alphabet collision as a four-character proof.**
A three-byte payload whose base64 is entirely `+`: pass it through one URL layer that decodes `+` as space and the token is garbage, with no error anywhere. The urlsafe variant is the same 64 symbols under a different treaty, and the operational rule is absolute: the codec and the channel are chosen *together*.

**The padding rows are the arithmetic made visible**: 1, 2, 3 input bytes produce `TQ==`, `TWE=`, `TWFu`, output length always a multiple of 4, information content recoverable from length alone, which is *why* trimming is safe and re-padding is mechanical. The listing closes by tying the volume's thread: Chapter 109's RECORD and Chapter 114's lockfiles were `urlsafe_b64encode(...).rstrip(b'=')` all along.

---

## 120.2 The model: alphabets as treaties, padding as arithmetic

**A base-N codec is positional numeration over byte groups.**
Base64 takes 3 bytes (24 bits) to 4 symbols of 6 bits; base32 takes 5 bytes to 8 symbols of 5 bits; base85 takes 4 bytes to 5 symbols of ~6.4 bits (85^5 > 2^32). Expansion is `log(256)/log(N)` rounded to group boundaries, and the group boundary is where padding comes from: a final partial group must declare how many bytes it carried, `=` count in base64, or equivalently, output length mod group size.

**The alphabet is a treaty with a channel, and every codec names its counterparty.**
Standard base64 assumed MIME (where `+/` are safe and lines wrap, hence the forgiving decoder); urlsafe assumed URLs and filenames; base32's uppercase-plus-digits assumed case-folding channels; hex assumed *nothing*, which is its entire value. Choosing a codec is asserting which characters will survive transit unescaped, and mismatches fail the way `b'++++'` fails: silently, at the second hop.

**Forgiveness versus validation is a boundary decision.**
The default decoders skip out-of-alphabet bytes because mail bodies arrive line-wrapped and whitespace-injected; that same forgiveness makes the decoder accept *smuggled* content (two different noisy strings decoding identically, a canonicalisation hazard wherever encoded strings are compared or signed). `validate=True` (and comparing *decoded bytes*, never encoded strings) is the rule at security boundaries, this is Chapter 116's canonicalisation lesson at the codec layer.

**And `binascii` is the machine room**: `hexlify`/`unhexlify` (mirrored as `bytes.hex()`/`bytes.fromhex()`), the CRC32 checksum, and the C engines under `base64`'s b16/b64 paths. The higher `base64` module adds the group arithmetic and variants, in C where it stayed hot (b64) and in Python where it did not (b32/b85), the tiering §120.3 measures.

---

## 120.3 Measurement: implementation tiers, not alphabet tiers

**Methodology.** `code/ch201/bench_codec_throughput.py`.
One megabyte of `os.urandom` bytes per operation; `min` of 7; 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| operation | time / MB | throughput |
|---|---|---|
| `hexlify` | 0.66 ms | 1.60 GB/s |
| `unhexlify` | 0.45 ms | 2.31 GB/s |
| `b64encode` | 0.91 ms | 1.15 GB/s |
| `b64decode` | 1.73 ms | 0.60 GB/s |
| `b32encode` | 47.0 ms | **0.02 GB/s** |
| `b85encode` | 35.9 ms | **0.03 GB/s** |

**The table splits by implementation, not by alphabet mathematics.**
Hex and base64 are `binascii`'s C loops, GB/s class, faster than the disks and networks they feed, never the budget line. Base32 and base85 are Python-level chunk loops inside `base64.py`, **40 to 50x out of class** at ~25 MB/s, a fact no docstring mentions and no alphabet-complexity intuition predicts (base32's math is *simpler* than base64's). For digests and tokens, bytes not megabytes, all four are free; for bulk payloads, the b32/b85 rows are real costs, and the mitigation is either the C-tier codecs or accepting the bill knowingly.

**The cost that always ships is expansion, not CPU.**
The 4/3 tax is paid in wire bytes, storage, and JSON size *forever*, on every copy and every transfer, long after the encode's microseconds are forgotten, which is why base64-in-JSON for large blobs is an architecture smell (multipart, object stores, or Chapter 121's compression-before-encoding are the escapes) and why base85's 6% ratio saving must argue against both its alphabet risks and, now, its 40x encode bill.

**Book I** hits the identical tiering from the other side, its base64 is SIMD-vectorised at 10+ GB/s, and both books file the same two conclusions: codec CPU is a solved problem *where someone bothered*, and expansion is the physics that no implementation removes.

---

## 120.4 Edges and failure modes

**Compare decoded bytes, never encoded strings.**
Padding presence, alphabet variant, line wrapping, and the forgiving decoder all make multiple encodings of one payload, string comparison of tokens is a canonicalisation bug (cache keys that miss, signatures over non-canonical forms). Decode, then compare; or define one canonical encoding and `validate=True` it.

**Trimmed padding breaks strict decoders.**
`b64decode('TWE')` raises; systems exchanging trimmed tokens (JWT's explicit choice) must re-pad. The one-liner is in the listing; the bug appears wherever one side is strict and the other trims.

**`encodebytes` is MIME-flavoured.**
It inserts newlines every 76 characters (mail line limits); using it for tokens produces multi-line "strings" that other systems reject or, worse, forgivingly mangle. `b64encode` for data; `encodebytes` only when speaking actual MIME.

**Hex has two case cultures.**
`hexlify` emits lowercase; other ecosystems emit upper; case-sensitive comparisons of hex digests across systems fail spuriously. Normalise case at boundaries (`casefold`, Chapter 118, earning its keep on machine text).

**CRC32 is a checksum, not a hash.**
`binascii.crc32` detects line noise; it resists no adversary and collides trivially. The moment integrity means anything against *intent*, it is Chapter 122's `hashlib`, and mixing the two up is a security bug wearing a performance costume.

**Base85 variants disagree.**
`b85encode` (RFC 1924 alphabet) and `a85encode` (Ascii85, with `z` compression and `<~ ~>` framing options) are incompatible on the wire; PDFs and git each chose one. Name the variant in protocols, or inherit a cross-decoder mystery.

**And none of this is encryption.**
Encoding is reversible by construction and by anyone; `b64encode` hides nothing. The sentence is obvious and the audit finding is perennial, secrets "protected" by base64 in configs and URLs. Secrecy is Chapter 124's territory; this chapter's codecs are transport, only ever transport.

---

## 120.5 Connections

**Backward.**
Text-to-bytes, the mirror bridge, Deep D. The RECORD hashes and lockfile digests that were urlsafe-trimmed base64 all along, Chapters 109 and 114. Canonicalisation at trust boundaries, Chapter 116. `casefold` for the hex-case edge, Chapter 118.

**Forward.**
Compression before encoding, the escape from the 4/3 tax on compressible payloads, Chapter 121. The digests these codecs carry, Chapter 122; the tokens, Chapter 123; and the constant-time comparisons that make token checks safe, Chapter 124.

**Across books.**
**Book I** vectorises base64 and treats alphabet choice as protocol design, its chapter's core table is this chapter's §120.2 with SIMD lanes added, and the shared system's content addresses cross the language boundary as urlsafe-trimmed base64 precisely because both sides agreed on the treaty once, in a design document, the way alphabets are supposed to be chosen.

---

## 120.6 Exercises

**1. Corrupt a token on purpose.** Round-trip a standard-base64 token through `urllib.parse.quote`/`unquote` and through a form-encoding cycle; find the inputs that corrupt. Repeat with urlsafe and show the class disappears.

**2. Canonicalise or perish.** Build a token cache keyed by encoded string; feed it padded/trimmed/wrapped variants of one payload and count the misses. Fix by decoding at the boundary; re-count.

**3. Tier the codecs yourself.** Measure `a85encode` and `bytes.hex()` against the table; place each in its implementation tier, then read `base64.py` to confirm from source which loops are Python.

**4. The 4/3 architecture review.** Take a real JSON API that embeds base64 blobs; compute its annual transfer-and-storage overhead at its actual volume, and price the multipart redesign against it.

**5. Speak both base85s.** Encode one payload with `b85encode` and `a85encode`; decode each with the other; catalogue the failures, then find which variant your PDF reader and git actually use.

**6. The design question.** The forgiving-by-default decoder serves MIME and betrays boundaries; `validate=True` exists but is opt-in. Argue what the default *should* be if designed today, the installed base of mail-handling code, the security cost of forgiveness (smuggling, non-canonical forms), and the precedent of `csv`'s strict flag, then write the deprecation path you would propose, and the reason PEPs have not.

---

## 120.7 Summary and cross-references

- **A binary-to-text codec is positional numeration over byte groups, and its alphabet is a treaty with a channel**: hex (2.00x, survives anywhere, diffable), base64 (1.42x, the workhorse; urlsafe variant because `+/` die in URLs, `b'++++'` is the proof), base32 (1.81x, case-insensitive channels), base85 (1.26x, markup-hostile alphabet).
- **Padding is arithmetic** (`=` to group boundaries; length mod 4 recovers it), so trimming is safe and re-padding is `'=' * (-len % 4)`, the JWT and RECORD convention, tied back to Chapters 109 and 114.
- **Decoders forgive by default** (MIME's line wrapping) and **validate on request**, forgiveness at a boundary is a canonicalisation hazard: compare decoded bytes, never encoded strings.
- **Measured: implementation tiers, not alphabet tiers**, hex/base64 in C at GB/s (1.15 GB/s encode), **base32/base85 in Python at ~25 MB/s, 40-50x out of class**; and the cost that always ships is the expansion, paid forever on every copy.
- **Encoding is not encryption**, and CRC32 is not a hash; secrecy and integrity live three chapters ahead.

**Cross-references.** Text-to-bytes → Deep D. RECORD and lockfile digests → Chapters 109, 114. Canonicalisation at boundaries → Chapter 116. Compression before encoding → Chapter 121. Digests → Chapter 122. Tokens and comparisons → Chapters 123, 124.
