# Chapter 241: The Iterator Turn

## The constraint

In Python 2, a surprising number of the language's most-used builtins had the same hidden habit: they built a list.
`range(n)` allocated a list of every integer from 0 to n-1 before your loop ran a single iteration.
`zip`, `map`, and `filter` each materialized a whole new list.
`dict.keys()`, `dict.values()`, and `dict.items()` each returned a fresh list snapshot of the dictionary's contents.
For small inputs none of this mattered.
For large ones it was a quiet disaster: `for i in range(10**9)` tried to allocate a billion-element list and could exhaust memory before the loop body ever ran, and a chain like `filter(pred, map(fn, big_sequence))` built two full-size intermediate lists just to iterate once.

The eager list was the *default*, and laziness - producing values on demand - was the exception you had to reach for (`xrange`, `itertools.imap`, and friends).
That default was backwards for the common case, where you iterate a sequence once and never need it to exist all at once.

Python 3.0 (2008) inverted it.
The constraint it answered: **make laziness the default posture of the language - range a compact object, zip/map/filter iterators, dict methods live views - so that producing-on-demand is what you get unless you explicitly ask to materialize.**

This is a two-track chapter.
The iterator protocol itself - `__iter__`, `__next__`, what makes something lazy, how iterators compose - belongs to Deep Volume F, and the streaming-pipeline cost model belongs to Chapter 91.
What this chapter owns is the release: the day the standard builtins stopped defaulting to eager lists and started defaulting to lazy production.

## What shipped

Listing 241.1 surveys the turn across range, the functional builtins, and dict views, on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- range is a compact object, not a list of every value ---
  range(10_000_000) type : range
  size of range(10) == size of range(10_000_000) : True
  it still indexes and has a length : r[5]=5, len=10000000
  in 2.x this allocated ten million ints up front; in 3.x range
  stores start/stop/step and COMPUTES each value on demand. its size
  is CONSTANT regardless of the range - laziness as the default
--- zip/map/filter return iterators, produced on demand ---
  zip(...)    is a zip
  map(...)    is a map
  filter(...) is a filter
  materialise when you ask : list(map) -> [0, 1, 4, 9, 16]
  each is a one-frame iterator, not a second list. chaining them -
  filter over map over range - streams values through without ever
  building the intermediate sequences (Chapter 91)
--- an iterator is single-use: it exhausts ---
  first list(it)  : ['0', '1', '2']
  second list(it) : []  (empty - already consumed)
  the flip side of laziness: an iterator yields each value ONCE, then
  is spent. this is the 3.x gotcha - a range you can reuse, but a
  map/zip/filter result you cannot. wrap in list() if you need it twice
--- dict.keys()/values()/items() are live VIEWS ---
  d.keys() type : dict_keys
  keys now : ['a', 'b']
  after d['c']=3, same view : ['a', 'b', 'c']  (reflects the change)
  in 2.x keys() returned a fixed list snapshot; in 3.x it is a VIEW
  that tracks the dict live and costs no copy. views even support
  set operations: d.keys() & other_keys
--- the memory consequence, stated plainly ---
  sum over range(1_000_000) : 499999500000  (never built a list)
  `for i in range(10**9)` is fine in 3.x - constant memory. the same
  code in 2.x tried to allocate a billion-element list and could
  MemoryError. the iterator turn changed what programs are feasible
--- the constraint answered ---
  Python 2 defaulted to building lists: range, zip, map, filter, and
  dict.keys all materialised. 3.0 made them lazy - iterators and
  views that produce on demand - so laziness is the default and
  eagerness the explicit choice (wrap in list()). constant memory
  replaced linear, and huge sequences became ordinary
```

## Why each part answers the constraint

**range is compact and computes on demand.**
The first block shows the flagship: `range(10)` and `range(10_000_000)` are the *same size* in memory, because a `range` stores only `start`, `stop`, and `step` and computes each value when asked.
It still indexes (`r[5]`) and reports its length, so it behaves like a sequence - but it never allocates the elements.
In Python 2 this call built ten million integer objects up front; in Python 3 it builds none.

**zip, map, and filter are iterators.**
The second block shows the functional builtins each returning a one-frame iterator rather than a list.
Their values materialize only when consumed, and chaining them - `filter` over `map` over `range` - streams values through the pipeline without ever building the intermediate sequences.
This is the streaming shape of Chapter 91, now the *default* behavior of the builtins rather than something you assemble from `itertools`.

**Single-use is the price of laziness.**
The third block is honest about the trade.
An iterator yields each value exactly once and is then spent: the first `list(it)` gets the values, the second gets an empty list.
This is the classic Python 3 gotcha - a `range` you can iterate repeatedly (it recomputes), but a `map`/`zip`/`filter` result you cannot.
When you need the values more than once, you wrap the iterator in `list()` to materialize it deliberately.
Laziness is the default; eagerness is the explicit, visible choice.

**dict methods are live views.**
The fourth block shows the other half of the turn.
`d.keys()` returns a `dict_keys` *view* - not a list snapshot but a live window onto the dict.
Add a key after taking the view, and the view reflects it, because it tracks the dict rather than copying it.
Views cost no allocation and, as a bonus, support set operations (`d.keys() & other`), which the old list snapshots could not.

**The consequence is what programs are feasible.**
The fifth block states the payoff plainly: `sum(x for x in range(1_000_000))` computes the total having never built a list, and `for i in range(10**9)` runs in constant memory.
The identical code in Python 2 attempted a billion-element allocation and risked `MemoryError`.
The iterator turn did not just save some bytes - it changed the set of programs that run at all.

## The two-track note

The iterator protocol - what `__iter__` and `__next__` do, why an exhausted iterator stays exhausted, how `itertools` composes lazy iterators - is Deep Volume F's to develop, and the streaming-pipeline reasoning is Chapter 91's.
What the timeline records is the release-level inversion: in 3.0, the standard builtins flipped from eager-by-default to lazy-by-default, and `list()` became the marker for "I actually want all of these at once."
The modern consequence, verified above, is that laziness is simply how Python's core sequence operations behave, and the single-use nature of iterators is the one piece of friction that inversion introduced - a small price for making huge sequences ordinary.

## Where this lands

The iterator turn is one of Python 3's least-discussed but most-consequential changes, precisely because it usually just works: loops over `range`, chains of `map`/`filter`, and iteration over dict views all do the memory-efficient thing without you asking.
Reach for `list()` when you genuinely need a materialized, reusable, indexable sequence; otherwise let the laziness stand.
Remember the single-use rule for `map`/`zip`/`filter` - it is the one place the inversion can surprise you.
Deep Volume F explains the protocol underneath; Chapter 91 explains the streaming model it enables; this chapter is the record of the release that made producing-on-demand the language's default.
