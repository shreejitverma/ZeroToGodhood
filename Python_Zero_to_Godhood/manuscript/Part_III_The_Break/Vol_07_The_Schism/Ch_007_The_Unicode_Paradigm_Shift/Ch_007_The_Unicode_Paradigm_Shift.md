# Chapter 7: The Unicode Paradigm Shift and Text vs. Bytes (Python 3.0)

A service passes every test. Its test data is names like `Smith` and `Jones`, and it ships. Three
weeks later it crashes on a user named `José`, in production, deep inside a logging call that has
nothing to do with the name, with a `UnicodeDecodeError` pointing at a line that looks correct. The
bug was there from the first commit; it just needed a byte above 127 to fire, and the test suite never
supplied one.

This failure mode, correct-looking code that fails at a distance on real-world data, is the exact
thing Python 3.0 was built to make impossible, and it is why Python 3 broke compatibility with Python
2 on purpose. In Python 2, one type (`str`) was both a byte string and an ASCII text string, and the
interpreter silently decoded between them, so the `José` bug could hide anywhere a byte string met a
text string. Python 3 made `str` a sequence of Unicode code points and `bytes` a sequence of octets,
with no implicit conversion, which turns that distant, production-only crash into an immediate, local
`TypeError` at the exact line where text and bytes were mixed.

This chapter covers that split and the cluster of 3.0 changes that followed from taking correctness
seriously: the coercion ban, PEP 393's memory-efficient strings, encoding and its error handlers,
`print` as a function, true division, and the lazy iterators and views. It reaches to Python 3.3 for
PEP 393, because the memory story is not complete without it.

## Section index

- **7.1** The text/bytes split and the coercion ban (PEP 3112)
- **7.2** `bytes` and `bytearray`: the binary types
- **7.3** Unicode internals: from narrow/wide builds to PEP 393
- **7.4** Encoding, decoding, and `surrogateescape` (PEP 383)
- **7.5** `print()` as a function (PEP 3105) and division unification (PEP 238)
- **7.6** Lazy iterators, dictionary views, and `memoryview`
- **7.7** Measurement: the string-concatenation folklore, corrected
- **7.8** Edges and failure modes
- **7.9** Connections
- **7.10** Exercises
- **7.11** Summary and cross-references

Listings live under `code/ch007/` and are re-executed by `make verify` on both interpreters.

---

## 7.1 The text/bytes split and the coercion ban (PEP 3112)

**Why this exists.** In Python 2, `"café"` was a byte string whose meaning depended on the source
encoding, and `u"café"` was text; mixing them implicitly decoded the bytes with ASCII and raised
`UnicodeDecodeError` the moment a byte exceeded 127, far from the cause. Python 3 removes the
ambiguity: `str` is text (code points), `bytes` is binary (octets), and the two never implicitly
convert.

```python
# code/ch007/l01_text_bytes_split.py
try:
    b"data" + "string"
except TypeError as exc:
    print("  b'data' + 'string' ->", type(exc).__name__ + ":", exc)
```

Verified output (CPython 3.13.5):

```text
--- implicit text/bytes mixing is a local TypeError, not a distant one ---
  b'data' + 'string' -> TypeError: can't concat str to bytes
--- str is a sequence of code points, not code units ---
  len('grinning face emoji') : 1 (one code point)
  Java would report length 2 (two UTF-16 code units)
--- the encoding is not part of the str; it exists only in bytes ---
  text (str)          : 'café' len 4
  text.encode('utf-8'): b'caf\xc3\xa9' len 5
  text.encode('latin1'): b'caf\xe9' len 4
```

The error is local: it names the line where `bytes` met `str`, not a line three modules away where
the value is finally used. (The message reads "can't concat str to bytes": the `str` operand cannot be
concatenated onto the `bytes` left operand.)

**The senior-engineer contrast.** A C `char*` is bytes; "text" is a convention layered on top. A Java
`String` is text but internally UTF-16, so a `char` is a 16-bit code *unit*, and a code point above
U+FFFF spans two of them, which is why `"😀".length() == 2` in Java. Python 3's `str` is a sequence of
*code points*: `len` of a single emoji is `1`, indexing returns whole code points, and, as the last
three lines show, **the encoding is not part of the object**. `"café"` has `len` 4 regardless of how
you later encode it; only the `bytes` from `encode()` carry an encoding, and their length depends on
it (5 in UTF-8, 4 in Latin-1). You decode bytes into text at input, work in `str`, and encode back to
bytes at output. This "Unicode sandwich" is the discipline the whole language is built to enforce.

---

## 7.2 `bytes` and `bytearray`: the binary types

`bytes` is the immutable octet sequence; `bytearray` is its mutable sibling. Both support the buffer
protocol (**Deep A**), letting C code and `memoryview` access their storage without copying.

```c
/* Illustrative; Include/bytesobject.h - immutable, storage inline with the object. */
typedef struct {
    PyObject_VAR_HEAD
    Py_hash_t ob_shash;     /* cached hash; -1 if uncomputed (bytes are hashable) */
    char ob_sval[1];        /* the octets, allocated inline, NUL-terminated for C interop */
} PyBytesObject;
```

```c
/* Illustrative; Include/bytearrayobject.h - mutable, storage via a separate buffer. */
typedef struct {
    PyObject_VAR_HEAD
    Py_ssize_t ob_alloc;    /* capacity of the buffer */
    char *ob_bytes;         /* start of the allocation */
    char *ob_start;         /* start of the logical data (>= ob_bytes) */
    Py_ssize_t ob_exports;  /* count of active buffer exports (e.g. memoryviews) */
} PyByteArrayObject;
```

Two design details earn their keep. The split between `ob_bytes` and `ob_start` makes a left-end
deletion (`del ba[0]`) *O(1)*: just advance `ob_start` rather than shift the whole buffer. And
`ob_exports` is a safety interlock: while a `memoryview` is live (`ob_exports > 0`), any operation
that would reallocate the buffer raises `BufferError`, so a view can never end up pointing at freed
memory. `bytearray` grows with the same amortized-*O*(1) overallocation policy as `list` (**Deep Q**).

---

## 7.3 Unicode internals: from narrow/wide builds to PEP 393

**The original problem.** Through Python 3.2, a CPython build stored *every* string in one fixed width
chosen at compile time: a narrow build used 2-byte `Py_UNICODE`, a wide build used 4-byte. Narrow
builds mishandled astral characters (above U+FFFF) as surrogate pairs, breaking `len()` and indexing;
wide builds made `"hello"` cost 20 bytes of payload. Neither was acceptable.

**PEP 393 (Python 3.3): flexible string representation.** CPython now picks the narrowest storage that
fits the string's largest code point, per string, at creation: three kinds, 1 byte (Latin-1 range,
with a pure-ASCII fast path), 2 bytes (BMP), or 4 bytes (full Unicode). The C structs behind the kinds
are `PyASCIIObject` and `PyCompactUnicodeObject`, whose full layout is **Deep D**; you can watch the
kind change with the data:

```python
# code/ch007/l02_pep393.py
import sys
for label, s in cases:
    print(f"  {label:24} len={len(s)} getsizeof={sys.getsizeof(s)}")
```

Verified output (CPython 3.13.5):

```text
--- one non-ASCII code point promotes the whole string to a wider kind ---
  ASCII      'hello'       len=5 getsizeof=46
  Latin-1    'hn~'         len=2 getsizeof=59
  BMP/UCS-2  'h+CJK'       len=2 getsizeof=62
  Astral/UCS-4 'h+emoji'   len=2 getsizeof=68
  empty str                len=0 getsizeof=41
```

(The labels are transliterated to ASCII so the transcript stays portable; the actual strings contain a
Latin-1 `ñ`, a CJK character, and an emoji.) Read the numbers: pure ASCII is cheapest, a compact
header plus 1 byte per character plus a NUL. A single non-ASCII code point promotes the *whole* string
to a wider kind with a larger header, which is why `"hñ"` at two characters is *larger* than `"hello"`
at five. The guarantees that matter: **`len()` and indexing are always *O*(1) and always in code
points**, so there are no surrogate-pair surprises, and ASCII text stays as cheap as a byte string.
The trap: one emoji in a megabyte of ASCII promotes the entire megabyte to 4 bytes per character, a
real consideration for large text buffers. These sizes are identical on 3.13.5 and 3.14.6; both are
recorded.

---

## 7.4 Encoding, decoding, and `surrogateescape` (PEP 383)

`str.encode(encoding)` turns code points into `bytes`; `bytes.decode(encoding)` turns octets back into
a `str`. Both take an error handler governing malformed data: `strict` (the default, raise), `ignore`
(drop), `replace` (insert U+FFFD or `?`), `backslashreplace` (escape), and `surrogateescape`.

**`surrogateescape` (PEP 383)** is the one worth understanding, because it is how Python survives the
Unix filesystem. POSIX paths are arbitrary byte sequences, not guaranteed valid UTF-8. To let such
bytes round-trip through `str` losslessly, each undecodable byte `b` maps to a lone surrogate code
point `U+DC00 + b` on decode, and back to `b` on encode:

```python
# code/ch007/l03_surrogateescape.py
raw = b"bad_\xff_path.txt"
decoded = raw.decode("utf-8", "surrogateescape")
reencoded = decoded.encode("utf-8", "surrogateescape")
```

Verified output (CPython 3.13.5):

```text
--- an undecodable byte survives a round trip through str ---
  original bytes     : b'bad_\xff_path.txt'
  round-trips exactly: True
  0xFF became lone surrogate U+DCFF: True
--- strict would have raised instead ---
  strict decode -> UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 4: invalid
```

The `0xff` byte, invalid in UTF-8 and fatal to the default `strict` handler, becomes `U+DCFF` under
`surrogateescape` and reappears as `0xff` on re-encode. This is exactly how `os.fsencode`/`os.fsdecode`
and `sys.argv` handle filenames. **The discipline:** always pass `encoding=` explicitly to `open()`,
`encode`, `decode`, and subprocess boundaries. Relying on the locale default is the cause of "works on
my machine, `UnicodeDecodeError` in the container."

> **Verified forward-looking note.** Python 3.15 makes UTF-8 the default text encoding via **PEP 686
> (Make UTF-8 mode default)**, which is Final and scheduled for that release; `PYTHONUTF8=0` will opt
> back out. Until 3.15 is your floor, be explicit. Source: PEP 686, peps.python.org.

---

## 7.5 `print()` as a function (PEP 3105) and division unification (PEP 238)

Two smaller 3.0 changes remove silent traps. Python 2's `print` was a *statement* compiled to
dedicated opcodes, its behavior fixed at compile time. Python 3 made it an ordinary builtin function,
resolved by normal name lookup and therefore overridable, composable, and keyword-configurable
(`sep`, `end`, `file`, `flush`). Because it is a function, `print(*items, sep=", ", file=sys.stderr,
flush=True)` works, and `builtins.print` can be replaced for a logging shim.

Division was the other trap. In Python 2, `/` was floor division for two integers but true division if
either operand was a float, so `5/2 == 2` but `5.0/2 == 2.5`, a silent precision hazard. Python 3 (PEP
238) split them: `/` is always true division (returns `float`), `//` is floor division.

```python
# code/ch007/l05_division.py
```

Verified output (CPython 3.13.5):

```text
--- the clean split ---
  7 / 2   = 3.5   (true division, always a float)
  7 // 2  = 3   (floor division)
--- the portability hazard: floor vs truncate for negatives ---
  -7 // 2 = -4   Python floors toward -inf
  int(-7 / 2) = -3   C/Java/Go truncate toward zero
  -7 % 2  = 1   Python: sign follows the DIVISOR
     (C would give -1 here: sign follows the dividend)
```

**The senior-engineer contrast, and a real portability hazard.** C, C++, Java, and Go integer division
*truncates toward zero*: `-7 / 2 == -3`. Python's `//` *floors toward negative infinity*: `-7 // 2 ==
-4`. Likewise `%` follows the divisor's sign in Python (`-7 % 2 == 1`) but the dividend's in C. Porting
modular-arithmetic code between the two without accounting for this produces off-by-one bugs that pass
every positive-number test. When you need truncation in Python, use `int(a / b)` or `math.trunc`.

---

## 7.6 Lazy iterators, dictionary views, and `memoryview`

Python 3 made the sequence-producing builtins lazy: `range`, `zip`, `map`, and `filter` return
iterators or views instead of materializing lists, and `dict.keys`/`values`/`items` return live views.

```python
# code/ch007/l04_lazy_and_views.py
r = range(0, 10_000_000, 3)
```

Verified output (CPython 3.13.5):

```text
--- range is O(1) memory with O(1) indexing and membership ---
  getsizeof(range(0,10M,3)): 48 bytes | len: 3333334
  9_999_999 in r          : True
  r[1_000_000]            : 3000000
  getsizeof(list of 1000) : 8056 bytes
--- dict views are live: they track the dict, they do not snapshot ---
  view after inserting 'c': ['a', 'b', 'c']
--- memoryview slices and edits a buffer with zero copy ---
  slice          : b'payload'
  edit visible in original: b'system_Payload_data'
```

A `range` over ten million values costs 48 bytes, because it stores only `start`/`stop`/`step` and
computes `start + i*step` on demand; the equivalent list of just one thousand ints already costs 8 KB,
plus the int objects behind it. Dict views are *live*: `ks` reflected the `"c"` insertion that happened
after it was created, because it is a window onto the dict, not a snapshot. And `memoryview` extends
the laziness to binary data: `sub` is a slice of `data`'s buffer with no copy, so writing `sub[0]`
edits the original `bytearray` in place. That zero-copy capability is foundational for high-performance
I/O and the boundary to C/C++; the buffer protocol and `memoryview` mechanics are **Deep A**, and the
seam is **Deep M**.

---

## 7.7 Measurement: the string-concatenation folklore, corrected

Every intermediate guide teaches that building a string with `+=` in a loop is *O*(n²), because each
`+=` builds a new immutable string, and that you must use `"".join`. The claim is the kind this book
tests rather than repeats, and it turns out to be right for the wrong reason.

**Methodology.** `code/ch007/bench_string_concat.py`, through `_harness/bench.py`. Build an n-character
string three ways: `+=` on an unaliased name, `"".join`, and `s = s + "x"` where a second name aliases
`s` each iteration. Measured at n = 10,000 and n = 40,000 so the *asymptotics* are visible, not just a
ratio. `min` is the headline; within one interpreter; CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| case | n=10,000 vs join | n=40,000 vs join | scaling (10k to 40k) |
|---|---|---|---|
| unaliased `+=` | 1.56x | 1.64x | ~4x (linear) |
| `"".join` | 1.00x | 1.00x | ~4x (linear) |
| aliased `s = s + x` | 4.4x | **13.3x** | **~12x (quadratic)** |

The work quadruples from 10k to 40k. A linear algorithm's time quadruples with it; a quadratic one's
grows about sixteenfold. **Unaliased `+=` scales linearly**, staying a small constant (about 1.6x)
behind `join`. It is *not* quadratic, because CPython contains an optimization: when the string being
extended has no other reference (refcount 1), `+=` resizes its buffer *in place* rather than allocating
a new string. So the common accumulation pattern `s += x` is *O*(n).

**The aliased case is the real *O*(n²)**, and you can see it in the last column: its cost relative to
`join` *triples* from 4.4x to 13.3x as n quadruples. The moment a second name references `s`, the
in-place resize would corrupt that alias, so CPython cannot do it and must allocate a fresh string each
iteration, giving the quadratic behavior the folklore describes.

The honest conclusion is more useful than the slogan: **use `"".join`, not because `+=` is always
quadratic (it usually is not), but because `join` stays linear unconditionally, while `+=` relies on a
fragile refcount condition that a stray alias, a debugger, or a logging call holding a reference can
silently break.** Correctness advice that happens to also be robust beats performance folklore that is
half true.

---

## 7.8 Edges and failure modes

**Omitting `encoding=`.** §7.4. The top source of cross-platform `UnicodeDecodeError`. Always be
explicit; use `surrogateescape` for filesystem paths. This is the chapter's opening `José` bug.

**Confusing `str` and `bytes` at API boundaries.** Sockets, files in binary mode, and hashing all speak
`bytes`; decode and encode at the edge, not in the middle. The coercion ban (§7.1) turns a mid-code mix
into an immediate `TypeError`, which is the feature working.

**Assuming C division semantics.** §7.5. `//` floors toward negative infinity and `%` follows the
divisor's sign, unlike C. Off-by-one bugs that pass every positive-number test.

**`str +=` with a lurking alias.** §7.7. The in-place optimization silently breaks if anything else
references the string, turning *O*(n) into *O*(n²). Use `join` for accumulation and do not rely on the
optimization.

**One emoji promoting a huge buffer.** §7.3. A single astral code point makes the whole string 4
bytes per character. For very large text buffers with rare non-BMP characters, this is a real memory
cost.

**Materializing lazy iterators needlessly.** `list(range(n))` or `list(d.keys())` "to use it twice."
Iterate directly; reach for a list only when you need indexing or multiple passes.

---

## 7.9 Connections

**Backward.** The layered I/O stack whose `TextIOWrapper` applies the codec of this chapter is Chapter
6, and the `open(..., encoding=)` discipline lives at that boundary. The buffer protocol that `bytes`,
`bytearray`, and `memoryview` implement builds on the `PyObject`/`PyVarObject` layout of Chapter 19.

**Forward.** Stdlib consolidation and UTF-8 mode are Chapter 8, the next chapter. Iterators and
generators in depth are Chapter 9. The buffer protocol, `memoryview`, and zero-copy numerics are
**Deep A**; the full codecs reference and the `PyASCIIObject`/`PyCompactUnicodeObject` layout are
**Deep D** and **Deep P**. Container internals (`bytearray` growth) are **Deep Q**.

**Across books.** The Unicode sandwich and the buffer protocol are the two halves of how Python meets
**Book I**. Text crosses the boundary as `bytes` with an explicit encoding, never as an ambiguous
string; binary data crosses zero-copy through `memoryview` over a shared buffer, never copied per
element. The order-book example ingests its market-data feed as raw `bytes` viewed through a
`memoryview` and handed to a C++ parser, decoding to `str` only for the human-facing symbol names.
**Deep M** owns that boundary; this chapter provides both of its data disciplines.

---

## 7.10 Exercises

**1. Reproduce the `José` bug.** Write a small function that concatenates a byte string read from a
"file" (a `bytes` literal) with a `str`, in the Python 2 style. Show that it works for ASCII input and
raises for a non-ASCII byte. Then fix it the Python 3 way and state exactly where in the code the
decode belongs.

**2. Watch the kind promote.** Using `sys.getsizeof`, find the per-character byte cost of a long string
in each of the three PEP 393 kinds by measuring two lengths and taking the difference (so the header is
cancelled out). Confirm 1, 2, and 4 bytes per character. Then predict the size of a 1000-character
string that is all ASCII except one emoji, and check it.

**3. Break the round trip.** `surrogateescape` round-trips arbitrary bytes through `str`. Find a
sequence of bytes and an operation on the decoded `str` (not just re-encoding it unchanged) that
*cannot* survive the round trip, and explain why. What does this tell you about treating
`surrogateescape` strings as ordinary text?

**4. Find the alias that kills the optimization.** Take the §7.7 benchmark's unaliased `+=` loop and
add exactly one line that turns it from *O*(n) into *O*(n²), without changing the `+=` itself. Measure
to confirm, then explain in terms of the refcount condition. This is the failure mode from §7.8 made
concrete.

**5. The design question.** Python 3 broke compatibility with millions of lines of Python 2 code to
fix the text/bytes ambiguity, and the migration took roughly a decade (Chapter 6 of the timeline
covers the 2.7 tail). Argue whether the break was worth it. Your answer must weigh the `José` bug class
against the migration cost, and address whether a language could have reached the same correctness
guarantee *without* a compatibility break, using `from __future__` as evidence for or against.

---

## 7.11 Summary and cross-references

- `str` is **code points**, `bytes`/`bytearray` are **octets**, and there is **no implicit
  conversion** (PEP 3112); a mix is an immediate, local `TypeError`, not the distant production crash
  it was in Python 2. Decode at input, work in `str`, encode at output.
- **PEP 393** stores each string in the narrowest of three widths from its largest code point, giving
  correct *O*(1) indexing *and* compact memory; the sizes are stable across 3.13 and 3.14.
- **`surrogateescape`** (PEP 383) round-trips arbitrary bytes through `str`; always specify the
  encoding. **PEP 686** makes UTF-8 the default in 3.15 (verified Final).
- `print` is a **function** (PEP 3105); `/` is **true division** and `//` **floors toward negative
  infinity** (PEP 238), unlike C truncation.
- `range`/`zip`/`map`/`filter` are **lazy**, dict `keys`/`values`/`items` are **live views**, and
  `memoryview` shares buffers **zero-copy**.
- **Measured:** unaliased `s += x` is *O*(n) (about 1.6x `join`) thanks to CPython's in-place resize;
  it becomes true *O*(n²) the moment a second reference exists. Use `join` for robustness, not because
  `+=` is always quadratic.

**Cross-references.** The text/binary I/O stack and `TextIOWrapper` → Chapter 6. Stdlib consolidation
and UTF-8 mode → Chapter 8. Iterators and generators → Chapter 9. The buffer protocol and `memoryview`
→ Deep A; the full codecs and string-layout reference → Deep D and Deep P; container growth → Deep Q.
The C/C++ boundary → Deep M.
