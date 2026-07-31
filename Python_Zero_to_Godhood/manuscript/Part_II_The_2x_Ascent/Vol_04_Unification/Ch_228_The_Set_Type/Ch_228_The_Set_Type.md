# Chapter 228: The Set Type

## The constraint

Python 2.3 (2003) shipped under a constraint that had gone unspoken for a decade: the language had no first-class way to say "a collection of unique things you test membership on."
Every Python programmer needed it constantly - "have I seen this ID?", "which tickers appear in both files?", "unique words in this document" - and every Python programmer faked it the same way, with a dictionary mapping each key to a throwaway value:

```python
seen = {}
seen[item] = 1        # the item is the key; the 1 is meaningless
if item in seen:      # membership test = dict lookup
    ...
```

It worked because a dict already gave O(1) membership by hashing its keys.
But it was a fake: it wasted a value slot per element, it offered none of the algebra that makes sets useful (no union, no intersection, no difference), and it read as a dictionary, so the next person had to infer from the meaningless `1`s that you meant a set.
The constraint 2.3 answered was this: **make the right container for uniqueness-and-membership a builtin, with the algebra of sets as operators, so the correct data structure is a name and not a workaround.**

This is a two-track chapter.
It owns no mechanism - the hashing, the open-addressing table, the load-factor policy that make membership O(1) all belong to Deep Volume Q (the dict and set internals), and the cost model that says "use a set for membership" belongs to Chapter 88.
What this chapter owns is the release: the moment the container Chapter 88 points at became a builtin type you could just name.

## What shipped

`set` (and its immutable sibling `frozenset`) became builtin types in Python 2.3.
Two years later, Python 2.4 added the literal and comprehension syntax (`{1, 2, 3}` and `{x for x in ...}`) that we use today.
The type gave three things the dict-hack could not: uniqueness by construction, membership in O(1), and set algebra as operators.

Listing 228.1 demonstrates all three on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- a set: unique elements, O(1) membership ---
  {3,1,2,2,3,1} -> [1, 2, 3]  (duplicates gone)
  3 in s : True  (O(1) - a hash lookup, not a scan)
  9 in s : False
  uniqueness is by CONSTRUCTION (adding a duplicate is a no-op) and
  membership is O(1) (a hash probe) - the two properties a 'set of
  things you test membership on' needs (Chapter 88's cost model)
--- set algebra as operators ---
  a | b (union)        : [1, 2, 3, 4, 5, 6]
  a & b (intersection) : [3, 4]
  a - b (difference)   : [1, 2]
  a ^ b (symmetric diff): [1, 2, 5, 6]
  {1,2} <= a (subset)  : True
  the algebra of sets - union, intersection, difference, subset -
  as operators. 'which symbols are in both portfolios' is a & b,
  not a nested loop (Chapter 88's 5000x membership win)
--- the pre-2.3 workaround, and why the type is better ---
  dict-as-set keys : [1, 2, 3]  (the pre-2.3 fake)
  real set         : [1, 2, 3]  (the 2.3 type)
  the dict-as-set worked but wasted a value per key, gave no set
  algebra, and read as a dict. a real type is smaller, has |&-^,
  and SAYS what it is - which is why the builtin mattered
--- the membership performance point (Chapter 88, in miniature) ---
  9999 in list  : True  (scans up to 10000 items)
  9999 in set   : True  (one hash probe)
  SAME result, wildly different cost: 'x in list' inside a loop is
  the accidental quadratic (Chapter 87), and 'convert to a set
  first' is the single highest-leverage line-level fix in Python
--- frozenset: the immutable, hashable set ---
  frozenset can be a dict key/set member : True
  a set is mutable and thus unhashable; frozenset is the immutable
  version you can put IN a set or use as a key (Deep A's hashability
  rule: mutable means unhashable)
--- the constraint answered ---
  before 2.3, 'unique collection + fast membership' was a dict
  hack with no algebra. the set type made the right container a
  builtin, so Chapter 88's advice ('use a set for membership') is
  a one-liner, not a workaround. the container IS the cost model
```

## Why each part answers the constraint

**Uniqueness by construction.**
The constraint asked for "a collection of unique things."
A set delivers that as an invariant, not a discipline: `{3, 1, 2, 2, 3, 1}` collapses to `{1, 2, 3}` at construction, and adding an element already present is a silent no-op.
You never write the "is it already here?" guard, because the type is the guard.
The dict-hack gave the same uniqueness but forced you to remember that the values were meaningless; the set makes the meaning the type.

**Membership in O(1).**
The constraint asked for "things you test membership on."
`3 in s` is a single hash probe, not a scan - the same cost model as a dict key lookup, because it is the same table underneath (Deep Q).
The listing's final section shows the point at the scale where it bites: `9999 in big_list` scans up to 10,000 elements, `9999 in big_set` does one probe, and the two return the identical answer.
Put that list membership inside a loop and you have written the accidental quadratic of Chapter 87; "convert to a set first" is, as Chapter 88 measures, the single highest-leverage line-level fix in everyday Python.
The set type is what makes that fix a one-liner instead of a data-structure rewrite.

**Set algebra as operators.**
This is the part the dict-hack could never give.
"Which tickers are in both portfolios" is `a & b`.
"Everything in either" is `a | b`.
"In the first but not the second" is `a - b`.
These are single operators over the whole collection, replacing the nested loop you would otherwise write - and the nested loop is exactly Chapter 88's 5000x membership case wearing a different hat.
The algebra is not a convenience bolted onto a membership structure; it is half the reason the mathematical concept of a set is worth having as a type at all.

**frozenset closes the hashability loop.**
A `set` is mutable, and Deep Volume A's rule is absolute: mutable means unhashable, because an object whose hash could change mid-life would get lost in its own table.
So a set cannot be a dict key or an element of another set.
`frozenset` is the immutable version that can - the same relationship `tuple` has to `list`.
The listing uses one as a dict key to prove it.
This is not a footnote: "a set of sets" and "a dict keyed by a set of tags" are real needs, and `frozenset` is what makes them expressible without violating the hashing contract.

## The two-track note

Everything about *why* membership is O(1) - the hash function, the open-addressing probe sequence, the resize policy that keeps the load factor low - is Deep Volume Q's to explain, and this chapter deliberately does not.
The cost model that turns "it's O(1)" into the practical rule "reach for a set the moment you test membership more than once" is Chapter 88's.
What the timeline owns is the release fact: in 2003, that container stopped being something you assembled out of a dictionary and became a builtin you name directly.
The modern consequence, verified byte-for-byte above, is that the single most common real performance bug in Python - membership-testing against a list in a loop - has a fix that is one word long, and that word has been a builtin since 2.3.

## Where this lands

The set type is the quiet workhorse of the standard library's data model.
Every time you deduplicate with `set(items)`, test membership with `in`, or intersect two collections with `&`, you are using the 2.3 release that turned a dictionary workaround into a named type.
Chapter 88 tells you when to reach for it; Deep Volume Q tells you why it is fast; this chapter is the record of the day it arrived.
The lesson of the release is the one the two-track structure keeps returning to: the right container is not an optimization you apply to working code - it is a decision you make when you name the data, and Python 2.3 is when the naming became possible.
