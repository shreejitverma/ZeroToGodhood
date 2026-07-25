# Chapter 57: Encoding Error Handlers

A data pipeline decodes uploaded files as UTF-8 and, to "be robust," uses `errors="ignore"` so a malformed
byte cannot crash it. Months later a security review finds that filenames and content with invalid bytes were
*silently truncated*, `caf\xe9 latte` became `caf latte`, the byte simply vanished, no error, no log, no way
to recover it. The intent was resilience; the effect was silent data loss. The `errors=` handler that decode
and encode take is a real decision with real trade-offs, and the two worst choices, `strict` (crash on any bad
byte) and `ignore` (silently delete it), are the two people reach for first. The right answer for undecodable
bytes is usually **`surrogateescape`**, the only handler that round-trips them *losslessly*: decode, use,
re-encode, and the original bytes come back unchanged. And it is nearly free, on clean data it costs **1.06x**
strict, because the handler only engages when a byte actually fails.

This chapter continues **Deep D** with the encoding error handlers: what each does, why `surrogateescape` is
special (it is why Python can handle filenames with invalid bytes), and why `ignore` is a data-loss bug
wearing a robustness costume.

## Section index

- **57.1** The handlers and their trade-offs
- **57.2** Why `surrogateescape` is special
- **57.3** Measurement: handlers are nearly free on clean data
- **57.4** Edges and failure modes
- **57.5** Connections
- **57.6** Exercises
- **57.7** Summary and cross-references

Listings live under `code/ch057/` and are re-executed by `make verify` on both interpreters.

---

## 57.1 The handlers and their trade-offs

```python
# code/ch057/l01_error_handlers.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- decode: bytes that are not valid UTF-8 ---
  strict           : raises UnicodeDecodeError (the default)
  replace          : 'caf� latte'
  ignore           : 'caf latte'
  backslashreplace : 'caf\\xe9 latte'
  surrogateescape  : 'caf\udce9 latte'
--- surrogateescape round-trips the undecodable bytes losslessly ---
  decode then encode == original : True
  (this is why sys.getfilesystemencoding uses surrogateescape)
--- 'ignore' silently loses data (the dangerous one) ---
  b'caf\xe9 latte'.decode(ignore) : 'caf latte'
  the byte is gone, no error, no way to recover it
--- encode: a character the target codec cannot represent ---
  replace            : b'price: 5?'
  ignore             : b'price: 5'
  backslashreplace   : b'price: 5\\u20ac'
  xmlcharrefreplace  : b'price: 5&#8364;'
```

When a byte cannot be decoded (invalid in the codec) or a character cannot be encoded (not in the target
codec), the `errors=` handler decides the outcome. **`strict`** (the default) raises, fail loudly, which is the
right default because it surfaces the problem instead of hiding it. **`replace`** substitutes a marker (U+FFFD
`�` on decode, `?` on encode), lossy but visible. **`ignore`** deletes the offending byte or character
entirely, lossy *and silent*, the dangerous one. **`backslashreplace`** escapes it as `\xNN`/`\uNNNN`, a
reversible textual form useful for debugging and logging. **`surrogateescape`** stashes each undecodable byte
in a reserved surrogate code point (`\udce9`), which round-trips (below). **`xmlcharrefreplace`** (encode only)
emits an XML/HTML character reference (`&#8364;`), for producing markup.

The key contrast the listing draws: `ignore` on `b"caf\xe9 latte"` yields `"caf latte"`, and the `\xe9` byte is
*gone with no trace*. A pipeline that uses `ignore` for robustness is silently corrupting data. Prefer
`strict` (know about the problem) or `surrogateescape` (preserve the bytes), never `ignore`.

---

## 57.2 Why `surrogateescape` is special

Every other non-strict handler *loses information*: `replace` and `ignore` discard the original bytes,
`backslashreplace` turns them into text that no longer decodes back to the same bytes automatically.
`surrogateescape` is the only one that is **reversible**. It maps each undecodable byte `0xNN` to a lone
surrogate code point in the range U+DC80-U+DCFF, and when you *encode* that string back with `surrogateescape`,
those surrogates turn back into exactly the original bytes. The listing proves it: `raw.decode("utf-8",
"surrogateescape").encode("utf-8", "surrogateescape") == raw` is `True`. The undecodable bytes survived a full
round trip through `str`.

This is not a curiosity, it is why Python can work with real filesystems. A filename on a POSIX system is a
sequence of *bytes*, not guaranteed to be valid UTF-8, but Python's file APIs give you `str`. The reconciliation
is `surrogateescape`: `sys.getfilesystemencoding()` is UTF-8 with the `surrogateescape` error handler (PEP 383),
so a filename with invalid bytes decodes to a `str` you can pass around, and when you use that `str` to open the
file, it re-encodes back to the *exact original bytes*. Without `surrogateescape`, either the invalid filename
would crash (`strict`) or be corrupted (`replace`/`ignore`) and you could not open it. The same handler makes
`os.environ` and command-line arguments robust to non-UTF-8 bytes. `surrogateescape` is the mechanism that lets
Python present a `str` world over a `bytes` reality without losing data at the boundary.

The rule: **use `surrogateescape` when you must accept possibly-invalid bytes, present them as `str`, and later
emit the original bytes, filesystem paths, environment, lenient network/file input. Use `strict` when validity
is required and a bad byte is a real error you want to hear about. Never use `ignore`.**

---

## 57.3 Measurement: handlers are nearly free on clean data

**Methodology.** `code/ch057/bench_handler_cost.py`. Decoding a block of *clean, valid* UTF-8 with `strict`,
`surrogateescape`, and `replace`. `min` per call; ratios relative to `strict`. CPython 3.13.5, Apple M3 Pro,
macOS 27.0, arm64.

| decode clean UTF-8 | min per call | ratio |
|---|---|---|
| `strict` (default) | **154 ns** | 1.00x |
| `surrogateescape` | **163 ns** | **1.06x** |
| `replace` | **161 ns** | 1.05x |

On valid data the non-strict handlers are within **~6%** of `strict`, essentially free. The reason is that the
handler is only *invoked* when a byte actually fails to decode, and clean input never triggers it; the decoder
runs its normal fast path and the handler is dead code on that input. The cost of a handler is paid only on the
*rare malformed byte*, not on every byte.

The practical consequence dissolves a common worry: **you can decode defensively without a speed penalty on the
common case.** Reading filesystem or CLI or lenient network input with `surrogateescape` costs ~6% over strict
*only if measured on a tight decode loop*, and nothing observable in real code, while buying loss-free handling
of the occasional invalid byte. So the choice of handler is a *correctness* decision (what should happen to a
bad byte), not a performance one, choose `strict` or `surrogateescape` based on whether a bad byte is an error
or a thing to preserve, and do not avoid the robust handler for fear of cost.

---

## 57.4 Edges and failure modes

**`errors="ignore"` for robustness.** §57.1. Silent data loss, the byte vanishes with no error. Use `strict`
(hear about it) or `surrogateescape` (preserve it), never `ignore`.

**`surrogateescape` strings leaking into other codecs.** A string containing lone surrogates from
`surrogateescape` can only be re-encoded cleanly with `surrogateescape` again; encoding it `strict` (or writing
it to a UTF-8 file normally) raises `UnicodeEncodeError`. Keep such strings on the byte-boundary round trip;
do not mix them into normal text processing or JSON.

**Assuming the default encoding.** Decoding without specifying the codec uses a platform/locale default. Always
pass the encoding explicitly (Chapter 7); the error handler is a separate axis from the codec.

**`replace` corrupting silently-enough.** `replace` is visible (`�`) but still lossy: the original byte is gone,
replaced by U+FFFD. Fine for display, wrong for data you must preserve. Do not `replace` on the ingest path if
the bytes matter.

**Encoding to a lossy codec.** Encoding text to a narrow codec (Latin-1, ASCII) with `replace`/`ignore` drops
characters the codec cannot hold (`€` becomes `?` or vanishes). If the text must survive, encode to UTF-8, not
to a codec that cannot represent it.

**Surrogates and JSON/logging.** A `surrogateescape` string may not serialize to JSON (which requires valid
Unicode) and can produce odd output in logs. Convert deliberately (e.g. `backslashreplace` for a loggable
form) before crossing into a system that expects clean Unicode.

---

## 57.5 Connections

**Backward.** The `str`/`bytes` boundary and `encode`/`decode` are Chapter 7; this chapter details the `errors=`
axis of that boundary. The in-memory `str` representation the decoded text lands in is Chapter 56 (PEP 393).
The raw `bytes` being decoded are Chapter 37.

**Forward.** Unicode normalization (NFC/NFD) and case folding, needed before *comparing* decoded text, are the
next Deep D chapters. The filesystem encoding (`sys.getfilesystemencoding`, PEP 383/529) and `os.fsencode`/
`os.fsdecode` are the OS-boundary application, connecting to Deep R. Codec internals and custom codecs are a
Deep D topic.

**Across books.** Correct error handling is how Book II ingests messy real-world text for **Book III** without
silently corrupting it. A **Book III** ingest pipeline decodes documents with `surrogateescape` (or `strict`
with explicit quarantine of failures), never `ignore`, so a document with a few invalid bytes is preserved or
flagged, not silently truncated, before it reaches embedding or indexing. The §57.1 `ignore` bug is exactly the
kind of silent corruption that poisons a corpus, which **Deep U** guards against at the ingest seam.

---

## 57.6 Exercises

**1. Compare the handlers.** Decode an invalid-UTF-8 byte string with each handler and show the different
results. Explain which are lossy, which are reversible, and which is silent.

**2. Prove the round trip.** Decode invalid bytes with `surrogateescape`, re-encode with `surrogateescape`, and
confirm you recover the original bytes exactly. Then re-encode `strict` and observe it fails. Explain why
`surrogateescape` must be used on both ends.

**3. Expose the `ignore` bug.** Build a small "robust" decoder with `errors="ignore"` and feed it data with
invalid bytes; show the data is silently shortened. Explain why this is worse than crashing.

**4. Measure the cost.** Run §57.3's benchmark and confirm the non-strict handlers are within a few percent of
strict on clean data. Explain why the handler is nearly free when there are no errors.

**5. The design question.** Python offers a spectrum of error handlers from crash-loud (`strict`) to
silent-lossy (`ignore`) to lossless-reversible (`surrogateescape`). Argue which should be the default for
ingesting untrusted external text. Your answer must use the §57.3 measurement (cost is not the deciding
factor), explain why `surrogateescape` enables the filesystem `str` API, and say why `ignore` is almost never
correct.

---

## 57.7 Summary and cross-references

- The **`errors=` handler** decides the fate of a byte/character that does not fit: `strict` (raise, default),
  `replace` (marker, lossy-visible), `ignore` (delete, **lossy-silent, avoid**), `backslashreplace` (escape),
  `surrogateescape` (**lossless round trip**), `xmlcharrefreplace` (encode-only, XML refs).
- **`surrogateescape` is the only reversible handler:** it round-trips undecodable bytes exactly, which is why
  Python's **filesystem/`os.environ`/CLI** decoding uses it (PEP 383). Use it to present possibly-invalid bytes
  as `str` and emit the original bytes.
- **Measured:** on clean data the non-strict handlers cost **~1.06x** strict, essentially free, because the
  handler only runs on an actual bad byte. The choice is about **correctness, not speed**.
- **Never `ignore`** (silent data loss); keep `surrogateescape` strings on their byte round trip (they do not
  re-encode cleanly to other codecs or JSON).

**Cross-references.** `str`/`bytes` and `encode`/`decode` → Chapter 7. `str` representation → Chapter 56.
`bytes` → Chapter 37. Normalization and case folding → the rest of Deep D. Filesystem encoding → Deep R. The
ingest seam → Deep U.
