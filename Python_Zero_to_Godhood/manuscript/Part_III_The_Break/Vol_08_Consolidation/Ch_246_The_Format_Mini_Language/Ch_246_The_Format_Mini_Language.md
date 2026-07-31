# Chapter 246: The Format Mini-Language

## The constraint

Python's original string formatting was the `%` operator, borrowed from C:

```python
"%s is %d years old" % (name, age)
```

It was compact and familiar to anyone who knew `printf`, and it was fragile.
The format string and the argument tuple were coupled only by position and count, checked only at runtime: pass the wrong number of arguments, or the wrong type, and you got a `TypeError` deep in the formatting.
The single-argument-versus-tuple ambiguity (`"%s" % value` versus `"%s" % (value,)`) was a perennial trap.
And the mini-grammar of `%` conversions was limited and awkward to extend - aligning columns, grouping thousands, or converting bases meant reaching outside it for `ljust`, manual math, or `bin`/`hex` plus string surgery.

Python 2.6/3.0 introduced `str.format` with numbered fields - `"{0} is {1}".format(name, age)` - which fixed the type coupling and added a far richer specification grammar.
Python 3.1 (2009) added the piece that made it pleasant for the common case: **automatic field numbering**, so `"{} is {}"` numbers its own fields.

But the durable contribution was not the `{}` syntax itself.
It was the *format mini-language* - the grammar after the colon that describes how a value becomes text.
The constraint this era answered: **settle, once, how values turn into formatted strings - alignment, width, grouping, precision, bases - in one consistent grammar that would outlast the surface syntax.**

This is a two-track chapter.
Text and encoding - what a string *is*, how characters become bytes - belong to Deep Volume D.
What this chapter owns is the release: the day auto-numbering removed the index-counting chore and the format mini-language became the settled way to describe formatted text.

## What shipped

Listing 246.1 walks through auto-numbering, named fields, and the mini-language - grouping, precision, alignment, bases - and shows f-strings reusing the identical spec, on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- auto-numbering: {} fills fields left to right (3.1) ---
  '{} is {}'.format(name, age) : Ada is 36
  numbered '{0} {1} {0}' reuses : a b a
  3.1 let fields number themselves ({}), so you no longer count
  indices for the common case. numbered fields {0} remain for reuse
  or reordering; named fields {who} for clarity
--- named fields read like a template ---
  Ada spent 42 on books
  named placeholders make the call self-documenting and order-
  independent - the arguments say which field they fill
--- the format mini-language: everything after the colon ---
  thousands separator  '{:,}'   : 1,234,567
  fixed precision      '{:.2f}' : 3.14
  both                 '{:,.2f}': 1,234,567.89
  percentage           '{:.1%}' : 7.3%
  after the colon comes a SPEC: ,=group thousands, .2f=two decimals,
  .1%=percent. these describe how the value becomes text, and they
  are the reason format() replaced ad-hoc rounding and string math
--- alignment and width: building aligned columns ---
  |apple   |    3|
  |fig     |   12|
  |cherry  |  155|
  '{:<8}' left-aligns in width 8; '{:>5}' right-aligns in width 5.
  columns line up without manual padding - the mini-language does
  the spacing, which is why tabular text stopped needing ljust/rjust
--- number bases and sign, in the same spec grammar ---
  binary  '{:b}'  of 42 : 101010
  hex     '{:#x}' of 255: 0xff
  signed  '{:+d}' of 7  : +7
  base conversion and explicit sign are part of one consistent
  grammar, not separate functions (bin(), hex()) plus prefix hacks
--- the payoff: f-strings (3.6) reuse this exact mini-language ---
  '{:,.2f}'.format(value) : 1,234,567.89
  f'{value:,.2f}'          : 1,234,567.89
  identical output : True
  the f-string is newer SYNTAX over the SAME spec after the colon.
  learn the mini-language once and it serves format(), str.format,
  and f-strings - which is why 3.1 settled the durable part
--- the constraint answered ---
  %-formatting was positional and fragile. str.format with auto-
  numbering (3.1) removed index-counting for the common case, and
  its format mini-language gave one consistent grammar for width,
  alignment, grouping, precision, and bases. f-strings later reused
  that grammar verbatim - the release settled how values become text
```

## Why each part answers the constraint

**Auto-numbering removes the chore.**
The first block shows the 3.1 addition: `"{} is {}".format(name, age)` numbers its own fields left to right, so the common case needs no indices.
Numbered fields `{0}` remain available when you want to *reuse* an argument (`"{0} {1} {0}"`) or reorder, and named fields `{who}` when you want clarity - but the everyday case is now free of counting.

**Named fields read like templates.**
The second block shows `"{user} spent {amount} on {item}".format(user=..., amount=..., item=...)` - self-documenting and order-independent, because each argument declares which field it fills.
This is the readability that `%`-formatting's bare positional tuple could never offer.

**The mini-language is the real content.**
The third block reaches the durable core: the spec after the colon.
`{:,}` groups thousands, `{:.2f}` fixes two decimals, `{:,.2f}` does both, `{:.1%}` formats a fraction as a percentage.
These describe *how a value becomes text*, and they replaced the ad-hoc rounding, manual comma insertion, and string arithmetic that pre-format code scattered everywhere.
One grammar, composable, covering the operations formatting actually needs.

**Alignment builds columns.**
The fourth block shows width and alignment: `{:<8}` left-aligns in a field of width 8, `{:>5}` right-aligns in width 5, and the result is tabular text with columns that line up - no manual `ljust`/`rjust` padding.
The mini-language does the spacing, which is why aligned output stopped requiring the string-method gymnastics it used to.

**Bases and sign share the grammar.**
The fifth block shows base conversion (`{:b}` binary, `{:#x}` hex with prefix) and explicit sign (`{:+d}`) as part of the *same* spec grammar - not separate `bin()`/`hex()` functions plus prefix hacks, but one consistent language.
This consolidation is the point: formatting concerns that used to be scattered across functions and idioms became one grammar.

**f-strings reuse it verbatim.**
The sixth block is the payoff that justifies calling this the "settled" part.
`"{:,.2f}".format(value)` and `f"{value:,.2f}"` produce identical output, because the f-string (3.6) is newer *syntax* over the *same* spec after the colon.
Learn the mini-language once and it serves `format()`, `str.format`, and f-strings alike.
The 3.1-era work settled the grammar; the 3.6 f-string changed only how you attach values to it.

## The two-track note

The nature of text itself - what a `str` is, how it relates to bytes and encodings - is Deep Volume D's subject, the actual centerpiece of the Python 3 break.
What this chapter records is narrower and complementary: the release-era settling of how values become *formatted* text.
The `%` operator still exists and still works; `str.format` and its mini-language layered a richer, safer, more consistent system over it, and f-strings later gave that system its most ergonomic surface without changing the spec grammar underneath.
The modern consequence, verified above, is that the format mini-language is a single skill that pays off across every formatting surface Python offers.

## Where this lands

The format mini-language is one of those investments that keeps returning: the `:,.2f`, `:<8`, `:>5`, `:.1%` vocabulary you learn for `str.format` is exactly what you use inside f-strings years later.
Reach for f-strings as the everyday surface - they are the most readable - but know that everything after the colon is this mini-language, and that `str.format` and `format()` remain the right tools when the template and its values are separated (a template loaded from a file, a format applied to many values).
Deep Volume D explains what text is; this chapter is the record of the release that settled how values turn into it.
