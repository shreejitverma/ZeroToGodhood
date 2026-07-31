# Chapter 252: The Flexible String

## The constraint

Before Python 3.3, how a `str` stored its characters depended on how *CPython itself had been compiled*.
There were two builds, and every Python installation was one or the other.

A **narrow** build stored each character in 2 bytes (UTF-16).
It was compact, but 2 bytes cannot hold a code point above U+FFFF, so characters in the astral planes - emoji, rare scripts, many symbols - had to be represented as *surrogate pairs*: two units standing for one character.
That broke the fundamentals.
On a narrow build, `len("😀")` returned `2`, indexing landed between the halves of a character, and slicing could cut a character in two.
Text handling was subtly, silently wrong for exactly the characters users increasingly used.

A **wide** build stored each character in 4 bytes.
It was correct - every code point fit, `len` and indexing worked - but wasteful: an all-ASCII string, which is the overwhelmingly common case, paid four bytes per character to store values that fit in one.

So you had to choose, at build time, between correct-but-wasteful and compact-but-broken.
The constraint Python 3.3 (2012, PEP 393) answered: **remove the choice - make each string adapt its storage width to its own contents, so it is correct for all text and compact for the common case.**

This is a two-track chapter.
The text model itself - what a code point is, the relationship between `str` and `bytes`, encodings and how text becomes bytes on the wire - is the whole subject of Deep Volume D, the actual centerpiece of the Python 3 break.
What this chapter owns is the release: the day the internal representation of `str` became flexible, ending the narrow/wide split.

## What shipped

Under PEP 393, a `str` stores 1, 2, or 4 bytes per character, chosen by its *largest* code point: pure ASCII/Latin-1 (up to U+00FF) uses 1 byte, Basic-Multilingual-Plane text (up to U+FFFF) uses 2, and only text containing astral characters (above U+FFFF) uses 4.
Listing 252.1 measures this, using a size *delta* so the numbers are build-independent, on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- str storage adapts to the widest character (1, 2, or 4 bytes) ---
  ASCII  ('a')     bytes/char : 1
  BMP    (CJK)     bytes/char : 2
  astral (emoji)   bytes/char : 4
  the width is set by the LARGEST code point in the string: 1 byte
  for ASCII, 2 for Basic-Multilingual-Plane, 4 for astral. the
  common case (ASCII/Latin text) pays the least - the point of PEP 393
--- one astral character upgrades the WHOLE string's width ---
  len(plain)      : 100   size heavier? : True
  len(with_emoji) : 100   (still 100 code points)
  adding one emoji forces every character to 4 bytes, because the
  buffer is uniform-width. so the size jumps even though only one
  character changed - width is a property of the whole string
--- correctness: len and indexing count CODE POINTS, not units ---
  len('😀') : 1   (ONE code point, not two)
  'a<emoji>b'[2] : 'b'   (indexing lands on 'b' correctly)
  on the old NARROW build an astral char counted as 2 units, so
  len() and indexing were wrong for emoji. PEP 393 stores whole code
  points, so counting and indexing are correct for ALL text
--- the two old builds, and why the choice is gone ---
  narrow build: 2 bytes/char, BROKE on astral chars (surrogate bugs)
  wide build  : 4 bytes/char always, correct but 4x on ASCII
  PEP 393     : per-string width - correct like wide, compact like
  narrow for the common case. there is no longer a narrow/wide flag
--- the constraint answered ---
  pre-3.3 you chose narrow (compact but buggy on astral text) or wide
  (correct but wasteful). PEP 393 made a string pick its width from
  its largest code point: ASCII pays 1 byte, BMP 2, astral 4, and
  len/indexing are always correct. str became both correct AND
  memory-adaptive - the everyday case the cheapest
```

## Why each part answers the constraint

**Storage adapts to the widest character.**
The first block measures per-character cost as a size delta (growing the string cancels the fixed header, so the number is build-independent): ASCII costs 1 byte per character, BMP text 2, astral text 4.
The width is chosen by the largest code point in the string, so the common case - ASCII and Latin text - pays the least.
This is the compactness of a narrow build for ordinary text, without the narrow build's breakage.

**Width is a property of the whole string.**
The second block shows the consequence of a *uniform-width* buffer: a 100-character ASCII string and a 100-character string with one emoji have the same length, but the second is heavier, because that single astral character forces *every* character to 4 bytes.
The representation does not mix widths within one string; the widest character sets the width for all of them.
This is worth understanding - it means one stray emoji can quadruple a large string's storage - but it is the price of keeping indexing O(1), which the next block relies on.

**Correctness for all text.**
The third block shows the payoff that matters most: `len("😀")` is `1`, not `2`, and indexing into `"a😀b"` lands on `'b'` at position 2, correctly.
Because the buffer stores whole code points at a uniform width, counting and indexing are correct for every character, astral ones included.
This is exactly what the narrow build got wrong - and it got it wrong silently, which is worse than an error.

**The choice is gone.**
The fourth block names what was eliminated.
The narrow build was compact but broke on astral characters; the wide build was correct but wasteful.
PEP 393 gives per-string width, which is correct like the wide build and compact like the narrow build for the common case - and there is no longer a narrow/wide compile-time flag at all.
Every Python 3.3+ install behaves the same way, correctly.

## The two-track note

Everything about what text *is* - code points versus bytes, the `str`/`bytes` distinction, encodings, why the Python 3 break separated them at all - is Deep Volume D's subject, the reason the whole schism was worth a decade of migration.
What this chapter records is the complementary internal advance: in 3.3, PEP 393 made the *representation* of `str` flexible, so the language's promise that a string is a sequence of code points became both correct and cheap to keep.
The modern consequence, verified above, is that string handling is uniformly correct across all installations and memory-efficient for ordinary text - and that the surrogate-pair bugs that plagued narrow builds are simply gone.
The one thing to remember is the uniform-width rule: a string's per-character cost is set by its widest character.

## Where this lands, and the close of Delegation

The flexible string representation is invisible in the best way: code that handles text just works, correctly and compactly, without anyone choosing a build or reasoning about surrogate pairs.
You rarely think about it, which is the point - PEP 393 turned a compile-time correctness-versus-memory tradeoff into an automatic per-string decision that gets both right.
Deep Volume D explains what text is and why Python 3 split it from bytes; this chapter is the record of the release that made the internal storage of that text adaptive.

This closes Volume 9, Delegation.
The volume's thesis paired three 3.3 advances - `yield from` for delegating to sub-generators (Chapter 9), namespace packages, and PEP 393 - as the release that matured Python's handling of composition and text.
Alongside them, 3.3 quietly consolidated the standard library: `inspect.signature` for callable introspection, `unittest.mock` for test doubles, and `ChainMap` for layered lookups.
Part IV continues with Volume 10, the provisional release of `asyncio`, following the generator machinery of `yield from` toward the async model it makes possible.
