# Chapter 236: OrderedDict

## The constraint

For twenty years, a Python dictionary was *unordered* - and this was not an accident of implementation but a documented property.
Iterating a dict gave its keys in an arbitrary, implementation-defined sequence, and any program that relied on that order was relying on a bug waiting to bite.
The hash table underneath placed keys wherever their hashes landed, and that placement had nothing to do with the order you inserted them.

But order matters more often than the unordered dict admitted.
Configuration sections should serialize in file order.
A table's columns should appear as declared.
An undo history is meaningless if its steps come back shuffled.
Whenever the order of keys carried meaning, the pre-2.7 programmer had to maintain it *separately* - a parallel list of keys beside the dict, kept in sync by hand, consulted whenever iteration order mattered.
It worked, and it was tedious and error-prone, and it scattered "order matters here" across two data structures that had to agree.

The constraint Python 2.7 (2010) answered was this: **make "this dictionary's order is meaningful" expressible as a single type, so the parallel key-list disappears.**

This is a two-track chapter.
The hash-table internals - how a dict stores keys, how the ordered variant threads a linked list through the entries, how the 3.6/3.7 compact-dict redesign made ordering essentially free - belong to Deep Volume Q (dict and set internals).
What this chapter owns is the release: the day ordering became a property a dictionary type could carry, and the long arc by which that idea became the language default.

## What shipped

Python 2.7 added `collections.OrderedDict`: a dict subclass that remembers the order in which keys were first inserted, and iterates them in that order.
Listing 236.1 shows its original purpose, the modern twist that ordinary dicts now share it, and the operations that still make `OrderedDict` distinct, on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- OrderedDict remembers insertion order (its original purpose) ---
  inserted gamma, alpha, beta -> keys: ['gamma', 'alpha', 'beta']
  the keys come back in INSERTION order, not sorted, not arbitrary.
  before 2.7 you kept a separate [gamma, alpha, beta] list beside
  the dict to remember this; OrderedDict folded that into the type
--- the modern consequence: plain dict is ALSO ordered since 3.7 ---
  plain dict keys : ['gamma', 'alpha', 'beta']
  since Python 3.7 the ordinary dict preserves insertion order by
  LANGUAGE GUARANTEE - the idea OrderedDict introduced became the
  default. so for plain 'keep insertion order', a dict now suffices
--- what OrderedDict still gives that a plain dict does not ---
  move_to_end('a') -> ['b', 'c', 'a']
  move_to_end('c', last=False) -> ['c', 'b', 'a']
  popitem(last=False) popped the front : ('c', 3)
  move_to_end() and popitem(last=...) are order-EDITING operations a
  plain dict has no equivalent for. an LRU cache is exactly this:
  move touched keys to the end, evict from the front
--- order-sensitive equality: the other real difference ---
  plain {a,b} == plain {b,a} : True  (order ignored)
  Ordered {a,b} == Ordered {b,a} : False  (order matters)
  plain dicts compare equal regardless of order; two OrderedDicts
  compare equal only if their ORDER also matches. when order is part
  of the meaning (a sequence of steps), that stricter equality is
  the correct one - the remaining reason to choose OrderedDict
--- the constraint answered ---
  a dict was defined as unordered, so 'preserve order' meant a
  parallel list. 2.7's OrderedDict made order a property of the type;
  the idea proved so right that 3.7 made every dict ordered. today
  OrderedDict remains for order-editing (move_to_end) and
  order-sensitive equality - the parts ordering-as-default did not
  absorb
```

## Why each part answers the constraint

**Order becomes a property of the type.**
The first block shows the original win: insert `gamma`, `alpha`, `beta` and get exactly that order back on iteration - not sorted, not arbitrary.
The parallel key-list that pre-2.7 code maintained by hand is now internal to the type.
"Order matters here" is expressed by choosing `OrderedDict` instead of `dict`, in one place, and the type keeps the two facts - the mapping and its order - in sync for you.

**The idea won so completely it became the default.**
The second block is the modern twist, and it is the reason this is a timeline chapter rather than just a stdlib note.
Since Python 3.7, the *ordinary* dict preserves insertion order by language guarantee - a consequence of the 3.6 compact-dict redesign that made ordering a free side effect of a more memory-efficient layout, promoted to a guarantee in 3.7.
The concept `OrderedDict` introduced in 2.7 was so obviously right that the language absorbed it into the base type.
So for the plain need - "iterate in insertion order" - a regular dict now suffices, and the parallel-list problem is gone from the language entirely.

**What still distinguishes OrderedDict: order editing.**
The third block shows the operations a plain dict, even an ordered one, still lacks.
`move_to_end(key)` relocates an existing key to the back (or, with `last=False`, to the front), and `popitem(last=False)` removes from the front rather than the back.
These are order-*editing* operations, and they have no plain-dict equivalent.
The canonical use is an LRU cache: on access, `move_to_end` the touched key so the recently-used stay at the back; when full, `popitem(last=False)` evicts the least-recently-used from the front.
That is precisely how `functools.lru_cache` and countless hand-rolled caches are structured.

**And order-sensitive equality.**
The fourth block shows the other genuine difference.
Two plain dicts with the same pairs are equal regardless of key order - `{"a":1,"b":2} == {"b":2,"a":1}` is `True`.
Two `OrderedDict`s are equal only if their *order* also matches - the same comparison is `False`.
When the order is part of the meaning - a sequence of pipeline stages, an ordered set of rules - that stricter equality is the correct one, and it is a reason to reach for `OrderedDict` even in a world where plain dicts are ordered.

## The two-track note

The internals - how the original `OrderedDict` threaded a doubly linked list through its entries, how the 3.6 compact dict reorganized storage so insertion order fell out for free, why that made the 3.7 guarantee cheap to promise - are Deep Volume Q's to develop.
What the timeline records is the conceptual milestone: in 2.7, ordering became a property a dictionary could carry, replacing the hand-maintained parallel list; and by 3.7, the idea had graduated into the base `dict`.
The modern consequence, verified above, is that plain dicts now cover the common case, and `OrderedDict` has narrowed to its genuinely distinct capabilities - order editing and order-sensitive equality - which is a healthy outcome, not a demotion.

## Where this lands

`OrderedDict` is a small feature with an unusually clean arc: it named a need the base type had ignored for twenty years, proved the need was universal, and then watched the language adopt its idea wholesale.
Reach for a plain dict when you just want insertion order preserved - since 3.7 that is guaranteed.
Reach for `OrderedDict` when you need to *reorder* entries (`move_to_end`, front-popping) or when order-sensitive equality is the correct semantics.
Deep Volume Q explains why ordering became cheap enough to make default; this chapter is the record of the release that first made a dictionary's order something you could count on.
