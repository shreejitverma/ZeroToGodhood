# Chapter 62: Bulk Character Translation

A text-cleaning routine strips punctuation the obvious way, `for p in ",.!?;:": s = s.replace(p, "")`, and it
works, but it does six full passes over the string and allocates six intermediate copies to remove one class of
character. `str.translate` does the same job in **one** pass driven by a lookup table, and it is **2.3x** faster
here, a gap that *grows* with the number of characters being mapped or deleted, because chained `replace` pays
one pass per character while `translate` pays one pass total. For mapping or deleting many characters at once,
`translate` is the tool the obvious code should have used.

This chapter closes **Deep D** with `str.translate` and `str.maketrans`, the table-driven, single-pass way to
transform text character by character, and the rule for when it beats chained `replace`. It is the string-
transformation counterpart to the earlier Deep D chapters on representation and encoding: those were about how
text is *stored*; this is about transforming it efficiently.

## Section index

- **62.1** `maketrans` and `translate`
- **62.2** One pass vs N passes
- **62.3** Measurement: translate vs chained replace
- **62.4** Edges and failure modes
- **62.5** Connections
- **62.6** Exercises
- **62.7** Summary and cross-references

Listings live under `code/ch062/` and are re-executed by `make verify` on both interpreters.

---

## 62.1 `maketrans` and `translate`

```python
# code/ch062/l01_translate.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- maketrans + translate: map characters in one pass ---
  'education'.translate  : 'EdUcAtIOn'
--- delete characters: map them to None (third maketrans arg) ---
  strip punctuation      : 'abcde'
--- map some, delete others, in the SAME table ---
  'a-b_c@d'.translate    : 'a b cd'
--- equivalence with chained replace (translate does it in one pass) ---
  chained replace result : 'hello world a test'
  translate result       : 'hello world a test'
  identical              : True
```

`str.translate(table)` walks the string once and maps each character through `table`, a mapping from code point
to a replacement (another code point, a string, or `None` to delete). `str.maketrans` builds the table in three
forms. **Two-string form** `maketrans("aeiou", "AEIOU")` maps each character in the first to the character at the
same position in the second (the listing uppercases vowels). **Three-argument form** `maketrans("", "", ",.!?;:")`
adds a set of characters to *delete* (mapped to `None`), the standard "strip these characters" idiom.
**Dict form** `maketrans({"-": " ", "_": " ", "@": None})` gives full control, mapping some characters to
strings and others to deletion in one table (`a-b_c@d` becomes `a b cd`).

The last block shows the equivalence: chaining `replace` for each punctuation character and a single `translate`
with a deletion table produce the *identical* result. They are two ways to write the same transformation, and
§62.3 measures why one is faster.

---

## 62.2 One pass vs N passes

The performance difference is structural. **Chained `replace`** runs `s.replace(p, "")` once per character `p`,
and each call scans the *entire* string looking for `p` and builds a *new* string with `p` removed. Removing K
kinds of character means K full scans and K allocations, and because strings are immutable (Chapter 7), each
intermediate result is thrown away after the next `replace` consumes it. The cost is O(K x n) time and K
allocations.

**`translate`** builds the table once (O(K), tiny) and then makes a *single* pass over the string, looking up
each character in the table and emitting its replacement, one scan, one allocation, regardless of how many
characters the table maps. The cost is O(n) time and one allocation. So the two approaches diverge as K grows:
for one or two characters they are close, but for a large character set (strip all punctuation, map a whole
alphabet, sanitize a wide range) `translate`'s single pass wins by a factor that tracks K.

The rule: **use `translate` for per-character mapping or deletion of a set of characters; use `replace` for a
specific substring.** The two are not interchangeable in *kind*, `translate` operates on single characters (it
cannot replace the multi-character substring `"foo"`), and `replace` operates on substrings. But whenever the
task is "map/delete these characters," which is a character-set operation, `translate` is both the clearer
expression (one table) and the faster execution (one pass).

---

## 62.3 Measurement: translate vs chained replace

**Methodology.** `code/ch062/bench_translate.py`. Removing six punctuation characters from a ~5,400-character
string via chained `str.replace` (six passes) versus one `str.translate` with a deletion table. `min` per call;
ratio relative to `translate`. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| remove 6 punctuation chars | min per call | ratio |
|---|---|---|
| `translate` (1 pass) | **5497 ns** | 1.00x |
| chained `replace` (6 passes) | **12,745 ns** | **2.3x** |

`translate` does the job in **5.5 us** with a single pass; chained `replace` takes **12.7 us**, **2.3x** more,
doing six scans and six allocations for the six characters. The ratio is not fixed, it grows with the number of
characters removed: strip a dozen characters and the gap widens, because `replace`'s cost scales with the
character-set size while `translate`'s does not. Even here, at six characters, the single-pass approach is more
than twice as fast.

The rule: **reach for `str.translate` with `str.maketrans` whenever you map or delete a set of characters**, text
cleaning (strip punctuation, control characters), transliteration (map one alphabet to another), sanitization
(delete or replace a class of characters). Reserve `str.replace` for replacing a *specific substring* (where
`translate` does not apply). Writing `translate` is also clearer, the intent ("this table of character mappings")
is in one place, versus a loop of `replace` calls whose order can even matter. As throughout the book, the
idiomatic tool is both the faster and the more readable one.

---

## 62.4 Edges and failure modes

**Chained `replace` for a character set.** §62.3. K passes and K allocations. Use `translate` (one pass) for
per-character mapping or deletion.

**Using `translate` for a multi-character substring.** `translate` maps *single characters*; it cannot replace
`"foo"` with `"bar"` (that is `replace`'s job). Pick `translate` for character-level, `replace`/`re.sub` for
substring-level.

**`replace` order dependence.** Chained `replace` can interact: replacing `"a"` then `"b"` can behave differently
from the reverse if an earlier replacement introduces characters a later one matches. `translate` has no such
hazard (all mappings apply in one simultaneous pass), which is a *correctness* advantage on top of the speed one.

**Building the table repeatedly.** `str.maketrans` builds the table; doing it inside a hot loop rebuilds it every
iteration. Build the table once (module level or before the loop) and reuse it, the table is the reusable part.

**`bytes.translate` differs.** `bytes` has its own `translate` (a 256-entry byte table via `bytes.maketrans`,
with an optional delete argument), not the same API as `str.translate`. Use the right one for the type
(Chapter 37 for bytes).

**Deleting vs mapping to empty string.** In `str.translate`, map a character to `None` to delete it (not to `""`).
The dict form accepts `None`; the three-argument `maketrans` handles the delete set. Mapping to `""` in a dict
also works, but `None` is the canonical "delete."

---

## 62.5 Connections

**Backward.** String immutability, why each `replace` allocates a new string, is Chapter 7 (which measured the
`+=` O(n^2) trap, the same allocation cost in another guise). The `str` and its code points that `translate`
walks are Chapter 56. The character classes you often strip (control characters, punctuation categories) relate
to the `unicodedata` of Chapter 58.

**Forward.** Regular expressions (`re.sub`) for pattern-based (not character-set) replacement are a Deep D/text-
processing topic, the tool when the transformation is a *pattern*, not a character set. `bytes.translate` for
binary data is Chapter 37's territory. Large-scale text cleaning pipelines are Deep U.

**Across books.** Efficient character transformation is how Book II cleans and normalizes text cheaply before it
reaches **Book III**. A **Book III** ingest pipeline that strips control characters, normalizes whitespace, or
transliterates does it with a single `translate` table per pass rather than chained `replace`, so per-document
cleaning stays O(n) as the corpus grows. The §62.3 one-pass property is what keeps the cleaning stage from
dominating ingest. **Deep U** owns the text-cleaning seam.

---

## 62.6 Exercises

**1. Reproduce the speedup.** Run §62.3's benchmark and confirm `translate` beats chained `replace` for removing
a character set. Then increase the number of characters removed and show the gap widens. Explain why.

**2. Use all three table forms.** Build translation tables with the two-string form, the three-argument (delete)
form, and the dict form, and apply each. Explain what each form expresses.

**3. Catch an order bug.** Construct a chained-`replace` sequence where the order of replacements changes the
result, then do the same mapping with `translate` and show it is order-independent. Explain why `translate` is
safer.

**4. Pick the right tool.** Take a task that needs a multi-character substring replacement and show `translate`
cannot do it (only `replace`/`re.sub` can), and a task that needs character-set deletion and show `translate` is
the right tool. Explain the character-vs-substring distinction.

**5. The design question.** Python provides both `replace` (substring) and `translate` (character table). Argue
why both exist rather than one. Your answer must use the §62.3 measurement, explain the one-pass-vs-N-passes
difference and the order-independence advantage, and characterize which transformations belong to each.

---

## 62.7 Summary and cross-references

- **`str.translate(table)`** maps each character through a table in a **single pass**; **`str.maketrans`** builds
  the table in three forms: two-string (map), three-argument (map + delete set), and dict (full control,
  including `None` to delete).
- **Chained `str.replace`** for a character set does **one pass and one allocation per character** (O(K x n)),
  while `translate` does **one pass total** (O(n)); the gap grows with the character-set size.
- **Measured:** removing six punctuation characters is **2.3x** faster with `translate` than chained `replace`
  (5.5 us vs 12.7 us), and the ratio widens with more characters. `translate` is also order-independent (safer).
- **Use `translate` for per-character mapping/deletion; use `replace`/`re.sub` for substrings.** Build the table
  once and reuse it.

**Cross-references.** String immutability and the `+=` trap → Chapter 7. `str` code points → Chapter 56.
`unicodedata` character classes → Chapter 58. `bytes.translate` → Chapter 37. Regex substitution → Deep D. The
text-cleaning seam → Deep U.
