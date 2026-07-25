# Chapter 56: Flexible String Representation (PEP 393)

A log-processing service holds a million-character buffer of mostly-ASCII text and budgets ~1 MB for it.
In production the buffer sometimes costs **4 MB** for the same million characters, and the cause is a single
emoji. Since Python 3.3, a `str` stores its characters at the *narrowest width that fits its widest
codepoint*, 1 byte if every character is Latin-1, 2 bytes if the widest is in the Basic Multilingual Plane,
4 bytes if any character is astral (above U+FFFF, where most emoji live), and that width is a property of the
*whole string*. So one astral character forces every character in the string to 4 bytes: a 1,000,041-byte
ASCII string becomes 4,000,060 bytes, **4x**, for one extra character. The memory did not grow with the
content; it quadrupled because of one codepoint's *width*.

That mechanism, PEP 393's "flexible string representation," is where **Deep D** (text, bytes, encodings)
begins, because it is the internal reality beneath everything Chapter 7 said about text. Chapter 7 taught the
`str`/`bytes` boundary and encodings *as behavior*; this volume opens by showing how a `str` is actually laid
out in memory, and why that layout has consequences you can measure.

## Section index

- **56.1** One string, three possible widths
- **56.2** Why the width is a whole-string property
- **56.3** Measurement: the four-fold blowup
- **56.4** Edges and failure modes
- **56.5** Connections
- **56.6** Exercises
- **56.7** Summary and cross-references

Listings live under `code/ch056/` and are re-executed by `make verify` on both interpreters.

---

## 56.1 One string, three possible widths

```python
# code/ch056/l01_pep393.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- footprint scales with the widest codepoint, not the content ---
  ASCII (a)    len=1000 getsizeof= 1041 bytes (1.0/char + header)
  Latin-1 (é)  len=1000 getsizeof= 1057 bytes (1.1/char + header)
  BMP (世)      len=1000 getsizeof= 2058 bytes (2.1/char + header)
  astral (😀)   len=1000 getsizeof= 4060 bytes (4.1/char + header)
--- one astral character widens the ENTIRE string ---
  1000 ASCII chars        :  1041 bytes
  999 ASCII + 1 emoji     :  4060 bytes (4x: the emoji widened all 1000)
--- len() is characters, not bytes; indexing is O(1) at any width ---
  'a😀b' len (characters) : 3
  utf-8 encoded bytes     : 6 (variable-width on disk)
  s[1] is the emoji       : True
```

A `str` of 1000 characters costs a different number of bytes depending on its *widest* codepoint. Pure ASCII
(and any Latin-1 text, `é` is U+00E9) uses **1 byte per character**: ~1 KB plus a small header. Text whose
widest character is in the BMP (`世`, U+4E16) uses **2 bytes per character**: ~2 KB. Text containing any
astral character (`😀`, U+1F600) uses **4 bytes per character**: ~4 KB. Same 1000 characters, three very
different footprints, chosen automatically by the widest codepoint present.

The last block states the invariants this buys. `len(s)` counts *characters* (code points), not bytes, `"a😀b"`
has length 3 regardless of the emoji's width, and indexing is **O(1)** at any width because every character in
a given string is the *same* fixed number of bytes. That fixed-width-per-string design is the whole point of
PEP 393: it keeps `len` and indexing O(1) (unlike UTF-8, where a character is variable-width and indexing
would be O(n)) while spending only as many bytes per character as the string actually needs.

---

## 56.2 Why the width is a whole-string property

The design forces a choice: to keep O(1) indexing, every character in a string must occupy the *same* number
of bytes, so `s[i]` is a constant-offset load. But different characters need different widths, `a` fits in 1
byte, `世` needs 2, `😀` needs 4. PEP 393 resolves this by picking *one* width for the whole string, the
smallest that fits its *widest* character. A string is stored as 1-byte (`Py_UCS1`, Latin-1), 2-byte
(`Py_UCS2`, BMP), or 4-byte (`Py_UCS4`, full Unicode) elements, uniformly.

The consequence is the chapter's headline: adding a single wide character does not add a few bytes, it
*promotes the whole string to a wider representation*. A million ASCII characters at 1 byte each is 1 MB; the
instant one astral character joins them, all million must be re-stored at 4 bytes each, 4 MB. There is no
"mostly narrow with a few wide" representation, because that would break the constant-offset indexing.
(Concatenation and other operations that produce a new string compute the result's width from its inputs;
join a wide string to a narrow one and the result is wide.)

This is the trade PEP 393 makes deliberately: **O(1) indexing and `len`, at the cost of width being an
all-or-nothing property of the string.** The alternative, storing everything as UTF-8 (variable-width, so
mostly-ASCII text stays ~1 byte/char even with a stray emoji), would make indexing O(n), the price Python
declined to pay for `str`. That is exactly why bulk text on disk and on the wire *is* UTF-8 (§56.4): the
storage format optimizes for size, the in-memory `str` optimizes for O(1) access.

---

## 56.3 Measurement: the four-fold blowup

**Methodology.** `code/ch056/bench_string_memory.py`. `sys.getsizeof` (deterministic) of a 1,000,000-character
string at each representation width, and of a pure-ASCII string plus one emoji. CPython 3.13.5, Apple M3 Pro,
macOS 27.0, arm64.

| 1,000,000-character string | bytes | per char |
|---|---|---|
| pure ASCII | **1,000,041** | 1.0 |
| BMP (2-byte) | **2,000,058** | 2.0 |
| astral (4-byte) | **4,000,060** | 4.0 |
| ASCII + 1 emoji | **4,000,060** | 4.0 |

The footprint is exactly the character count times the representation width, plus a fixed ~40-byte header.
The last row is the finding: a million ASCII characters cost ~1 MB, but the *same million characters* with one
of them replaced by an emoji cost ~4 MB, a **4.0x** blowup driven by a single codepoint. This is deterministic
(`getsizeof` is exact) and identical on both interpreters, it is not a measurement subject to noise but a
structural fact of the representation.

The practical rule: **for large, mostly-ASCII text that might contain stray wide characters, do not hold it as
one giant `str`.** Keep bulk text as **UTF-8 `bytes`** (variable-width, so ASCII stays ~1 byte/char and a
stray emoji adds only its own few bytes, not a 4x multiplier), and decode to `str` only the spans you actually
operate on. This is the same "store compact, materialize what you use" discipline as the buffer/array chapters
(37, 39): the `str` is the convenient O(1)-indexable working form, UTF-8 `bytes` is the compact storage form,
and holding a multi-megabyte document as a single `str` pays the width tax on every character for the
convenience of a few operations. Decode late, encode early, keep the bulk as bytes.

---

## 56.4 Edges and failure modes

**Holding large text as one `str`.** §56.3. A stray wide character can quadruple the memory. Store bulk text as
UTF-8 `bytes`; decode spans on demand.

**Assuming `len(s)` is the byte size.** `len(s)` is *characters*; the byte size depends on the width
(`sys.getsizeof`) in memory and on the encoding (`len(s.encode("utf-8"))`) on disk. Never size a buffer or a
database column from `len(s)` alone when bytes are what matter.

**Assuming one character is one "user-perceived character."** A code point is not a grapheme. `"👨‍👩‍👧"` is one
family emoji but several code points (with zero-width joiners), so `len` and indexing operate on code points,
not on what a human sees as one character. For grapheme-aware handling you need a library (`regex`,
`unicodedata` awareness), not raw `str` indexing.

**Comparing visually-equal strings that differ in code points.** `"é"` can be one code point (U+00E9) or two
(`e` + U+0301 combining accent); they look identical but are unequal and have different lengths and widths.
Normalize with `unicodedata.normalize` (a later Deep D chapter) before comparing or hashing user text.

**Surrogate and astral confusion on other platforms.** Some environments (older Windows APIs, Java, JavaScript)
use UTF-16 and expose astral characters as *surrogate pairs* (length 2). Python's `str` counts an astral
character as length 1. Round-tripping through such a system can change lengths; be explicit about the boundary.

**Micro-optimizing width.** You cannot ask a `str` to use a narrower representation than its content requires,
the width is determined by the data. The lever is not the `str` but *what you store*: keep bytes if you do not
need `str` operations.

---

## 56.5 Connections

**Backward.** The `str`/`bytes` boundary and `encode`/`decode` this refines are Chapter 7. The `bytes` and
buffer types that UTF-8 storage uses are Chapter 37. The "store compact, materialize what you use" discipline
is Chapters 37 and 39 (buffers, arrays). The object header included in `getsizeof` is the object model of
Chapter 4 and Deep A.

**Forward.** Encodings and codecs (UTF-8/16/32, error handlers), Unicode normalization (NFC/NFD), and case
folding are the rest of **Deep D**. The C-level `PyUnicodeObject` layout and the `Py_UCS1/2/4` storage are a
Deep D/Deep A internals topic. String operations' performance (search, join) builds on this representation.

**Across books.** The width tax is why Book II hands **Book III** *bytes*, not giant strings, at scale. A
**Book III** ingest pipeline reads a corpus as UTF-8 `bytes`, decodes documents (or spans) to `str` only to
tokenize or analyze them, and never holds the whole corpus as one wide `str`, so a few emoji in a large
document do not quadruple the resident set. The §56.3 measurement is the reason the ingest path keeps bulk text
as bytes. **Deep U** owns the text-at-scale seam.

---

## 56.6 Exercises

**1. Reproduce the widths.** Use `sys.getsizeof` to show the 1-, 2-, and 4-byte-per-character footprints for
ASCII, BMP, and astral strings of equal length. Explain what determines the width.

**2. Trigger the blowup.** Build a large ASCII string, measure it, append one emoji, and measure again. Confirm
the ~4x jump. Explain why one character changes the whole string's representation.

**3. Characters vs bytes.** For a mixed string, compare `len(s)`, `sys.getsizeof(s)`, and
`len(s.encode("utf-8"))`. Explain what each measures and when each is the number you need.

**4. Store compact.** Hold a large mostly-ASCII document as `str` and as UTF-8 `bytes`, add one emoji to each,
and compare the memory. Explain why the `bytes` form does not blow up and when you would still want the `str`.

**5. The design question.** PEP 393 makes width an all-or-nothing property of a string to keep O(1) indexing,
accepting the 4x blowup a single astral character can cause. Argue whether this is the right trade. Your answer
must use the §56.3 measurement, contrast it with UTF-8's variable-width storage (O(n) indexing), and say when
you should keep text as bytes to avoid the tax.

---

## 56.7 Summary and cross-references

- **PEP 393 (3.3+)** stores a `str` at the **narrowest width that fits its widest codepoint**: 1 byte
  (Latin-1), 2 bytes (BMP), or 4 bytes (astral), uniformly across the whole string.
- The width is a **whole-string property** (so indexing and `len` stay O(1)), so a **single astral character
  promotes every character to 4 bytes**.
- **Measured:** a million-character ASCII string is ~1 MB; the same million with one emoji is ~4 MB, a **4.0x**
  blowup (deterministic, identical on both interpreters).
- **Store bulk text as UTF-8 `bytes`** (variable-width, no width tax) and decode spans to `str` on demand;
  `len` is characters, not bytes; normalize before comparing user text.

**Cross-references.** `str`/`bytes` and encodings → Chapter 7. `bytes`/buffers → Chapter 37. Compact storage
discipline → Chapters 37, 39. Object header → Chapter 4, Deep A. Codecs, normalization, case folding → the rest
of Deep D. The text-at-scale seam → Deep U.
