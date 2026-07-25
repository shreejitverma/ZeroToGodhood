# Chapter 60: UTF Codecs and the BOM

A team storing a large corpus of Chinese text picks UTF-8 "because it is the standard," and their storage
bill is a third higher than it needs to be. UTF-8 encodes most CJK characters in **3 bytes**, while UTF-16
encodes the entire Basic Multilingual Plane, including nearly all CJK, in **2**. Measured, a 100,000-character
Chinese document is 300,000 bytes in UTF-8 but 200,000 in UTF-16. UTF-8 is the right *default*, ASCII-
compatible, no byte-order ambiguity, dominant on the web and on disk, but it is not always the *smallest*, and
the codec choice is a size trade that depends on the script. Meanwhile a different team decodes a file with a
byte-order mark as plain UTF-8 and finds a mysterious invisible `﻿` at the start of every string, breaking
their parser. Both problems are about knowing what the UTF codecs actually do with bytes.

This chapter continues **Deep D** with the UTF codecs, UTF-8, UTF-16, UTF-32, their size trade-offs, and the
byte-order mark (BOM). It is the on-disk/on-wire counterpart to Chapter 56's in-memory representation: the
`str` picks a width for O(1) indexing; the codec picks an encoding for size and interchange.

## Section index

- **60.1** Three codecs, three size profiles
- **60.2** The BOM and its traps
- **60.3** Measurement: size by codec and script
- **60.4** Edges and failure modes
- **60.5** Connections
- **60.6** Exercises
- **60.7** Summary and cross-references

Listings live under `code/ch060/` and are re-executed by `make verify` on both interpreters.

---

## 60.1 Three codecs, three size profiles

```python
# code/ch060/l01_codecs.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- same text, three codecs, different byte counts ---
  text           chars  utf-8  utf-16  utf-32
  ASCII             11     11      22      44
  Latin (café)      12     15      24      48
  CJK (世界)           8     24      16      32
  emoji              4     16      16      16
  (UTF-8 wins for ASCII/Latin; UTF-16 wins for CJK; UTF-32 always 4/char)
--- the BOM: a byte-order / signature mark ---
  utf-8      : f09f9880  (no BOM)
  utf-8-sig  : efbbbff09f9880  (EF BB BF prefix)
  utf-16     : fffe4100  (FF FE BOM, then LE data)
  utf-16-le  : 4100  (explicit endian, no BOM)
--- decoding utf-8-sig strips the BOM; utf-8 leaves it as a char ---
  decode as utf-8-sig : 'text' (len 4, clean)
  decode as utf-8     : '\ufefftext' (len 5, leading U+FEFF)
  first char is BOM   : True
```

The same text encodes to different byte counts under each codec, and the winner depends on the script.
**UTF-8** is variable-width: **1 byte** for ASCII, **2** for Latin/Greek/Cyrillic (so `café` is 15 bytes for
12 characters, `é` takes 2), **3** for most CJK, **4** for astral (emoji). **UTF-16** is 2 bytes for the whole
BMP (so CJK is 2 bytes, *smaller* than UTF-8's 3) and 4 for astral (a surrogate pair). **UTF-32** is always
**4 bytes per character**, uniform and trivial to index, but the largest.

So UTF-8 wins for ASCII and Latin text (the Western-language and code/markup case), UTF-16 wins for CJK-
dominant text (the `世界` row: 16 bytes vs UTF-8's 24), and UTF-32 never wins on size (it is an in-memory
convenience, not a storage format). The emoji row is a tie at 16 bytes, all three spend 4 bytes on an astral
character.

---

## 60.2 The BOM and its traps

The **byte-order mark** is the character U+FEFF placed at the start of a stream, and it serves two purposes.
For **UTF-16/UTF-32**, byte order matters (is a 2-byte unit big- or little-endian?), and the BOM disambiguates
it: `"A".encode("utf-16")` produces `fffe4100`, the `FF FE` BOM signaling little-endian, then the data. Encode
with an *explicit* endianness (`utf-16-le`) and there is no BOM, just `4100`. When you control both ends, use
the explicit `-le`/`-be` variant and skip the BOM; when you write a file others will read, include the BOM so
they can detect the byte order.

For **UTF-8**, byte order is irrelevant (it is a byte sequence), so a BOM is not needed, but Windows tools
sometimes write one as a *signature* to mark a file as UTF-8. That is the `utf-8-sig` codec: it prepends
`EF BB BF`. Here is the trap the listing shows: if a file written as `utf-8-sig` is decoded as plain `utf-8`,
the BOM is *not* stripped, it becomes a leading `﻿` character in the string (`'﻿text'`), an invisible
character that breaks header parsing, JSON, CSV, and equality checks. Decoding as `utf-8-sig` strips it
correctly (`'text'`). The symmetric trap: writing `utf-8-sig` when the consumer expects clean UTF-8 injects a
BOM they will choke on.

The rule: **default to plain UTF-8 (no BOM) for interchange**; use `utf-8-sig` only when a specific tool
requires the signature, and when *reading* files of unknown origin, decode with `utf-8-sig` (which strips a BOM
if present and behaves like `utf-8` if absent) to be robust to a stray mark. For UTF-16/32, prefer explicit
`-le`/`-be` when you own both ends.

---

## 60.3 Measurement: size by codec and script

**Methodology.** `code/ch060/bench_codec_size.py`. Encoded byte size (`len(encoded)`, deterministic) of a
100,000-character document in UTF-8, UTF-16, and UTF-32, for three scripts. CPython 3.13.5, Apple M3 Pro, macOS
27.0, arm64.

| script (100,000 chars) | UTF-8 | UTF-16 | UTF-32 | smallest |
|---|---|---|---|---|
| ASCII | **100,000** | 200,000 | 400,000 | UTF-8 |
| Latin (é) | **200,000** | 200,000 | 400,000 | UTF-8 (tie) |
| CJK (世) | 300,000 | **200,000** | 400,000 | **UTF-16** |

The table makes the trade concrete. For **ASCII**, UTF-8 is half the size of UTF-16 and a quarter of UTF-32.
For **Latin**, UTF-8 ties UTF-16 (both 2 bytes/char here). For **CJK**, UTF-16 is a third smaller than UTF-8
(2 vs 3 bytes/char). UTF-32 is always the largest. This is deterministic (byte counts, not timing) and
identical on both interpreters.

The rule: **default to UTF-8.** It is the smallest for the ASCII and Latin text that dominates code, markup,
logs, and Western-language content; it is ASCII-compatible (an ASCII file *is* valid UTF-8); it has no byte-
order ambiguity; and it is the universal interchange standard. **Consider UTF-16 only for large, predominantly-
CJK corpora** where the ~33% saving is worth giving up ASCII-compatibility and taking on byte-order handling.
**Never use UTF-32 for storage**, its uniform 4-byte width is an in-memory indexing convenience (and Python's
own `str` uses a similar fixed-width scheme internally, Chapter 56), not a disk format. As with the number-type
and container choices elsewhere in the book, match the encoding to the data: UTF-8 unless the script and scale
make UTF-16's size win decisive.

---

## 60.4 Edges and failure modes

**A stray BOM decoded as UTF-8.** §60.2. A `utf-8-sig` file read as plain `utf-8` yields a leading `﻿`
that breaks parsers, JSON, and equality. Read unknown files with `utf-8-sig` (strips a BOM if present); write
plain `utf-8` for interchange.

**Choosing UTF-8 for CJK-heavy storage.** §60.3. UTF-8 is 3 bytes/CJK char vs UTF-16's 2. For large CJK
corpora, UTF-16 (or compression on UTF-8) can save a third. Do not assume UTF-8 is smallest for all scripts.

**UTF-16 without a byte order.** `utf-16` (no suffix) writes a BOM on encode and reads it on decode; `utf-16-le`/
`-be` do not. Mixing them (write `utf-16`, read `utf-16-le`) leaves the BOM as a `﻿` in the data or
misreads endianness. Pin the variant on both ends.

**UTF-16 surrogate handling.** Astral characters are a *surrogate pair* in UTF-16 (2 code units, 4 bytes), and
a truncated stream can split a pair, producing an invalid lone surrogate. Frame UTF-16 data on character
boundaries; do not cut mid-pair.

**Assuming byte length equals character count.** None of the UTF codecs is 1 byte = 1 character except ASCII in
UTF-8. Size a buffer or column from `len(encoded)`, and count characters with `len(str)` (Chapter 56); never
conflate them.

**Legacy non-UTF codecs.** Latin-1, Windows-1252, Shift-JIS, GBK still appear in real data. They are not
UTF and cannot represent all Unicode; decoding UTF-8 bytes as Latin-1 (or vice versa) produces mojibake. Detect
or declare the encoding; do not guess (Chapter 57's error handlers help when you must be lenient).

---

## 60.5 Connections

**Backward.** The in-memory `str` width (PEP 393) that these codecs serialize is Chapter 56. The `encode`/
`decode` boundary and explicit-encoding rule are Chapter 7. The error handlers for bytes that do not fit are
Chapter 57. The raw `bytes` the codecs produce are Chapter 37.

**Forward.** File I/O writing these bytes (and the `encoding=`/`newline=` parameters) is Chapter 40. Encoding
detection heuristics (`chardet`/`charset-normalizer`) and legacy codec handling are Deep D application topics.
Compression of UTF-8 text is a Deep P/storage topic.

**Across books.** Codec choice is how Book II controls the on-disk and on-wire cost of the text it hands
**Book III**. A **Book III** corpus store defaults to UTF-8 for its ASCII-heavy metadata and code, but a CJK-
dominant document store may use UTF-16 (or compressed UTF-8) to cut a third of the bytes, and every boundary
reads defensively with `utf-8-sig` to survive a stray BOM. The §60.3 size trade is the calculation behind that
storage decision. **Deep U** owns the text-storage seam.

---

## 60.6 Exercises

**1. Reproduce the size trade.** Encode ASCII, Latin, CJK, and emoji text in UTF-8, UTF-16, and UTF-32 and
compare the byte counts. Explain which codec wins for each script and why.

**2. Trip over the BOM.** Write a string as `utf-8-sig`, decode it as plain `utf-8`, and show the leading
`﻿`. Then decode as `utf-8-sig` and show it is clean. Explain why reading unknown files as `utf-8-sig` is
safer.

**3. Handle endianness.** Encode text as `utf-16` (with BOM) and as `utf-16-le` (no BOM) and compare the bytes.
Decode each with the matching and mismatching variant and observe the failures. Explain when to use the BOM
variant.

**4. Measure a corpus.** Take (or synthesize) a large CJK document and compute its UTF-8 vs UTF-16 size. Confirm
UTF-16 is smaller and quantify the saving. Explain the 3-vs-2 bytes/char difference.

**5. The design question.** Python (and the world) default to UTF-8 even though it is not the smallest for all
scripts. Argue why UTF-8 is the right default despite the CJK size penalty. Your answer must use the §60.3
measurement, weigh ASCII-compatibility and byte-order simplicity against size, and say when UTF-16 is
nonetheless the right choice.

---

## 60.7 Summary and cross-references

- **UTF-8** is variable-width (1 ASCII, 2 Latin, 3 CJK, 4 astral), ASCII-compatible, byte-order-free, the
  **interchange default**. **UTF-16** is 2 bytes for the BMP (**smaller than UTF-8 for CJK**), 4 for astral.
  **UTF-32** is always 4 bytes/char (in-memory, not storage).
- **Measured:** a 100,000-char document is 100 KB (ASCII) / 200 KB (Latin) / 300 KB (CJK) in UTF-8, but 200 KB
  in UTF-16 regardless, so UTF-16 wins for CJK, UTF-8 for ASCII/Latin, UTF-32 never.
- The **BOM** (U+FEFF) marks byte order for UTF-16/32 and signatures `utf-8-sig`; decoding a BOM'd file as plain
  `utf-8` leaves a stray `﻿`. **Read unknown files as `utf-8-sig`; write plain `utf-8`.**
- **Default to UTF-8;** consider UTF-16 only for large CJK-heavy corpora; never UTF-32 for storage.

**Cross-references.** In-memory `str` width → Chapter 56. `encode`/`decode` → Chapter 7. Error handlers →
Chapter 57. `bytes` → Chapter 37. File I/O and `encoding=` → Chapter 40. Encoding detection and legacy codecs →
Deep D. The text-storage seam → Deep U.
