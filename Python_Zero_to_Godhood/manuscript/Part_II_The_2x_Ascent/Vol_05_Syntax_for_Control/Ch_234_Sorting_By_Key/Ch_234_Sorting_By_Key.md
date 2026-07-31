# Chapter 234: Sorting by Key

## The constraint

Before Python 2.4, sorting had one shape and one steering wheel.
The shape was `list.sort()` - in place only, mutating the list and returning `None`, so it could never appear in an expression.
The steering wheel was `cmp=`, a two-argument comparator function: you passed a function that took two elements and returned negative, zero, or positive, and the sort called it to decide every ordering question.
Both were problems.

The in-place-only shape meant you could not sort as part of a larger expression - no sorting inside a comprehension, no sorting a value on its way into a function call, no `return sorted_version` without a temporary variable and a separate `.sort()` line.

The comparator was worse, and the problem was performance.
A comparator is called *once per comparison*, and a sort of n elements makes on the order of n log n comparisons.
Every one of those calls crossed from the C sort routine back into a Python-level function - the single most expensive kind of operation in a hot loop.
Sorting a list of 10,000 items by a comparator meant on the order of 130,000 Python function calls just to decide orderings.

The constraint Python 2.4 (2004) answered was this: **replace the comparator model with a key-extraction model, add an expression-form `sorted()`, and guarantee stability - so that describing *what to sort by* is cheap, composable, and never requires writing a comparison.**

This is a two-track chapter.
The comparison protocol itself - how objects define their ordering, what "rich comparison" means, how the sort algorithm (Timsort) uses it - belongs to Deep Volume B (the execution and comparison model).
What this chapter owns is the release: the day key-based, stable sorting became the model, and the comparator began its slide toward removal.

## What shipped

Python 2.4 shipped three connected things: a `sorted()` builtin that returns a *new* sorted list, a `key=` parameter that names a one-argument function called *once per element* to extract that element's sort key, and a *guarantee* that the sort is stable - equal elements keep their input order.
Listing 234.1 shows all three and what stability enables, on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- sorted() returns a new list; sort() mutates in place ---
  sorted(data) -> [1, 1, 2, 3, 4, 5, 6, 9]
  original unchanged : [3, 1, 4, 1, 5, 9, 2, 6]
  sorted() is the expression form: it returns a NEW sorted list and
  leaves the input alone, so it works in a comprehension or argument.
  list.sort() still exists for in-place sorting of a list you own
--- key=: called ONCE per element, not once per comparison ---
  sorted(words, key=str.lower) -> ['Apple', 'banana', 'cherry', 'Date']
  sorted by len -> ['Date', 'Apple', 'banana', 'cherry']
  key called 4 times for 4 elements (once each)
  the OLD cmp= comparator ran O(n log n) times, each a Python call;
  key= runs exactly n times to extract keys, then compares those in C.
  same order, far fewer Python-level calls - the performance reason
  key= replaced cmp= (which 3.0 removed entirely)
--- stability: equal keys keep their input order (guaranteed since 2.4) ---
  by age : [('Bob', 25), ('Dave', 25), ('Alice', 30), ('Carol', 30)]
  Alice before Carol (both 30), Bob before Dave (both 25) - equal
  keys stayed in INPUT order. 2.4 made this a guarantee, not luck,
  which is what makes the next trick correct
--- stability composes: multi-key sort by sorting LEAST-significant first ---
  sort by name, then STABLE-sort by age -> [('Bob', 25), ('Dave', 25), ('Alice', 30), ('Carol', 30)]
  because the age sort is stable, it preserves the name order within
  each age. so 'sort by A then B' = sort by B, then stable-sort by A.
  stability turns multi-criteria sorting into a pipeline of simple
  one-key sorts - no comparator, no compound key tuples needed
--- the modern one-liner: a tuple key does it in a single pass ---
  key=lambda p: (p[1], p[0]) -> [('Bob', 25), ('Dave', 25), ('Alice', 30), ('Carol', 30)]
  or extract a TUPLE key and let tuple ordering do the tiebreak in
  one pass. either way you describe the KEY, never a comparison -
  the model 2.4 established and Python has used ever since
```

## Why each part answers the constraint

**`sorted()` is the expression form.**
The first block shows `sorted(data)` returning a new list while leaving the input untouched.
That is what makes it usable where `list.sort()` never could be: inside a comprehension, as a function argument, in a `return`.
`list.sort()` remains for the case where you own the list and want to sort it in place without allocating a copy; `sorted()` is for everywhere else.

**`key=` collapses the call count.**
The second block is the performance heart.
`key=str.lower` sorts case-insensitively; the instrumented `keyfn` proves the key was called exactly four times for four elements - *once each*.
The old comparator model would have called a Python function on the order of n log n times.
The key model calls the Python key function n times to extract keys, then does all the comparisons on those keys in C.
For large lists this is the difference between tens of thousands of Python calls and a few thousand - the reason `key=` did not just supplement `cmp=` but replaced it, and the reason Python 3.0 removed `cmp=` from `sort`/`sorted` entirely.
Describe the key, and the expensive comparison work stays in C.

**Stability is a guarantee, not luck.**
The third block sorts people by age and shows that Alice stays before Carol (both 30) and Bob before Dave (both 25) - equal keys preserve input order.
Before 2.4 this happened to be true of the implementation but was not promised; 2.4 made it a language guarantee.
That promise is not a nicety - it is the precondition for the next technique.

**Stability composes into multi-key sorting.**
The fourth block uses the guarantee: sort by name first, then *stably* sort by age, and the result is ordered by age with names in order within each age group.
Because the age sort preserves the existing name order among equal ages, "sort by A then B" becomes "sort by B, then stable-sort by A" - a pipeline of simple one-key sorts, each trivial to write, no comparator anywhere.
This is the elegant consequence of guaranteeing stability: complex orderings decompose into a sequence of simple ones.

**Or do it in one pass with a tuple key.**
The fifth block shows the modern shorthand: `key=lambda p: (p[1], p[0])` extracts a `(age, name)` tuple, and tuple ordering breaks ties automatically - the same result in a single sort.
Both approaches share the defining property of the 2.4 model: you describe the *key*, never a *comparison*.
That is the shift the release made permanent.

## The two-track note

The comparison protocol - how `<` is defined on objects, rich comparison methods, how Timsort exploits existing order and why it is stable - is Deep Volume B's to develop, and the cost model that says "a Python call in the inner loop is the thing to eliminate" is Chapter 88's territory.
What the timeline records is the release decision: in 2.4, Python replaced "tell me how to compare two things" with "tell me what to sort by," added an expression-form `sorted()`, and promised stability.
The modern consequence, verified above, is that key-based stable sorting is still the only model a working Python programmer needs - `cmp=` is gone, and the techniques the guarantee enables are exactly as valid today as in 2.4.

## Where this lands

Sorting by key is one of the most-used features in the language and one of the least-thought-about, precisely because 2.4 got the model right.
Reach for `sorted(xs, key=...)` for the expression form, a tuple key for compound orderings, and successive stable sorts when the criteria are computed separately.
You will almost never write a comparison function in Python, and the reason is this release: it made the key the thing you describe, kept the comparisons in C, and promised the stability that lets simple sorts compose into complex ones.
Deep Volume B explains how comparison works underneath; this chapter is the record of the release that made "describe the key, not the comparison" the Python way.
