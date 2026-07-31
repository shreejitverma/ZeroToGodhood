# Chapter 258: Math Isclose

## The constraint

The first surprise nearly every programmer meets with floating point is this:

```python
>>> 0.1 + 0.2 == 0.3
False
```

It is not a bug in Python; it is how binary floating point works.
The decimals `0.1`, `0.2`, and `0.3` have no exact representation in base-2, so they are stored as the nearest representable values, and the tiny errors do not cancel - `0.1 + 0.2` lands at `0.30000000000000004`, a hair off `0.3`.
The lesson is that `==` on *computed* floats is almost always the wrong question.

The usual fix was a hand-picked epsilon: `abs(x - y) < 0.0001`.
And that fix is *also* wrong, just less obviously - because a fixed absolute epsilon does not scale.
A tolerance of `0.0001` is far too coarse near zero (it would call `0.00005` and `0` equal) and far too tight for large numbers (it would call `1e16` and `1e16 + 2` - which agree to sixteen significant figures - "far apart").
There is no single fixed epsilon that is right across magnitudes, because "close" is inherently relative to the scale of the numbers involved.

The constraint Python 3.5 (2015, PEP 485) answered: **put the correct way to compare floats in the standard library - a relative tolerance that scales with magnitude, plus an absolute tolerance for the near-zero case - so "are these floats close enough?" is a standard function, not an ad-hoc guess.**

This is a two-track chapter.
The float representation itself - why binary floating point is inexact, ULPs, the IEEE 754 model - belongs to the Deep Volumes on Python's numeric model.
What this chapter owns is the release: the day the right float comparison became a builtin.

## What shipped

`math.isclose(a, b, rel_tol=1e-9, abs_tol=0.0)` returns whether `a` and `b` are within tolerance: by default a *relative* tolerance scaled to the larger magnitude, with an optional *absolute* tolerance for values near zero.
Listing 258.1 shows the trap and the tool on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- the classic trap: computed floats are not exactly equal ---
  0.1 + 0.2      : 0.30000000000000004
  0.1 + 0.2 == 0.3 : False   (False - the famous surprise)
  math.isclose(0.1 + 0.2, 0.3) : True   (True)
  0.1, 0.2, 0.3 have no exact binary form, so the sum lands a tiny
  bit off 0.3 and == fails. isclose asks the RIGHT question: are they
  within a sensible tolerance of each other?
--- relative tolerance scales with the magnitude compared ---
  isclose(1000000.0, 1000000.1)     : False
  isclose(1.0, 1.1)                 : False
  the DEFAULT tolerance is relative (rel_tol=1e-9): a 0.1 difference
  is negligible next to a million but huge next to 1. a fixed epsilon
  cannot do both; a relative tolerance is correct at every scale
--- tuning rel_tol: how many significant figures must agree ---
  isclose(1.0, 1.001, rel_tol=1e-2) : True   (1% - close enough)
  isclose(1.0, 1.001, rel_tol=1e-4) : False   (0.01% - too far)
  rel_tol is the maximum allowed difference as a FRACTION of the
  larger magnitude. raise it to be lenient, lower it to demand more
  agreeing significant figures
--- abs_tol: the fix for comparisons near zero ---
  isclose(tiny, 0.0)                : False
  isclose(tiny, 0.0, abs_tol=1e-9)  : True
  relative tolerance breaks down at zero (any tolerance times 0 is 0),
  so isclose(x, 0.0) is almost always False. for near-zero values you
  supply an ABSOLUTE tolerance - the one case relative cannot cover
--- why a hand-rolled epsilon was the wrong habit ---
  naive_close(1e16, 1e16 + 2) with eps=1e-4 : False
  isclose(1e16, 1e16 + 2)                   : True
  a fixed 1e-4 epsilon calls 1e16 and 1e16+2 FAR apart (abs diff 2),
  though they agree to ~16 significant figures. isclose's relative
  tolerance treats them as close, which is what you almost always mean
--- the constraint answered ---
  == on computed floats is a bug because binary float is inexact, and
  a hand-picked epsilon is wrong across scales. math.isclose (3.5)
  encodes the correct comparison: relative tolerance by default,
  absolute tolerance for near-zero. 'are these floats close enough?'
  became a standard function instead of an ad-hoc guess
```

## Why each part answers the constraint

**The classic trap.**
The first block shows the surprise and the fix together: `0.1 + 0.2` is `0.30000000000000004`, so `== 0.3` is `False`, but `math.isclose(0.1 + 0.2, 0.3)` is `True`.
`isclose` asks the question you actually meant - "are these within a sensible tolerance?" - rather than the almost-always-wrong "are these bit-for-bit identical?".

**Relative tolerance scales.**
The second block shows the default is *relative* (`rel_tol=1e-9`): both `isclose(1000000.0, 1000000.1)` and `isclose(1.0, 1.1)` are `False`, because a `0.1` gap is significant relative to `1` and, while it is tiny relative to a million, still exceeds `1e-9` of it.
The key point is that the tolerance is a *fraction of the magnitude compared*, so it behaves sensibly whether the numbers are tiny or huge - something a single fixed epsilon can never do.

**Tuning `rel_tol` sets required precision.**
The third block shows control: `isclose(1.0, 1.001, rel_tol=1e-2)` is `True` (a 1% tolerance accepts them) while `rel_tol=1e-4` makes it `False` (0.01% is too demanding for a 0.001 gap).
`rel_tol` is effectively "how many significant figures must agree" - raise it to be lenient, lower it to demand more precision.

**`abs_tol` handles zero.**
The fourth block covers the one case relative tolerance cannot: comparisons to zero.
`isclose(1e-10, 0.0)` is `False`, because any relative tolerance times zero is zero, so nothing is ever relatively close to `0.0`.
For near-zero values you pass an *absolute* tolerance: `isclose(1e-10, 0.0, abs_tol=1e-9)` is `True`.
This is the deliberate two-part design - relative for the general case, absolute for the neighborhood of zero.

**The fixed epsilon is the wrong habit.**
The fifth block shows the failure of the old approach at the large end: a fixed `1e-4` epsilon calls `1e16` and `1e16 + 2` "far apart" because their absolute difference is `2`, even though they agree to about sixteen significant figures.
`isclose` correctly reports them as close, because relative to `1e16` a difference of `2` is negligible.
This is exactly the case a hand-rolled absolute epsilon gets wrong, and it is why "pick an epsilon" was never a real solution.

## The two-track note

Why floats are inexact - the finite mantissa, the base-2 representation of base-10 fractions, the unit-in-the-last-place spacing that makes `1e16 + 1` and `1e16` round together - is the numeric model's subject in the Deep Volumes.
`isclose` is the practical consequence: given that floats are inexact, equality is the wrong test, and this function encodes the right one.
What the timeline records is the release act: in 3.5, PEP 485 put a correct, scale-aware float comparison in the standard library, with a companion `cmath.isclose` for complex numbers.
The modern consequence, verified above, is that `math.isclose` is the standard way to compare computed floats, and the hand-picked epsilon is recognized as the anti-pattern it always was.

## Where this lands

`math.isclose` is a small function that encodes a genuinely tricky piece of numerical judgment.
Never compare computed floats with `==`; reach for `isclose` instead.
Use the default relative tolerance for general comparisons, tune `rel_tol` when you need a specific number of agreeing figures, and - critically - remember to pass an `abs_tol` whenever one of the values may be at or near zero, the one case the relative default cannot handle.
The Deep Volumes on Python's numeric model explain why floats behave this way; this chapter is the record of the release that put the correct comparison in the standard library.
