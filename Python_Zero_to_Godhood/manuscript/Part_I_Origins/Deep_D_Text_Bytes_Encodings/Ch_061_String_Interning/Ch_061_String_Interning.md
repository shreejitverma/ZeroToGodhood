# Chapter 61: String Interning

A service parses a million JSON records, each with the field name `"user_id"`, and holds them in memory. The
field name is the *same seven characters* a million times, but because each was built by the JSON parser at
runtime, it is a million *separate* string objects, seven million characters of storage for one distinct value.
Interning fixes this: `sys.intern` stores a single canonical copy so all million references share *one* object.
Measured, 200,000 runtime-built copies of `"user_id"` cost **11.2 MB** as distinct objects but **1.6 MB** when
interned, a **6.9x** reduction, because the interned list holds 200,000 *pointers* to one string instead of
200,000 strings.

The folklore about interning emphasizes a *speed* benefit (interned strings compare by identity), and that is
real but modest on modern CPython, whose `==` already fast-paths length and `memcmp`. The durable win is
**memory**: deduplicating repeated string values. This chapter continues **Deep D** with string interning, when
CPython interns automatically, how `sys.intern` forces it, and the memory-versus-uniqueness judgment of when to
use it.

## Section index

- **61.1** Automatic and manual interning
- **61.2** The real benefit is memory, not speed
- **61.3** Measurement: deduplicating repeated strings
- **61.4** Edges and failure modes
- **61.5** Connections
- **61.6** Exercises
- **61.7** Summary and cross-references

Listings live under `code/ch061/` and are re-executed by `make verify` on both interpreters.

---

## 61.1 Automatic and manual interning

```python
# code/ch061/l01_interning.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- identifier-like literals are auto-interned at compile time ---
  two 'user_id' literals share an object : True
--- strings built at runtime are NOT auto-interned ---
  equal?                                 : True
  same object (is)?                      : False
--- sys.intern forces sharing ---
  after sys.intern, same object          : True
  interned equals the literal            : True
--- why it matters: many copies collapse to one ---
  a list of N equal runtime strings holds N objects;
  interning makes them share ONE (the benchmark measures the saving)
```

CPython interns some strings *automatically*. String **literals that look like identifiers** (letters, digits,
underscores, the shape of a variable name or dict key) are interned at compile time, so two `"user_id"` literals
in the source are the *same object* (`a is b` is `True`). This is why dict lookups on literal keys are fast and
why `a is b` sometimes surprises people by being `True` for strings, it is an optimization, not a guarantee.

Strings **built at runtime** are *not* auto-interned. The `x` and `y` built by `"".join([...])` are equal
(`x == y` is `True`) but *different objects* (`x is y` is `False`), because the interpreter has no way to know
at build time that they duplicate an existing string. `sys.intern` forces it: `sys.intern(build(...))` returns
the canonical copy, so two interned builds are the same object (`xi is yi` is `True`) and equal to the interned
literal. The rule of thumb this establishes: **never rely on `is` for string equality** (it is `True` only for
interned or identical strings, an implementation detail), and **use `sys.intern` deliberately** when you want
runtime strings deduplicated.

---

## 61.2 The real benefit is memory, not speed

Interning has two potential payoffs, and the book's measurement discipline separates the real one from the
folklore.

The **speed** claim is that interned strings compare by identity: `a is b` is a pointer comparison, O(1),
whereas `a == b` must compare content. This was a meaningful win on older interpreters. On modern CPython it is
small, because `str.__eq__` already has fast paths: it checks identity first (so equal *interned* strings short-
circuit anyway), then length (unequal lengths return immediately), then a `memcmp` of the bytes (which is SIMD-
fast). So comparing two equal 1000-character strings is only marginally slower than an `is`, and for the *equal*
case interning barely helps because `==` would take the identity fast path too. Interning for comparison speed
is optimizing something already cheap.

The **memory** benefit is the durable one. When the same string *value* appears many times, each non-interned
occurrence is a separate object with its own header and character buffer (~50 bytes for a short string, Chapters
4 and 56). Interning collapses all occurrences to *one* object; the many references become many *pointers* (8
bytes each) to that single string. For data with a small set of values repeated a large number of times, parsed
field names, categorical columns, enum-like tokens, repeated identifiers, the saving is large, exactly what
§61.3 measures. **Interning is a deduplication tool.** Reach for it when you hold many copies of few distinct
strings; do not reach for it to speed up comparisons.

---

## 61.3 Measurement: deduplicating repeated strings

**Methodology.** `code/ch061/bench_intern_memory.py`. Held memory of a list of 200,000 runtime-built copies of
`"user_id"` as distinct objects versus interned (shared), via `tracemalloc` (deterministic). CPython 3.13.5,
Apple M3 Pro, macOS 27.0, arm64.

| 200,000 copies of `"user_id"` | held memory |
|---|---|
| distinct equal strings | **11,224,000 bytes** |
| interned (shared) | **1,624,048 bytes** |
| ratio | **6.9x** |

The distinct-strings list holds 200,000 separate string objects (~50 bytes each) plus the list's pointers, 11.2
MB. The interned list holds *one* string object plus 200,000 pointers to it, 1.6 MB, dominated by the pointer
array (200,000 x 8 bytes ≈ 1.6 MB). The **6.9x** saving is the 200,000 redundant string objects that interning
eliminated. This is deterministic (`tracemalloc` is exact) and identical on both interpreters.

The rule: **intern high-repetition, low-cardinality strings; leave unique or short-lived ones alone.** The ideal
target is a value from a *small set* that appears *many times*, field/column names, category labels, repeated
tokens, symbol tables, where interning turns N objects into one. The wrong target is *unique* strings (interning
them adds bookkeeping and saves nothing, since there are no duplicates to collapse) or *short-lived* ones
(interned strings live in a table and are not easily released, so interning transient data is a slow leak,
§61.4). As always, match the tool to the data shape: interning pays exactly when the same few values recur at
scale.

---

## 61.4 Edges and failure modes

**Relying on `is` for string equality.** §61.1. `a is b` is `True` only for interned or identical strings, an
implementation detail. Always use `==` to compare string *values*; reserve `is` for genuine identity (e.g.
sentinel objects).

**Interning unique strings.** §61.3. Interning strings that are all distinct adds table bookkeeping and saves no
memory (nothing to dedup). Intern only values that actually repeat.

**Interning short-lived strings (a slow leak).** Interned strings are held by the interpreter's intern table. In
CPython the table holds them, and interning a stream of transient strings grows that table without bound.
Intern long-lived, repeated values (keys, categories), never a firehose of one-off strings.

**Assuming all literals are interned.** Only *identifier-shaped* literals are auto-interned; a literal with
spaces or punctuation (`"user id"`) is generally not. Do not assume `a is b` for arbitrary string literals; it
is guaranteed only by `sys.intern`.

**Interning is not compression.** Interning deduplicates *identical* strings; it does nothing for strings that
are merely *similar*. For near-duplicate or compressible text, use actual compression, not interning.

**Cross-interpreter/subprocess assumptions.** Interning is per-interpreter; a string interned in one process (or
subinterpreter, Chapter 23) is a different object in another. Do not rely on interning identity across process
or interpreter boundaries.

---

## 61.5 Connections

**Backward.** The string object and its ~50-byte header that interning deduplicates are Chapters 4, 56 (PEP
393), and Deep A. The `==` fast path (identity, length, `memcmp`) that makes the speed benefit modest is the
string-comparison internals of Chapter 7. The identity-versus-equality distinction (`is` vs `==`) is Chapter 4.

**Forward.** The dict/hashing machinery that benefits from interned keys (identity short-circuit on lookup) is
Deep P. The intern table itself and small-string caching are a Deep A internals topic. Categorical/dictionary
encoding at scale (the columnar-data generalization of interning) is Deep T/Deep U.

**Across books.** Interning is how Book II holds repeated string values cheaply on the way to **Book III**. A
**Book III** ingest or feature pipeline that parses millions of records interns the small set of recurring field
names, category labels, and tokens, so the resident set holds one object per distinct value rather than one per
occurrence, the §61.3 6.9x applied to a real corpus. The columnar systems Book III builds on generalize this to
*dictionary encoding* (store distinct values once, reference them by index). **Deep U** owns the repeated-value
seam; **Deep T** owns the columnar generalization.

---

## 61.6 Exercises

**1. Observe auto-interning.** Show that two identifier-like string literals share an object but two runtime-
built equal strings do not, and that `sys.intern` makes the runtime ones share. Explain when CPython interns
automatically.

**2. Reproduce the memory saving.** Run §61.3's benchmark and confirm interning many copies of one value cuts
memory several-fold. Explain what the interned list actually holds versus the distinct-strings list.

**3. Test the speed claim.** Compare `==` on two equal long non-interned strings with `is` on two interned ones.
Show the difference is small, and explain the `==` fast path that makes it so.

**4. Cause a slow leak.** Intern a large number of *unique* strings and observe memory grow without the dedup
benefit (and reason about why the intern table retains them). Explain why interning transient/unique strings is
harmful.

**5. The design question.** CPython auto-interns some strings and offers `sys.intern` for the rest, and the main
benefit is memory, not speed. Argue when a program should intern explicitly. Your answer must use the §61.3
measurement, explain why the comparison speedup is modest on modern CPython, and characterize the string
populations (repeated/long-lived vs unique/transient) for which interning is right or wrong.

---

## 61.7 Summary and cross-references

- **Interning** stores one canonical copy of a string so equal copies share an object. CPython **auto-interns
  identifier-shaped literals** at compile time; **runtime-built strings are not** auto-interned; **`sys.intern`**
  forces it.
- **Never use `is` for string equality** (`True` only for interned/identical strings, an implementation detail);
  use `==`.
- **The durable benefit is memory, not speed.** The comparison speedup is modest on modern CPython (`==` fast-
  paths identity, length, `memcmp`); the win is **deduplication**.
- **Measured:** 200,000 copies of `"user_id"` cost **11.2 MB** distinct vs **1.6 MB** interned, a **6.9x**
  saving. **Intern repeated, long-lived, low-cardinality strings** (keys, categories); never unique or transient
  ones (a slow leak).

**Cross-references.** String object and header → Chapters 4, 56; Deep A. `==` internals and `is` vs `==` →
Chapters 7, 4. Hashing and dict keys → Deep P. Dictionary/columnar encoding → Deep T, Deep U. The repeated-value
seam → Deep U.
