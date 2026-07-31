# Chapter 237: Counter

## The constraint

Counting how often things occur is among the most common tasks a program performs: word frequencies in a document, event tallies in a log, hits per endpoint, items per category.
And for twenty years, Python made you re-derive the same small pattern every time.
The naive form guarded every increment:

```python
counts = {}
for item in items:
    if item in counts:
        counts[item] += 1
    else:
        counts[item] = 1
```

The pattern improved over the years - `counts[item] = counts.get(item, 0) + 1` avoided the branch, and `collections.defaultdict(int)` avoided the guard entirely - but every one of these is ceremony wrapped around a single idea: *tally the occurrences*.
And none of them gave you the operations that make a tally useful.
"What are the ten most common words" still meant sorting the dict by value with a `key=` function and a `reverse=True`.
"Combine the counts from these two sources" still meant a merge loop.

The constraint Python 2.7 (2010) answered was this: **make counting a complete, named data type - not just the increment, but the ranking, combining, and streaming that counting implies.**

This is a two-track chapter.
The dict it is built on - the hash table, the O(1) lookup, why a dict subclass is the right foundation - belongs to Deep Volume Q.
The streaming-accumulation shape that `update` fits into belongs to Chapter 91.
What this chapter owns is the release: the day "count things" stopped being a pattern every codebase re-derived and became a tool you import.

## What shipped

Python 2.7 added `collections.Counter`, a dict subclass specialized for counting: a missing key reads as `0` (so `c[k] += 1` always works), the constructor tallies an iterable in one call, and a set of counting-specific methods and operators come attached.
Listing 237.1 walks through them on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- Counter: a missing key counts as zero ---
  Counter(votes) : {'yes': 3, 'no': 2, 'abstain': 1}
  c['yes']    : 3
  c['missing'] : 0  (absent key -> 0, no KeyError)
  the pre-2.7 tally was `if k in d: d[k]+=1 else: d[k]=1`. Counter
  makes a missing key read as 0, so counting is just c[k] += 1 -
  and Counter(iterable) tallies a whole sequence in one call
--- most_common(): the counting-specific operation ---
  word counts : {'the': 3, 'quick': 1, 'brown': 1, 'fox': 1, 'lazy': 1, 'dog': 1, 'end': 1}
  most_common(2) : [('the', 3), ('quick', 1)]
  most_common(n) returns the n highest-count items, already sorted -
  the exact operation a plain dict makes you write sorted(...,
  key=..., reverse=True) for. it is the point of counting
--- counters do arithmetic: add and subtract tallies ---
  monday + tuesday : {'apples': 4, 'bananas': 6, 'cherries': 5}
  tuesday - monday : {'bananas': 2, 'cherries': 5}
  adding counters sums per-key counts; subtracting removes them
  (dropping non-positive results). combining tallies from two
  sources is one operator, not a merge loop
--- update(): accumulate more counts into an existing Counter ---
  after streaming 3 batches : {'a': 3, 'b': 1, 'c': 1}
  update() ADDS to the counts (unlike dict.update which REPLACES),
  so a Counter accumulates naturally across a stream of batches -
  the streaming-tally shape (Chapter 91) with counting built in
--- elements(): expand a Counter back to items ---
  sorted(elements()) : ['blue', 'green', 'green', 'green', 'red', 'red']
  elements() yields each key as many times as its count - the
  inverse of Counter(iterable). a Counter is really a MULTISET:
  a set where membership has a multiplicity
--- the constraint answered ---
  counting was a dict wrapped in a presence guard, re-derived in
  every codebase. 2.7's Counter made it a type: zero-default lookup
  so c[k]+=1 always works, most_common() for ranking, +/- to combine
  tallies, update() to stream. 'count things' stopped being a
  pattern and became a tool
```

## Why each part answers the constraint

**The zero default removes the guard.**
The first block shows the foundation: `Counter(votes)` tallies the whole list in one call, and a missing key reads as `0` rather than raising `KeyError`.
That single behavior - absent means zero - is what makes `c[k] += 1` always correct without a presence check.
The guard that every hand-rolled tally needed is gone, folded into the type's `__missing__` behavior.

**`most_common` is the operation counting exists for.**
The second block shows the method that distinguishes a `Counter` from "a dict I happen to be incrementing."
`most_common(2)` returns the two highest-count items, already sorted by count - the exact "top N" query that a plain dict forces you to express as `sorted(d.items(), key=lambda kv: kv[1], reverse=True)[:2]`.
Ranking by frequency is the *point* of counting, and `Counter` makes it a method call.

**Counters do arithmetic.**
The third block shows counters combining as values.
`monday + tuesday` sums per-key counts across two tallies; `tuesday - monday` subtracts them, dropping counts that fall to zero or below.
Merging tallies from two sources - two log files, two shards, two days of inventory - is one operator, not a merge loop.
This is what it means for counting to be a *complete* type: the operations you actually perform on tallies are built in.

**`update` accumulates, which fits streaming.**
The fourth block highlights a subtlety that matters.
`Counter.update` *adds* counts, where `dict.update` *replaces* values.
So a `Counter` naturally accumulates across a stream of batches: call `update` on each batch and the counts grow.
This is the streaming-tally shape of Chapter 91 with counting built in - you never hold the whole stream, only the running `Counter`.

**`elements` reveals it is a multiset.**
The fifth block expands a `Counter` back into its items, each key repeated as many times as its count - the inverse of `Counter(iterable)`.
This exposes what a `Counter` fundamentally is: a *multiset*, a set in which membership carries a multiplicity.
That framing explains the arithmetic (multiset union and difference) and the constructor (count the multiplicities of an iterable) as facets of one coherent abstraction rather than a grab-bag of methods.

## The two-track note

The dict machinery - the hash table, why subclassing `dict` (rather than wrapping one) is the right design, how `__missing__` produces the zero default - is Deep Volume Q's to detail.
The streaming-accumulation pattern that `update` slots into is Chapter 91's.
What the timeline records is the release act: in 2.7, counting became a named type with the ranking, combining, and streaming operations that counting implies, retiring a pattern that every codebase had re-derived for two decades.
The modern consequence, verified above, is that `Counter` is still the first tool a Python programmer reaches for whenever the task is "how many of each," and its multiset arithmetic still expresses tally-combining more clearly than any manual loop.

## Where this lands

`Counter` is a small, complete type that captures a genuinely universal task and all its natural operations.
Reach for it any time you are about to write an increment-with-guard loop; reach for `most_common` instead of sorting by value; reach for `+`/`-` instead of a merge loop; and let `update` accumulate a running tally across a stream.
Deep Volume Q explains the dictionary underneath; Chapter 91 explains the streaming shape; this chapter is the record of the release that turned counting from a re-derived pattern into a named, complete tool.
