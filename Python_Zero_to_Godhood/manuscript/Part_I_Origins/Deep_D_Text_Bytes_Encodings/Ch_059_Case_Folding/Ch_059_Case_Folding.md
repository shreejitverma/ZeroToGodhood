# Chapter 59: Case Folding

A German user registers the username "Straße" and the system stores `"straße".lower()` as the canonical key.
Later they try to log in typing "STRASSE" (many keyboards and habits render the sharp-s as "ss"), the system
computes `"STRASSE".lower()`, which is `"strasse"`, and it does not match `"straße"`, login fails on a name
that is, by the language's own rules, the same. `str.lower()` is the wrong tool for the job: it maps characters
to lowercase for *display*, and it leaves the German ß as ß. The right tool is `str.casefold()`, which applies
Unicode's *caseless-matching* fold: it maps ß to "ss", so `"straße".casefold()` and `"STRASSE".casefold()` are
both `"strasse"` and they match. And casefold is not slower, it costs the **same** as `lower()` on typical
text, so there is no reason to use the weaker tool for comparison.

This chapter continues **Deep D** with case folding: why `lower()` is for display and `casefold()` is for
comparison, the cases where they diverge, and the robust caseless-equality recipe (normalize, then casefold).
It pairs directly with Chapter 58, normalization unifies *spellings*, case folding unifies *case*, and correct
caseless matching needs both.

## Section index

- **59.1** `lower` for display, `casefold` for comparison
- **59.2** Where they diverge, and the robust recipe
- **59.3** Measurement: casefold is not slower
- **59.4** Edges and failure modes
- **59.5** Connections
- **59.6** Exercises
- **59.7** Summary and cross-references

Listings live under `code/ch059/` and are re-executed by `make verify` on both interpreters.

---

## 59.1 `lower` for display, `casefold` for comparison

```python
# code/ch059/l01_casefold.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- casefold folds more than lower ---
  'Straße'     lower='straße'     casefold='strasse'
  'ΣΊΣΥΦΟΣ'    lower='σίσυφος'    casefold='σίσυφοσ'
  'Σ'          lower='σ'          casefold='σ'
--- the German sharp-s case ---
  'ß'.lower()          : 'ß'  (unchanged)
  'ß'.casefold()       : 'ss'  (folds to 'ss')
--- caseless equality: lower fails, casefold works ---
  a.lower() == b.lower()       : False
  a.casefold() == b.casefold() : True
--- Greek final sigma: lower keeps it, casefold folds it ---
  'ΟΔΟΣ'.lower()       : 'οδος'  (final sigma form ς)
  'ΟΔΟΣ'.casefold()    : 'οδοσ'  (plain sigma σ)
--- the robust recipe: normalize + casefold ---
  caseless_equal('Straße','STRASSE') : True
```

`str.lower()` produces a lowercased string suitable for *showing to a user*: `"Straße"` becomes `"straße"`,
preserving the ß because ß *is* the lowercase form (its uppercase is "SS", but lowercasing does not go the
other way). `str.casefold()` produces a string suitable for *caseless comparison*: it applies the Unicode case-
folding algorithm, which is deliberately more aggressive, `ß` folds to `ss`, so that a word written with ß and
the same word written with "ss" compare equal.

The `caseless equality` block is the payoff: `"straße".lower() == "STRASSE".lower()` is `False` (straße vs
strasse), but `"straße".casefold() == "STRASSE".casefold()` is `True` (both strasse). If you compare user text
case-insensitively with `.lower()`, you get exactly the login bug; with `.casefold()`, you get the correct
answer.

---

## 59.2 Where they diverge, and the robust recipe

`lower` and `casefold` agree on the vast majority of text (all ASCII, most accented Latin), and diverge on the
cases where a single character's caseless-equivalent is *not* simply its lowercase:

- **German ß** (U+00DF): `lower` leaves it ß; `casefold` folds it to `ss`. This is the headline case, because
  ß has no distinct uppercase (it uppercases to "SS"), so only folding to "ss" makes the round trip match.
- **Greek final sigma**: the listing's `"ΟΔΟΣ"` lowercases to `"οδος"` (with the *final* sigma form `ς`,
  positionally correct for display), but casefolds to `"οδοσ"` (plain `σ`), because for *matching* the final-
  versus-medial distinction must be erased, `"οδος"` and `"οδοσ"` are the same word. `lower` preserves the
  display distinction; `casefold` removes it for comparison.
- Various other characters (certain ligatures, some Cherokee and Georgian letters) fold differently for
  matching than they lowercase for display.

The general principle: **`lower` optimizes for a correct-looking lowercase string; `casefold` optimizes for
"two strings that are the same word compare equal."** They are different goals, and comparison needs the
second.

Case and normalization are *independent* axes, so robust caseless matching needs both. The listing's
`caseless_equal` shows the recipe: **normalize (NFC, Chapter 58), then casefold.** Normalization unifies the
composed/decomposed spellings of accents (so `é` in either encoding matches); casefolding unifies case (so ß
matches ss). Skipping either leaves a gap: casefold alone still fails on a decomposed accent, and normalize
alone still fails on ß-versus-ss. The order is normalize-then-casefold (or casefold-then-normalize; for most
text either works, but a canonical pipeline picks one and applies it everywhere).

---

## 59.3 Measurement: casefold is not slower

**Methodology.** `code/ch059/bench_casefold.py`. `str.lower()` versus `str.casefold()` on a block of typical
(ASCII) text. `min` per call; ratio relative to `lower`. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| operation | min per call | ratio |
|---|---|---|
| `str.lower()` | **278 ns** | 1.00x |
| `str.casefold()` | **278 ns** | **1.00x** |

The two are **the same speed**. `casefold` consults a slightly larger fold table for the handful of characters
that fold specially, but for typical text the cost is indistinguishable from `lower`. There is therefore *no
performance argument* for using `lower` in place of `casefold` when the goal is comparison.

The rule: **use `casefold` for any caseless operation, comparison, search, dedup, dictionary keys, and use
`lower` only when you specifically want a lowercase string to display.** Since casefold is free relative to
lower and strictly more correct for matching, the only reason to reach for `lower` is presentation. Pair
`casefold` with NFC normalization at the input boundary (Chapter 58) and every downstream caseless comparison
becomes a plain `==` on already-folded, already-normalized text. Choosing `lower` "because it is the obvious
one" is the source of the ß login bug; the correct default for comparison is `casefold`.

---

## 59.4 Edges and failure modes

**Using `lower` for caseless comparison.** §59.1. It misses ß/ss, final sigma, and other fold-only cases, so
strings that are the same word compare unequal. Use `casefold` for comparison.

**Casefold without normalization.** §59.2. `casefold` folds case but not composed/decomposed spelling, so a
decomposed accent still fails to match. Normalize (NFC) *and* casefold for robust caseless equality.

**Casefold is not reversible or display-safe.** `casefold` can produce strings that are not valid display text
(ß to ss changes the word's appearance, final sigma to medial looks wrong mid-word). Never show casefolded
text to users or store it as the canonical copy, keep it as a *comparison key* beside the preserved original.

**The Turkish dotted/dotless I.** In Turkish, uppercase `I` lowercases to dotless `ı` and `İ` to dotted `i`,
which differs from the default (locale-independent) behavior of `lower`/`casefold`. Neither method is locale-
aware; for Turkish-correct casing you need explicit handling. Do not assume `lower`/`casefold` are correct for
every locale's casing rules.

**Casefold does not solve security matching.** Like normalization (Chapter 58), casefolding does not defend
against confusables (Cyrillic look-alikes, mixed scripts). Identifier security needs confusable detection on
top of normalize-plus-casefold.

**Comparing case-insensitively byte-by-byte.** Do not lowercase *bytes* (`b"...".lower()` only touches ASCII).
Decode to `str` first (Chapters 7, 57), then casefold; caseless matching is a `str` operation.

---

## 59.5 Connections

**Backward.** Normalization, the other half of the caseless-equality recipe, is Chapter 58. The `str` and its
code points are Chapter 56. The `encode`/`decode` that produces the text to fold is Chapters 7 and 57. The
`str` equality and hashing that folded text feeds are Chapters 4 and 7.

**Forward.** Confusable and security-identifier handling (beyond normalize+casefold) is a Deep D/Deep O
security topic. The hashing that caseless dict keys rely on is Deep P. Locale-aware collation (sorting text per
language rules, `locale`/`PyICU`) is a distinct, harder problem flagged in Deep D.

**Across books.** Caseless matching is how Book II makes user-facing lookups forgiving before they reach
**Book III**. A **Book III** retrieval or entity-matching pipeline folds queries and keys with normalize-plus-
casefold, so "Straße", "strasse", and "STRASSE" all resolve to one entity, and a case- or ß-variant of a query
still hits the index. The §59.1 bug, using `lower` for comparison, is exactly the silent miss that makes search
feel broken, which **Deep U** designs out at the matching seam.

---

## 59.6 Exercises

**1. Reproduce the ß bug.** Compare "straße" and "STRASSE" with `.lower()` and with `.casefold()`, and show
`lower` fails while `casefold` succeeds. Explain why ß needs folding, not lowercasing, to match "ss".

**2. Find the divergences.** For several strings (German, Greek, ligatures), print `lower` and `casefold` side
by side and identify where they differ. Explain the display-vs-matching distinction in each case.

**3. Build the robust recipe.** Write `caseless_equal` that normalizes (NFC) then casefolds, and show it
matches across both a decomposed accent and a ß/ss difference, where casefold-alone or normalize-alone fails.
Explain why both steps are needed.

**4. Measure the cost.** Run §59.3's benchmark and confirm `casefold` and `lower` are the same speed. Explain
why there is no performance reason to prefer `lower` for comparison.

**5. The design question.** Python provides both `lower` (display) and `casefold` (matching) rather than one
case operation. Argue why. Your answer must use the §59.1 divergence and §59.3 measurement, explain why
casefolded text is unsafe to display or store as canonical, and why caseless equality also requires
normalization.

---

## 59.7 Summary and cross-references

- **`str.lower()`** produces lowercase for **display**; **`str.casefold()`** applies Unicode caseless folding
  for **comparison**, and folds more aggressively (ß to ss, Greek final sigma to sigma).
- Using `lower` for caseless comparison **silently fails** on those cases (the ß login bug). Use `casefold` for
  comparison, search, dedup, and keys.
- **The robust recipe is normalize (NFC, Chapter 58) then casefold**, case and spelling are independent axes,
  and correct caseless equality needs both.
- **Measured:** `casefold` costs the **same** as `lower` (278 ns each), so there is no performance reason to use
  the weaker tool for matching.
- **Edges:** casefolded text is not display-safe or canonical (keep it as a key beside the original); neither
  method is locale-aware (Turkish I) or a security-confusable defense.

**Cross-references.** Normalization → Chapter 58. `str` code points → Chapter 56. Encodings → Chapters 7, 57.
Equality and hashing → Chapters 4, 7; Deep P. Confusable/security matching → Deep D, Deep O. The matching seam →
Deep U.
