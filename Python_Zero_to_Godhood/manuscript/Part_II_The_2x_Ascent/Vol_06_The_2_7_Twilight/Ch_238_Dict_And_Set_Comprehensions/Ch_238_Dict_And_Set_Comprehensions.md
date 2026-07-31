# Chapter 238: Dict and Set Comprehensions

## The constraint

Python 2.0 gave the language list comprehensions - `[f(x) for x in xs]` - and they were an immediate success.
Within a few years the comprehension was the signature Python way to build a list: a single expression that says "map this over that, keeping these," reading almost like the set-builder notation of mathematics.

But the comprehension family had a conspicuous hole.
Lists had the syntax; dicts and sets did not.
To build a dictionary from a computation you wrapped a generator of pairs in the `dict` constructor - `dict((k, v) for k, v in ...)` - and to build a set you wrapped a generator in `set(...)`.
Both worked, and both read as a *function call around a generator expression* rather than as a first-class way to construct that container.
The declarative clarity that `[...]` gave lists was missing for the two other core containers, and the asymmetry was arbitrary: nothing about dicts or sets made them less deserving of the shape.

Python 3.0 filled the hole with dedicated syntax - `{k: v for ...}` and `{x for ...}`.
And Python 2.7 (2010) *backported* both.
That backport is the point of this chapter's placement: 2.7's defining role was to be the bridge release, the last 2.x, deliberately stuffed with 3.x features so that a single codebase could target both lines at once.
The constraint 2.7 answered here was: **give the 2.x line the same declarative container-building syntax 3.0 introduced, so the comprehension family is complete on both sides of the migration.**

This is a two-track chapter.
Comprehension scoping and evaluation - that a comprehension has its own scope, how the iteration variable is contained, how it compiles - belong to Deep Volume B.
What this chapter owns is the release: the day dict and set comprehensions completed the family, and the bridging role that put them in 2.7.

## What shipped

Listing 238.1 shows both new comprehension forms and the completed family, on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- dict comprehension: {key: value for ...} ---
  {n: n*n for n in range(1,6)} : {1: 1, 2: 4, 3: 9, 4: 16, 5: 25}
  before this you wrote dict((n, n*n) for n in ...) - a dict() call
  around a generator of pairs. the comprehension says the same thing
  with the {k: v ...} shape that mirrors a dict literal
--- the classic use: invert a dict ---
  invert {'alice': 1, 'bob': 2, 'carol': 3}
    -> {1: 'alice', 2: 'bob', 3: 'carol'}
  swapping keys and values is one line and reads as exactly that.
  the pre-2.7 dict((v, k) for k, v in ...) buried the intent in a
  constructor call
--- dict comprehension with a filter ---
  items with price <= 2 : {'banana': 1, 'date': 2}
  the same `if` clause list comprehensions have, so filtering while
  building a dict is one expression - no build-then-delete pass
--- set comprehension: {expr for ...} ---
  distinct lowercased : ['apple', 'banana', 'cherry']
  {x for ...} builds a set: unique by construction (Chapter 228),
  with the comprehension's map-and-filter shape. replaces
  set(w.lower() for w in words)
--- the family is now complete: same shape, four containers ---
  list : [0, 1, 4, 9, 16]
  set  : [0, 1, 2]
  dict : {0: 0, 1: 1, 2: 4, 3: 9, 4: 16}
  gen  : sum -> 30  (parens = lazy generator)
  one comprehension shape - map, optional filter - for list, set,
  dict, and (lazily) generator. learn it once, build any container
--- the constraint answered ---
  list comprehensions (2.0) had no dict/set sibling, so those were
  built with constructor-around-genexpr calls. 3.0 added {k: v ...}
  and {x ...}, and 2.7 backported them - bridging the two lines and
  completing the comprehension family so every builtin container has
  the same declarative build syntax
```

## Why each part answers the constraint

**The dict comprehension mirrors the dict literal.**
The first block shows `{n: n*n for n in range(1, 6)}` building a dict directly.
The syntax deliberately echoes the dict literal `{k: v}` - `{key: value for ...}` reads as "a dict of these pairs," where the old `dict((n, n*n) for n in ...)` read as "call `dict` on a generator of tuples."
The information is the same; the intent is far more visible in the comprehension.

**Inversion is the canonical case.**
The second block shows the operation that dict comprehensions are most loved for: swapping keys and values.
`{v: k for k, v in name_to_id.items()}` inverts a mapping in one line that reads as exactly "make a dict keyed by the old values."
The pre-2.7 form, `dict((v, k) for k, v in ...)`, buried that intent inside a constructor call.

**Filtering comes for free.**
The third block shows the `if` clause working exactly as it does in list comprehensions: `{name: p for name, p in prices.items() if p <= 2}` builds a filtered dict in one pass.
There is no build-everything-then-delete step - the filter is part of the construction, the same capability lists have had since 2.0.

**Set comprehensions complete the triad.**
The fourth block shows `{w.lower() for w in words}` building a set of distinct lowercased words - unique by construction (Chapter 228), with the comprehension's familiar map-and-filter shape, replacing `set(w.lower() for w in words)`.

**One shape, four containers.**
The fifth block is the payoff.
The identical comprehension skeleton - an expression, a `for`, an optional `if` - now builds a list with `[...]`, a set with `{...}`, a dict with `{k: v ...}`, and, with parentheses, a lazy generator.
You learn the shape once and build any core container with it.
That uniformity is what "completing the family" means: the arbitrary gap where dicts and sets lacked the syntax is closed.

## The two-track note

The scoping and compilation of comprehensions - that each has its own scope so the loop variable does not leak (a 3.0 change), how the compiler turns the syntax into an efficient build loop, why a generator expression is the lazy member of the family - are Deep Volume B's to develop.
What the timeline records is twofold: 3.0 introduced dict and set comprehension syntax, and 2.7 backported it as part of its bridge role, so a codebase straddling the two lines could use the same declarative container-building on both.
The modern consequence, verified above, is that all four container-building forms share one shape, and that shape is among the most recognizable in the language.

## Where this lands

Dict and set comprehensions are the kind of feature whose absence you only notice in hindsight: once the family is complete, building any container from a computation is the same readable gesture, and the constructor-around-generator idioms they replaced look needlessly indirect.
Reach for `{k: v for ...}` to build or transform a mapping, `{x for ...}` to build a set of distinct results, and remember that swapping brackets for parentheses gives you the lazy generator when you do not need the whole container at once.
Deep Volume B explains how comprehensions scope and compile; this chapter is the record of the release that completed the family and, in doing so, did part of the quiet work of bridging Python 2 to Python 3.
