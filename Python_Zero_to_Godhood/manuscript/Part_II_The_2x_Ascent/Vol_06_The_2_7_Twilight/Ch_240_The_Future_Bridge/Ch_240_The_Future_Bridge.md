# Chapter 240: The Future Bridge

## The constraint

By 2010, Python faced a structural decision it could not avoid.
Python 3.0 had shipped in 2008 with deliberate, backward-incompatible changes - text and bytes split, `print` as a function, true division - and adoption was slow because the whole ecosystem of libraries had to move.
The question was how to run the two lines at once without either stranding the enormous Python 2 codebase or forking the language permanently into two parallel, independently-evolving branches.

The answer Python chose was *linear, not parallel*.
There would be no Python 2.8, no 2.9 - Python 2.7 (2010) would be the *last* 2.x release.
Feature development stopped on the 2.x line; 2.7 was frozen and instead kept alive as a long-term-support *bridge*, maintained for a full decade until its end-of-life on 1 January 2020.
All new language work went into 3.x.
The 2.x line did not keep evolving alongside 3.x; it held still and served as the crossing.

But a frozen bridge still needs a way for code to *walk across it*.
That is what the `__future__` mechanism provided, and it is the closing subject of Part II: **let a single Python 2.7 codebase opt into specific 3.x behaviours, one feature at a time, so migration could be gradual rather than a cliff.**

This chapter has appeared in miniature before - Chapter 222 introduced the `__future__` mechanism itself as a way to stage syntax changes.
Here it returns in its historical role: the tool that made the 2-to-3 crossing survivable, seen from the far side where every one of those futures has become the present.

## What shipped, and what it became

`from __future__ import <feature>` let a 2.x program adopt a 3.x behaviour ahead of time: `division` for true division, `print_function` for `print` as a callable, `unicode_literals` for unicode string literals, `absolute_import` for the 3.x import rules.
A codebase could add these imports file by file, test that it still worked on 2.7, and thereby converge on 3.x-compatible behaviour while still running on 2.x.
Listing 240.1 looks at those features from today, where they are all simply how Python works.

Verified output (CPython 3.13.5):

```text
--- the __future__ module names the 3.x behaviours 2.7 could opt into ---
  division           mandatory since Python 3.0
  print_function     mandatory since Python 3.0
  unicode_literals   mandatory since Python 3.0
  absolute_import    mandatory since Python 3.0
  with_statement     mandatory since Python 2.6
  each was OPTIONAL in 2.x via `from __future__ import ...` and
  MANDATORY (just the default) from the release shown. the module is
  a ledger of behaviours that migrated from opt-in to standard
--- true division: the flagship __future__ import, now the default ---
  1 / 2   : 0.5   (true division - 3.x default; needed the import in 2.x)
  7 // 2  : 3   (floor division - the explicit operator)
  in 2.x, 1/2 was 0 (integer floor) unless you wrote `from __future__
  import division`. 3.0 made / always true-divide and // always
  floor. what was a __future__ opt-in is now simply how / behaves
--- print is a function, not a statement (print_function, now default) ---
  print is callable : True
  print.__name__    : print
  print with keyword args!
  2.x `print x` was a STATEMENT; `from __future__ import
  print_function` made it the function it is in 3.x - so it takes
  sep=, end=, file=, and composes like any other call
--- all string literals are unicode text (unicode_literals, now default) ---
  type('...') : str   (str IS unicode text in 3.x)
  a plain literal holds code points : 4 of them
  2.x had bytes-y `str` and separate `unicode`; `from __future__
  import unicode_literals` made every '...' literal unicode. 3.0 made
  that the only kind of text (the Deep D story). the bridge previewed it
--- the point: these imports on 3.x are a harmless no-op ---
  this file imported division/print_function/unicode_literals
  and they changed nothing (already the default) : True
  the imports still EXIST and still parse on 3.x - they just do
  nothing, because the future arrived. that is why bridge code
  written for 2.7 keeps running unchanged on modern Python
--- the constraint answered ---
  Python chose a linear path: 2.7 was the final 2.x, frozen and kept
  alive as a bridge until 2020, not an evolving parallel line. the
  __future__ mechanism let one 2.7 codebase adopt 3.x behaviour
  feature by feature, so migration was gradual, not a cliff. today
  those futures are the present, and __future__ is the record of how
  the language crossed over
```

## Why each part answers the constraint

**`__future__` is a ledger of the crossing.**
The first block reads the `__future__` module itself: each feature records the release in which it became *mandatory* - the default, no import required.
`division`, `print_function`, `unicode_literals`, and `absolute_import` all became mandatory in 3.0; `with_statement` had already done so in 2.6.
The module is a literal record, in the language, of which behaviours migrated from opt-in to standard, and when.
Reading it is reading the migration's timeline.

**True division was the flagship.**
The second block shows the change that broke the most code and mattered the most: `1 / 2` is `0.5` today, but in Python 2 it was `0` - integer division floored silently, a bug factory in numeric code.
`from __future__ import division` let a 2.x file get the 3.x behaviour (`/` always true-divides, `//` always floors) ahead of time.
What was once the most-recommended `__future__` import is now simply how the division operators behave.

**Print became a function.**
The third block confirms `print` is a callable with keyword arguments (`end`, `sep`, `file`).
In Python 2 `print x` was a *statement* with special syntax; `from __future__ import print_function` turned it into the composable function of 3.x.
That change is why `print` can take `end=`, be passed as a callable, and behave like any other function - all of which the bridge let 2.x code preview.

**String literals became text.**
The fourth block shows `type("...")` is `str`, holding code points - the unicode text type.
Python 2 had a bytes-flavoured `str` and a separate `unicode`; `from __future__ import unicode_literals` made every quoted literal unicode, previewing the text/bytes model that Deep Volume D covers as the actual subject of the Python 3 break.
The bridge let 2.x code adopt the text model one file at a time.

**And on 3.x, the imports do nothing.**
The fifth block is the quiet closing point.
This very file really does `from __future__ import division, print_function, unicode_literals` at the top - and on Python 3 those imports change nothing, because the behaviours are already the default.
They still parse, still import, still exist; they are simply no-ops now.
That is precisely why bridge code written carefully for 2.7 continues to run unchanged on modern Python: the futures it reached for have all arrived.

## The two-track note

The `__future__` mechanism's machinery - how the compiler reads these imports as directives before executing the module, why they must appear at the top - is Chapter 222's and Deep Volume B's to detail; the text/bytes model that `unicode_literals` previewed is Deep Volume D's, the actual subject of the Python 3 break that Part III opens.
What this chapter records is the historical shape of the crossing: 2.7 as the deliberate last 2.x, frozen and maintained as a decade-long bridge, with `__future__` as the plank-by-plank mechanism that let code walk across.
The modern consequence, verified above, is that every one of those futures is now the present, and the `__future__` module stands as the language's own record of how it got from there to here.

## Where this lands, and the close of Part II

Part II, The 2.x Ascent, traced Python from the 2.0 licence rupture through the unification of types and classes, the syntax-for-control era, and into this twilight.
Volume 6's through-line was the one this chapter names directly: *linear, not parallel*.
Rather than maintain two evolving lines forever, Python chose to make 2.7 the final 2.x, freeze it, and pour its future into 3.x - accepting a long, painful migration as the price of not carrying the old model indefinitely.
The `__future__` bridge was the humane part of that hard choice: it let the migration happen gradually, file by file, feature by feature, so that no one had to leap the gap all at once.

That decision sets up everything that follows.
Part III, The Break, is the story of Python 3 itself - what it changed, why the text/bytes split was worth a decade of migration, and how the bet's terms are still visible in every release since.
Deep Volume D explains the break's actual subject; this chapter is the record of the twilight that made crossing to it survivable, and the last chapter of the 2.x ascent.
