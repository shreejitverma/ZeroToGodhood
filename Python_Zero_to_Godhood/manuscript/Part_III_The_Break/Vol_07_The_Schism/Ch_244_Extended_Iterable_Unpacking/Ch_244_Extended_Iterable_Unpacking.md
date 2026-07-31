# Chapter 244: Extended Iterable Unpacking

## The constraint

Python's tuple unpacking was one of its earliest and best-loved features: `a, b, c = triple` binds three names to three values in one clean assignment, and `x, y = y, x` swaps without a temporary.
But it had a rigid requirement: the number of targets had to match the number of values *exactly*.
Three names required exactly three values; a mismatch raised `ValueError`.

That exactness made the single most common structural operation - "take the first item, and the rest" - awkward.
There was no way to write it as an unpacking, because "the rest" is not a fixed count.
So you fell back to indexing and slicing:

```python
first, rest = seq[0], seq[1:]
```

Two separate operations, and worse, both depend on `seq` being *sliceable* - a list or tuple.
Hand it a generator, a `zip` result, a file object, or any of the lazy iterators that Chapter 241 just made the default in Python 3, and `seq[1:]` fails outright, because those have no slicing.
The head/rest pattern, natural in every functional language, had no natural Python form.

The constraint Python 3.0 (2008, PEP 3132) answered: **let one target in an unpacking absorb "everything else," from any iterable, so destructuring a sequence into fixed and variable parts is a single position-driven assignment.**

This is a two-track chapter.
The assignment and unpacking model - how targets are matched to an iterable, how a starred target's share is computed, how this relates to `*args` in calls - belongs to Deep Volume B.
What this chapter owns is the release: the day a starred assignment target let you split head from tail in one line.

## What shipped

A starred name in an assignment target - `first, *rest = seq` - binds the non-starred names to individual items and the starred name to a *list* of everything left over.
The star can appear anywhere in the target list, and it works on any iterable, not just sliceable sequences.
Listing 244.1 shows the range of it on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- a starred target absorbs 'the rest' as a list ---
  first, *rest = [10,20,30,40] -> first=10, rest=[20, 30, 40]
  first binds one item; *rest collects everything else into a LIST,
  in one assignment. the pre-3.0 form was first, rest = seq[0],
  seq[1:] - two indexings that only work on a sliceable sequence
--- the star can go anywhere: head, tail, or middle ---
  *init, last  -> init=[1, 2, 3], last=4
  head, *mid, tail -> head=1, mid=[2, 3, 4], tail=5
  the starred name takes as many items as are left after the fixed
  targets are filled from both ends. one assignment expresses
  first/last, drop-first, drop-last, and split-the-middle
--- it works on ANY iterable, including un-sliceable ones ---
  from a generator: first_sq=0, other_sqs=[1, 4, 9, 16]
  seq[1:] would fail on a generator (no slicing); starred unpacking
  just consumes the iterator. it is defined on ITERATION, not on
  indexing, so it covers cases the old slice idiom could not
--- the starred target is always a list, even when empty ---
  only, *nothing = [99] -> only=99, nothing=[]
  a, b, *rest2 = [1,2] -> a=1, b=2, rest2=[]
  when there is nothing left, the starred name is an EMPTY list, not
  an error - so head/tail code does not need a length check first
--- a practical use: split a record into key and values ---
  date=2024-01-15, readings avg=12.57
  'the first field is the label, the rest are data' is exactly
  date, *readings = row - the shape of parsing a CSV line, a command
  and its args, a header and its payload
--- the constraint answered ---
  tuple unpacking required an exact count, so head/rest meant manual
  slicing that only worked on sequences. starred targets (3.0) bind
  one part to a list of 'everything else' in a single assignment,
  from any iterable, with the star anywhere. destructuring a sequence
  into fixed and variable parts became one readable line
```

## Why each part answers the constraint

**The head/rest split in one line.**
The first block shows the core: `first, *rest = [10, 20, 30, 40]` binds `first` to `10` and `rest` to `[20, 30, 40]`.
One assignment, and it reads as exactly what it does.
The pre-3.0 `first, rest = seq[0], seq[1:]` needed two indexing operations and a sliceable sequence; the starred form needs neither.

**The star goes anywhere.**
The second block shows the flexibility.
`*init, last` captures everything but the last item; `head, *mid, tail` captures the two ends and the middle.
The starred name takes whatever remains after the fixed targets are filled from both ends, so a single syntax expresses first-and-rest, all-but-last, and first/middle/last.
The pre-3.0 equivalents were a scattered mix of indexing and slicing, each written differently.

**It is defined on iteration, not indexing.**
The third block is the deepest point.
Unpacking a generator - `first_sq, *other_sqs = (x*x for x in range(5))` - works, even though a generator has no `[1:]`.
Starred unpacking is defined in terms of *iteration*, so it consumes any iterable, including the lazy ones that Chapter 241 made pervasive in Python 3.
This is why it is not merely a shorthand for slicing: it covers cases slicing cannot reach at all, and it composes naturally with the iterator-default world 3.0 created.

**The starred target is always a list, even when empty.**
The fourth block covers the edge case that makes the feature safe to use without guards.
`only, *nothing = [99]` binds `nothing` to `[]`, and `a, b, *rest2 = [1, 2]` binds `rest2` to `[]` - an empty list, not an error.
So head/tail code does not need a length check first: the starred name gracefully absorbs zero items when there are none left.

**The practical shape.**
The fifth block shows the pattern in the wild: `date, *readings = row` splits a record into its label and its data fields.
This is the shape of parsing a CSV line into a key and values, a command into a verb and its arguments, a header into its first field and payload.
"The first part is the label, the rest is data" is one of the most common structural operations in real code, and starred unpacking is its direct expression.

## The two-track note

The assignment model - how the interpreter counts fixed targets, computes the starred target's share, iterates the source exactly once, and why exactly one star is allowed per target list - is Deep Volume B's to formalize, along with the symmetry between `*rest` in assignment and `*args` in calls, and the later extension of `*`/`**` into literal displays (`[*a, *b]`, `{**d1, **d2}`).
What the timeline records is the release act: in 3.0, PEP 3132 added the starred assignment target, giving the head/rest destructuring a single, iteration-based form.
The modern consequence, verified above, is that starred unpacking is a standard tool for splitting sequences, works uniformly across lists and lazy iterators, and made a whole category of manual slicing obsolete.

## Where this lands, and the close of the Schism

Extended iterable unpacking is a small syntax with a large reach: it turned the awkward head/rest idiom into a one-line assignment that works on anything you can iterate.
Reach for `first, *rest` to peel off a leading item, `*init, last` to isolate a trailing one, and `label, *data = record` to split a record into its parts - and trust the starred name to be an empty list when there is nothing left.
Deep Volume B explains the unpacking model underneath; this chapter is the record of the release that made destructuring a sequence a single readable line.

This closes Volume 7, The Schism.
The volume's thesis was blunt - *3.0 alone; it did enough* - and these chapters show why one release warranted a whole volume.
Python 3.0 did not add a feature or two; it changed the language's defaults.
Laziness replaced eagerness across the builtins (Chapter 241), closures gained the power to write outward (Chapter 242), signatures gained the power to demand named arguments (Chapter 243), assignment gained the power to destructure variable-length sequences (Chapter 244), and - the change that defined the break and cost a decade of migration - text and bytes were separated (Chapter 7, and Deep Volume D, which follows as the break's actual subject).
Each of these, on its own, would have been a notable release.
Together, in one backward-incompatible version, they were the schism.
Part III continues with Deep Volume D, the text and bytes model that was the whole point of the break, and then Volume 8, the two quiet releases that made Python 3 usable.
