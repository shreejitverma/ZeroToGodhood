# Chapter 58: Unicode Normalization

A user signs up as "café" and later cannot log in, even with the identical username, because the signup form
sent the accented `é` as one precomposed code point (U+00E9) and the login form sent it as two (`e` plus a
combining acute, U+0301). The two strings *look* identical, pixel for pixel, but they are different sequences
of code points: different lengths (4 versus 5), unequal under `==`, different hashes, so the dictionary lookup
keyed on the first form misses the second entirely. Nothing is broken; Unicode simply allows the same visible
text to be encoded more than one way, and `str` equality is code-point equality, not visual equality. The fix
is **normalization**: `unicodedata.normalize("NFC", s)` maps both forms to one canonical representation, after
which they are equal. And it is nearly free, on already-normalized (or ASCII) text, `normalize` returns in
**~16 ns**, so normalizing user input on the boundary costs essentially nothing in the common case.

This chapter continues **Deep D** with Unicode normalization: why visually-equal strings can be code-point-
unequal, the four normal forms, and the rule to normalize text before comparing, hashing, deduplicating, or
keying on it. It is a correctness (and security) chapter, the login bug is benign; the same mechanism enables
homograph attacks and duplicate-account bypasses.

## Section index

- **58.1** One appearance, two encodings
- **58.2** The four normal forms
- **58.3** Measurement: normalization is nearly free when it can be
- **58.4** Edges and failure modes
- **58.5** Connections
- **58.6** Exercises
- **58.7** Summary and cross-references

Listings live under `code/ch058/` and are re-executed by `make verify` on both interpreters.

---

## 58.1 One appearance, two encodings

```python
# code/ch058/l01_normalization.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- two strings, one appearance, different code points ---
  composed   len=4  codepoints=['U+0063', 'U+0061', 'U+0066', 'U+00E9']
  decomposed len=5  codepoints=['U+0063', 'U+0061', 'U+0066', 'U+0065', 'U+0301']
  equal?              : False
  same hash?          : False
--- a dict keyed by one form misses the other ---
  lookup decomposed   : None
--- NFC makes them canonically equal ---
  NFC(composed) == NFC(decomposed): True
  normalized length   : 4
--- NFKC also folds compatibility variants ---
  ligature   'fi'  (U+FB01) -> 'fi'
  superscript '2' (U+00B2) -> '22'
  fullwidth  'A'  (U+FF21) -> 'A'
```

The two strings are built explicitly from code points so the source is unambiguous: `composed` is `caf` plus
the precomposed `é` (U+00E9), `decomposed` is `cafe` plus a combining acute accent (U+0301) that renders over
the `e`. They display identically, but they are different sequences: `len` 4 versus 5, `==` is `False`, and
their hashes differ, so a `dict` keyed on `composed` returns `None` for `decomposed`. This is the login bug in
miniature, and it is *silent*: no error, just a lookup that mysteriously fails on text that looks correct.

`unicodedata.normalize("NFC", ...)` fixes it: after normalizing both to NFC (composed form), they are equal and
both have length 4. **NFC** is the normalization you want for equality, comparison, and keys, it composes
characters into their canonical precomposed form so the two spellings of `é` become one.

---

## 58.2 The four normal forms

Unicode defines four normal forms, along two independent axes: **composition** (compose vs decompose) and
**compatibility** (canonical vs compatibility folding).

- **NFC** (Normalization Form C, *canonical composition*): compose to precomposed characters. `é` becomes the
  single U+00E9. **This is the default choice** for storing, comparing, and keying text, it is the most compact
  and the form most systems produce.
- **NFD** (*canonical decomposition*): decompose to base character plus combining marks. `é` becomes `e` +
  U+0301. Useful when you need to *process* the marks (e.g. strip accents by removing combining characters).
- **NFKC / NFKD** (*compatibility* composition/decomposition): additionally fold *compatibility* variants that
  are not strictly the same character but are compatible. The listing shows NFKC turning the `fi` ligature into
  `fi`, the superscript `²` into `2`, and the fullwidth `Ａ` into `A`. This is a *lossy* fold (it discards
  formatting distinctions) and is the right tool for **search, deduplication, and security checks**, where you
  want `file` and `file` to match, but the *wrong* tool for text you must preserve exactly.

The rule: **NFC for canonical equality and storage** (preserve the text, unify the spellings); **NFKC for
matching and security** (fold compatibility variants so look-alikes collapse), knowing it is lossy. Choose the
axis deliberately: canonical (NFC/NFD) preserves the character's identity; compatibility (NFKC/NFKD) trades
that for aggressive folding.

---

## 58.3 Measurement: normalization is nearly free when it can be

**Methodology.** `code/ch058/bench_normalize.py`. `unicodedata.normalize("NFC", ...)` on text that is already
NFC (an ASCII sentence) versus text that needs recomposition (decomposed accents). `min` per call; ratio
relative to the already-NFC case. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| `normalize("NFC", ...)` | min per call | ratio |
|---|---|---|
| already-NFC (ASCII) | **16 ns** | 1.00x |
| needs recomposition (decomposed) | **4009 ns** | **~244x** |

Normalizing text that is *already* normalized, and ASCII is always NFC, returns in **~16 ns**, because
`normalize` detects the already-normalized case with a fast quick-check and returns without doing the
recomposition work. Text that genuinely needs recomposition costs **~244x** more (~4 us for this 500-character
decomposed string), but even that is microseconds, and it is paid only on the input that actually needs it.

The practical consequence: **normalize user text on the input boundary; do not skip it for fear of cost.** The
common case, ASCII and already-NFC text, is essentially free, and the rare case that needs work is cheap in
absolute terms. Do not bother guarding with `unicodedata.is_normalized` first, `normalize`'s own quick-check
already makes the already-normalized path fast, so the guard adds code without saving time. Normalize at the
edges, where text enters your system (form input, API payloads, file contents), so everything downstream, every
comparison, dict key, dedup, and security check, operates on a single canonical form. The alternative, comparing
un-normalized text, is the silent login/lookup bug of §58.1.

---

## 58.4 Edges and failure modes

**Comparing or keying un-normalized user text.** §58.1. Visually-equal strings can be unequal and hash
differently, so lookups and dedup silently fail. Normalize (NFC) at the boundary before comparing, hashing, or
keying.

**Using NFKC where you must preserve text.** §58.2. NFKC is *lossy*, it folds `²` to `2`, `fi` to `fi`,
fullwidth to ASCII. Never store NFKC-folded text as the canonical copy of user content; use it for a *search
key* alongside the preserved original.

**Normalizing for security incompletely.** Homograph and look-alike attacks (Cyrillic `а` vs Latin `a`,
zero-width characters, confusable scripts) are *not* fully solved by NFKC. Security-sensitive identifier
comparison needs confusable detection and script-mixing checks (`unicodedata` plus policy), not normalization
alone. Normalize *and* apply an identifier profile.

**Assuming normalization makes strings byte-comparable across systems.** NFC is a Unicode canonical form, but a
system that stores NFD (macOS filesystems historically decompose filenames) will disagree with one storing NFC.
Normalize on *both* sides of a comparison to the same form; do not assume the other side matches yours.

**Case and normalization are different axes.** Normalization does not fold case; `"CAFÉ"` and `"café"` are
unequal even after NFC. For caseless comparison use `str.casefold()` (a later Deep D topic), typically *with*
NFC, not instead of it.

**Grapheme clusters remain multi-code-point.** Even after normalization, one user-perceived character (a family
emoji, some scripts) can be several code points. Normalization unifies *spellings*, it does not make `len`
count graphemes. Grapheme handling needs a dedicated library.

---

## 58.5 Connections

**Backward.** The code-point-level `str` and its O(1) indexing are Chapter 56 (PEP 393); normalization operates
on those code points. The `str` equality and hashing that normalization must precede are Chapters 4 and 7. The
`encode`/`decode` that produced the text is Chapters 7 and 57.

**Forward.** Case folding (`str.casefold`) for caseless comparison, and confusable/security handling, are the
next Deep D topics. The hashing that dict keys rely on (why unequal-but-visually-equal strings miss) is Deep P.
The filesystem NFD/NFC disagreement is a Deep R (OS) concern.

**Across books.** Normalization is how Book II makes user text *comparable* before it reaches **Book III**. A
**Book III** retrieval or dedup pipeline normalizes documents and queries to NFC (and uses NFKC for the match
key) at ingest, so "café" the query matches "café" the stored document regardless of how each was typed, and
near-duplicate documents that differ only in encoding collapse. The §58.1 silent-mismatch bug is exactly the
failure that makes a search index miss obvious matches, which **Deep U** designs out at the ingest seam.

---

## 58.6 Exercises

**1. Reproduce the mismatch.** Build the composed and decomposed forms of an accented word from explicit code
points and show they are unequal, differently sized, and differently hashed, and that a dict keyed on one
misses the other. Then normalize both to NFC and show they match.

**2. Compare the forms.** Normalize a string with a ligature and a superscript to NFC and to NFKC, and show NFC
preserves them while NFKC folds them. Explain when each is correct.

**3. Measure the cost.** Run §58.3's benchmark and confirm normalizing already-NFC text is far cheaper than
text needing recomposition. Explain the quick-check fast path and why guarding with `is_normalized` is
pointless.

**4. Normalize at the boundary.** Write a small "user store" that normalizes usernames to NFC on both write and
lookup, and show it now matches across encodings. Explain why normalizing at the edge is better than at every
comparison.

**5. The design question.** Unicode permits multiple encodings of the same visible text, and Python compares by
code point. Argue why normalization is the application's responsibility rather than something `str` does
automatically. Your answer must use the §58.1 bug and §58.3 cost, distinguish NFC (canonical) from NFKC
(compatibility, lossy), and explain why security comparison needs more than normalization.

---

## 58.7 Summary and cross-references

- The same visible text can have **different code points** (composed `é` = U+00E9 vs decomposed `e` + U+0301),
  so `str` `==` and `hash` treat them as different, and lookups/dedup silently fail.
- **`unicodedata.normalize`** maps to a canonical form: **NFC** (composed, for equality/storage/keys), **NFD**
  (decomposed, for processing marks), **NFKC/NFKD** (also fold *compatibility* variants like ligatures and
  fullwidth, *lossy*, for search/security).
- **Measured:** normalizing already-NFC (or ASCII) text is **~16 ns** (a quick-check fast path); text needing
  recomposition is **~244x** more but still microseconds. **Normalize at the input boundary**, it is nearly
  free in the common case; do not guard with `is_normalized`.
- **Edges:** NFKC is lossy (do not store it as canonical); normalization does not fold case or fully solve
  homograph attacks; a grapheme can still be multiple code points.

**Cross-references.** Code points and `str` layout → Chapter 56. Equality and hashing → Chapters 4, 7; Deep P.
Encodings → Chapters 7, 57. Case folding and confusables → the rest of Deep D. Filesystem NFC/NFD → Deep R. The
ingest/dedup seam → Deep U.
