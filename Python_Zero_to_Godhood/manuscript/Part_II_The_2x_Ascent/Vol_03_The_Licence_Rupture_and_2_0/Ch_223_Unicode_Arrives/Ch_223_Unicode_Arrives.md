# Chapter 13: Unicode Arrives

Chapter 1 named ABC's first fatal flaw as "no way to talk to the outside world", and Python's fix, real file I/O, made it usable. But there was a deeper version of that flaw hiding inside the string type, and it took Python a decade to fully resolve. **Python 2.0 (2000) added a separate `unicode` type** alongside `str` (which was bytes), and that addition was the first move in the longest, most deliberate correction in Python's history: the untangling of **bytes** (what a file or socket carries) from **text** (a sequence of characters).

Python 2's model, two types that converted between each other *implicitly*, was a half-fix. It gave you `unicode` for text and `str` for bytes, but it silently converted between them by guessing an encoding (ASCII), and it guessed wrong the moment any non-ASCII character appeared, producing the infamous `UnicodeDecodeError` that plagued Python 2 code for years. Python 3.0 (2008) completed the fix: `str` became text, `bytes` became bytes, and *no implicit conversion* remained, every crossing must name its encoding. This release chapter shows the modern, correct model, the one 2.0 began reaching for, on the verification interpreters. **Deep D owns the mechanism** (encodings, code points, normalisation); this chapter owns the release that started the journey and the arc from 1989's flaw to 2008's fix.

## Section index

- **13.1** The constraint: bytes and text are different, and conflating them is a bug
- **13.2** The modern model: str is text, bytes is bytes
- **13.3** encode/decode: the only bridge, and it is explicit
- **13.4** Why implicit conversion was the mistake
- **13.5** One character, several byte-representations
- **13.6** Edges: the journey's remaining subtleties
- **13.7** Connections
- **13.8** Exercises
- **13.9** Summary and cross-references

Listings live under `code/ch223/` and are re-executed by `make verify` on the verification interpreters.

---

## 13.1 The constraint: bytes and text are different

A file holds *bytes*, octets, numbers 0-255. A string, to a human, is *text*, a sequence of characters: `café`, `naïve`, an emoji. These are not the same thing, and the relationship between them is an *encoding*: a rule for turning characters into bytes (encode) and bytes back into characters (decode). UTF-8 encodes `é` as two bytes; Latin-1 encodes it as one; ASCII cannot encode it at all. The character exists independent of any encoding; the bytes exist only under one.

Early Python, like most languages of its era, conflated them: a `str` was bytes, and "the characters" were whatever those bytes meant under the machine's assumed encoding (usually ASCII, sometimes the locale's). This worked as long as text was ASCII, which in 1990 it often was. But the world is not ASCII, and a language that assumes text is bytes breaks on the first accented name, the first non-Latin script, the first emoji. The constraint 2.0 began to answer is that **text and bytes are genuinely different types of thing**, and a correct language must distinguish them, provide a bridge between them (encode/decode), and never guess which is which.

---

## 13.2 The modern model: str is text, bytes is bytes

```python
# code/ch223/l01_unicode_arrives.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- the modern model: str is TEXT, bytes is BYTES, and they differ ---
  str (text)  : 'café' - 4 code points
  bytes (data): b'caf\xc3\xa9' - 5 bytes
  they are different types : True
  a string is a sequence of CHARACTERS (code points); bytes is a
  sequence of OCTETS. one character can be several bytes (utf-8),
  which is exactly the distinction 2.0's unicode type introduced
```

**`str` and `bytes` are different types, and `café` shows why the distinction matters.**
The text `café` is 4 *code points* (c, a, f, é); its UTF-8 encoding is 5 *bytes* (é becomes two bytes, `\xc3\xa9`). The string is a sequence of characters; the bytes are a sequence of octets; and one character can be several bytes. These are different types (`str` and `bytes`), and Python 3 keeps them rigorously separate, you cannot mix them (`"a" + b"b"` raises), you cannot index one expecting the other's units, and you must *convert* explicitly to cross between them. This is the model Python 2.0's `unicode` type began reaching for and Python 3.0 completed, and it is correct: text and bytes are different, so they are different types.

**The 4-vs-5 mismatch is the whole point, made concrete.**
`len(text)` is 4 (characters); `len(data)` is 5 (bytes); they differ because `é` is one character but two UTF-8 bytes. Code that assumes `len(string) == len(bytes)`, the ASCII-era assumption, is wrong for any non-ASCII text, and the bug is silent until the input is French, or German, or emoji. Keeping `str` and `bytes` as distinct types with distinct lengths makes the mismatch *visible*: you cannot accidentally treat characters as bytes, because they are different types with different `len`. Deep D owns the full mechanism (why é is two bytes in UTF-8, one in Latin-1, how normalisation affects the count); this chapter's point is the release-level one, that 2.0 introduced the distinction the model rests on.

---

## 13.3 encode/decode: the only bridge, and it is explicit

```text
--- encode/decode is the ONLY bridge, and it is explicit ---
  text.encode('utf-8')  : b'caf\xc3\xa9'  (text -> bytes)
  data.decode('utf-8')  : 'café'  (bytes -> text)
  round trip is exact   : True
  the encoding is NAMED at every crossing - Python 3's rule. 2.0
  had the two types but converted between them IMPLICITLY, which
  guessed an encoding and guessed wrong (the UnicodeDecodeError era)
```

**Crossing between text and bytes requires naming an encoding, every time, explicitly.**
`text.encode('utf-8')` turns text into bytes; `data.decode('utf-8')` turns bytes into text; and the round trip is exact *because the same encoding was named on both sides*. This is Python 3's rule and the correction Python 2 needed: the encoding is named at *every* crossing, so there is no guessing. Python 2 had the two types but converted between them *implicitly*, if you mixed `str` and `unicode`, it silently decoded the `str` using ASCII to make them compatible, and that implicit decode is what exploded on non-ASCII. Python 3 removed the implicit path entirely: to go from text to bytes or back, you *must* call `encode`/`decode` with an encoding, and forgetting is a `TypeError` (you cannot mix the types), not a silent wrong guess.

**Explicitness at the boundary is "errors should never pass silently" (Chapter 3) applied to encoding.**
The Python 2 implicit conversion was *convenient*, it let ASCII code mix `str` and `unicode` freely, and *wrong*, it made non-ASCII code fail unpredictably. Python 3's explicit encode/decode is *less convenient* (you must name the encoding) and *correct* (no guessing, no surprise). This is the values (Chapter 3) choosing correctness over convenience at the text/bytes boundary, the same trade as `1/0` raising instead of returning a default, and it is why Python 3 text handling, once you accept that crossings are explicit, simply works where Python 2's guessing failed.

---

## 13.4 Why implicit conversion was the mistake

```text
--- why implicit conversion was the mistake ---
  'naïve' as latin-1 bytes : b'na\xefve'
  decoding as utf-8 raises : UnicodeDecodeError
  decoding as latin-1 works: 'naïve'
  the SAME bytes mean different text under different encodings, so
  there is no 'the' encoding to guess. Python 2 guessed (ascii) and
  exploded on any non-ascii; Python 3 REFUSES to guess - you name it
```

**The same bytes mean different text under different encodings, so there is no "the" encoding to guess, which is why implicit conversion had to go.**
`naïve` encoded as Latin-1 is `b'na\xefve'`; decoding those *same bytes* as UTF-8 raises `UnicodeDecodeError` (they are not valid UTF-8), while decoding them as Latin-1 gives back `'naïve'`. The bytes are identical; the text they represent depends *entirely* on the encoding you choose. There is no way to look at bytes and know "the" encoding, because there is no such thing, the encoding is external information the bytes do not carry. Python 2's implicit conversion *had* to guess an encoding (it chose ASCII), and since the guess was fixed and the world's encodings are not, it was wrong for most non-ASCII data. Python 3 *refuses to guess*: you name the encoding, because only you (or the protocol, the file's metadata, the HTTP header) know it.

**This is the deepest lesson of the whole text/bytes journey.**
"Bytes do not carry their encoding" is why the distinction between text and bytes is not pedantry but necessity: bytes are meaningless without an encoding, text is meaningful independent of one, and a language that treats them as the same type *must* assume an encoding, which *must* be wrong sometimes. Python 2's decade of `UnicodeDecodeError` was the cost of that assumption; Python 3's explicit model is the fix, and the fix is not "handle unicode better" but "stop pretending bytes and text are the same thing". The 2.0 `unicode` type was the first admission that they are different; the 3.0 model is the full commitment to it.

---

## 13.5 One character, several byte-representations

```text
--- one character, several representations ---
  A (ascii)    : 1 char, 1 utf-8 bytes (41)
  e-acute      : 1 char, 2 utf-8 bytes (c3a9)
  emoji        : 1 char, 4 utf-8 bytes (f09f9880)
```

**A character is one code point; its byte length depends on the encoding, and conflating the two is the ASCII-era bug.**
`A` is 1 UTF-8 byte; `é` is 2; an emoji is 4. All are single characters (one code point each), but their UTF-8 encodings range from 1 to 4 bytes. Code that assumes "one character is one byte", the ASCII assumption, is correct only for the ASCII subset (`A`) and wrong for everything else. Truncating a string to "100 bytes" can split a multi-byte character (producing invalid bytes); computing "string width" from byte count over-counts; indexing bytes expecting characters lands mid-character. These are all the char-equals-byte assumption failing, and the `str`/`bytes` distinction exists precisely to make the assumption *impossible* to hold accidentally, characters are `str` (code points), bytes are `bytes` (octets), and you cannot confuse their units because they are different types.

**Deep D owns the full complexity; this chapter owns the release-level takeaway.**
The full story, why UTF-8 uses 1-4 bytes, how code points relate to grapheme clusters, why `len` can disagree with visible character count under normalisation (Chapter 223's `café` combining-vs-precomposed subtlety), is Deep D's subject. The release-level takeaway is simpler and sufficient here: 2.0 introduced the character-vs-byte distinction, 3.0 made it inescapable, and the modern model where a character is a code point (in `str`) and a byte is an octet (in `bytes`) is what a correct text-handling language requires. The timeline reached it slowly, a flaw named in 1989, a half-fix in 2000, the full fix in 2008, because getting text right is genuinely hard and worth the deliberation.

---

## 13.6 Edges: the journey's remaining subtleties

**The default encoding is UTF-8, but assuming it is a bug at the boundary.**
Python 3 defaults to UTF-8 in most contexts (source files, `open` in text mode on most platforms), so much code "just works". But the default is a *default*, not a guarantee, a file written in Latin-1, an HTTP response in Shift-JIS, a Windows console in cp1252, all require naming the actual encoding. Relying on the UTF-8 default for data whose encoding you do not control reintroduces Python 2's guessing bug in a smaller form, and the boundary discipline (Chapter 130, Deep D) is to name the encoding from the data's metadata, not assume it.

**`len` is code points, not grapheme clusters.**
`len("café")` is 4 code points, but if the é is a combining sequence (e + combining acute), it is *5* code points for one visible character (this is the subtlety the listing's precomposed form avoids). "Visible characters" are grapheme clusters, which can be multiple code points, so even `str` length is not "number of characters a human sees". Deep D owns normalisation (NFC/NFD) and grapheme handling; the edge here is that the `str`/`bytes` distinction fixes char-vs-byte but not code-point-vs-grapheme, a further layer of the same "text is complicated" truth.

**Mixing `str` and `bytes` is a `TypeError`, which is the fix working.**
`"a" + b"b"` raises `TypeError` in Python 3 (it silently worked, wrongly, in Python 2). This is not a limitation but the model enforcing itself: you cannot accidentally mix text and bytes, so the entire class of Python 2 implicit-conversion bugs is *impossible*. Code ported from Python 2 hits these `TypeError`s exactly where it was relying on implicit conversion, and each is a latent bug the new model surfaces, the migration pain of 2-to-3 was largely this, and it was the model doing its job.

**And the network and files are always bytes.**
Sockets (Chapter 106) and binary files carry bytes; text is a *decode* away, always. The boundary between a program's text world and the byte world of I/O is where encode/decode lives, and getting it wrong (decoding with the wrong encoding, or forgetting to decode) is the most common text bug. Deep D and Chapter 40 (file I/O) own the boundary; the release-level point is that 2.0/3.0 made the boundary *explicit*, so the encode/decode is a visible operation you can get right, not an implicit guess you cannot.

---

## 13.7 Connections

**Backward.**
ABC's I/O flaw that this deepens is Chapter 1; the "errors should never pass silently" value that motivates explicit encode/decode is Chapter 3; the object model where `str` and `bytes` are distinct types is Chapter 4.

**Forward.**
The full mechanism, encodings, code points, normalisation, the flexible string representation, is Deep D (Chapters 56-62); the 3.0 completion of the fix is Part III (the Break); file I/O and the text/bytes boundary are Chapter 40 (Deep R); binary-to-text codecs (base64) are Chapter 120; sockets carrying bytes are Chapter 106.

**Across books.**
Text/bytes is a universal problem, **Book I**'s C++ has `std::string` (bytes) and `std::u32string`/`std::wstring` (wider units) with the same distinction, and its networking code decodes at the boundary exactly as Python's does. The shared trading system carries symbols and messages as text and ships them as bytes over sockets, naming the encoding at the boundary (Chapter 106, Deep V), the text/bytes discipline this chapter's release began, applied in the capstone.

---

## 13.8 Exercises

**1. Prove bytes carry no encoding.** Encode the same string in UTF-8 and Latin-1; show the byte sequences differ, then decode each with the *wrong* encoding and observe error-or-garbage. Conclude why guessing is impossible.

**2. Measure char vs byte.** For ASCII, accented, CJK, and emoji strings, compare `len(s)` (code points) with `len(s.encode('utf-8'))` (bytes); tabulate the ratio and explain the ASCII-era assumption's failure.

**3. Reproduce the truncation bug.** Truncate a multi-byte-character string to a byte count that splits a character; show the resulting invalid bytes; fix by truncating code points instead. This is a real production bug class.

**4. Port a Python 2 mix.** Write code that mixes `str` and `bytes` (Python 2 style); show the `TypeError` in Python 3; fix it by explicit encode/decode. Explain what latent bug the `TypeError` surfaced.

**5. The design question.** Python took a decade to fix text/bytes (2.0 half-fix, 3.0 full fix) and the full fix was the most painful part of the 2-to-3 transition. Argue whether the deliberation was worth it, versus a faster, more disruptive fix, and whether a new language should get text/bytes right from day one (as Rust and Go did) at the cost of early complexity, using Python's slow, painful path as the counter-example.

---

## 13.9 Summary and cross-references

- **Python 2.0 (2000) added the `unicode` type**, the first move in a decade-long correction of the deepest form of ABC's I/O flaw (Chapter 1): the confusion between **bytes** (what I/O carries) and **text** (a sequence of characters).
- **The modern (Python 3) model keeps `str` (text, code points) and `bytes` (octets) as distinct types** with no implicit conversion: `café` is 4 code points and 5 UTF-8 bytes, and the mismatch is *visible* because they are different types with different `len`.
- **encode/decode is the only bridge, and it names the encoding every time**: Python 2 converted implicitly (guessing ASCII, the `UnicodeDecodeError` era), Python 3 refuses to guess, because the *same bytes mean different text under different encodings*, so there is no "the" encoding, only the one you name.
- **A character is a code point; its byte length depends on the encoding** (1 for ASCII, 2 for é, 4 for emoji in UTF-8), and the `str`/`bytes` distinction makes the char-equals-byte assumption impossible to hold accidentally.
- **The arc is the timeline at its most deliberate**: a flaw named in 1989, half-fixed in 2000, fully fixed in 2008, because getting text right is genuinely hard, and Deep D owns the mechanism this release began.

**Cross-references.** ABC's I/O flaw → Chapter 1. The loud-errors value → Chapter 3. The object model → Chapter 4. Encodings, code points, normalisation → Deep D. The 3.0 completion → Part III. File I/O → Chapter 40. Codecs → Chapter 120. Sockets → Chapter 106. The capstone's text/bytes boundary → Deep V.
