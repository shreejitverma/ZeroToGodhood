# Chapter 257: Unpacking Generalizations

## The constraint

Chapter 244 showed the star on the *left* of an assignment: `first, *rest = seq`.
That was one place `*` could appear, and by 3.4 there were a few others - a single `*args` in a function call, a single `**kwargs` - but the coverage was patchy.
The places `*` and `**` were conspicuously *absent* were exactly the places you most wanted them: inside collection literals, and in calls that draw arguments from more than one source.

The result was that "combine these into a new collection" was always a little procedure rather than an expression.
Merging two lists into a new one meant `a + b`, or `list(a) + list(b)` when they were arbitrary iterables rather than lists.
Merging two dicts meant copying one and updating it: `d = dict(defaults); d.update(overrides)` - two statements, a mutation, and a temporary.
Calling a function with positional arguments from one object and keyword arguments from another meant assembling temporaries, and unpacking *two* iterables into one call was simply not allowed.

The constraint Python 3.5 (2015, PEP 448) answered: **let `*` and `**` appear wherever a collection is built - inside list, set, dict, and tuple literals, and in calls with multiple unpackings - so combining iterables or mappings is a literal expression rather than a copy-and-update procedure.**

This is a two-track chapter.
The call grammar and the display (literal) grammar - how arguments bind, how literals are constructed - belong to Deep Volume B.
What this chapter owns is the release: the day unpacking became available everywhere a collection is assembled.

## What shipped

Listing 257.1 shows `*` in list/set literals, `**` in dict literals, both in function calls, and multiple unpackings in one call, on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- * inside a list/tuple/set literal merges iterables ---
  [*a, *b] : [1, 2, 3, 4, 5]
  [0, *a, 99, *b] (interleave with literals) : [0, 1, 2, 3, 99, 4, 5]
  {*a, *b} (a set)  : [1, 2, 3, 4, 5]
  before 3.5 this was a + b, or list(a)+list(b) for mixed iterables.
  now the * splices any iterable straight into a new literal, mixed
  freely with individual elements - one expression, a NEW collection
--- ** inside a dict literal merges mappings ---
  {**defaults, **overrides} : {'color': 'black', 'size': 'L', 'tag': 'new'}
  later keys WIN: size='L' from overrides beat size='M'. this is the
  merge that used to be d=dict(defaults); d.update(overrides) - now a
  single expression that builds a new dict without mutating either
--- ** with extra literal keys, in one expression ---
  {**defaults, 'shipping': 'express', **overrides} : {'color': 'black', 'size': 'L', 'shipping': 'express', 'tag': 'new'}
  you can interleave unpacked mappings and explicit key:value pairs,
  applied left to right, so building a config from a base plus
  additions plus overrides is one readable literal
--- * and ** in a function CALL, from multiple sources ---
  connect(*address, **options) : db.local:5432 timeout=30 retries=3
  *address supplies the positional args, **options the keyword args,
  from two separate objects - no temporary, no manual spreading. the
  call site assembles its arguments from wherever they live
--- multiple unpackings in ONE call (the part 3.5 newly allowed) ---
  total(*first, *second, 10) : 20
  pre-3.5 a call could unpack only ONE iterable; 3.5 allowed several,
  mixed with literals. total(*first, *second, 10) sums 1+2+3+4+10
--- the idioms it replaced, side by side ---
  merge lists : a + b            -> [*a, *b]        = [1, 2, 3, 4, 5]
  merge dicts : copy+update      -> {**d1, **d2}    = {'color': 'black', 'size': 'L', 'tag': 'new'}
  the old forms still work, but the unpacking literals say 'a NEW
  collection combining these' directly, without a mutation step or a
  helper - which is why they became the idiomatic way to merge
--- the constraint answered ---
  * and ** existed for assignment and single-call unpacking, but not
  inside literals or multi-source calls. PEP 448 (3.5) generalized
  them: [*a, *b], {**d1, **d2}, f(*a, *b, **kw). combining iterables
  or mappings into a new collection became a literal expression, not
  a copy-and-update procedure
```

## Why each part answers the constraint

**`*` splices iterables into literals.**
The first block shows `[*a, *b]` merging two lists, `[0, *a, 99, *b]` interleaving unpacked iterables with individual elements, and `{*a, *b}` building a set.
The `*` splices *any* iterable straight into a new literal, mixed freely with literal elements.
The old `a + b` worked only for same-type sequences; `[*a, *b]` works for any iterables and reads as "a new list combining these."

**`**` merges mappings with last-wins.**
The second block shows `{**defaults, **overrides}` producing a merged dict where later keys win - `size` is `'L'` from `overrides`, not `'M'` from `defaults`.
This is the merge that used to require `d = dict(defaults); d.update(overrides)` - two statements and a mutation - now a single expression that builds a new dict without touching either input.

**Literal keys interleave with unpacked mappings.**
The third block shows `{**defaults, "shipping": "express", **overrides}` mixing unpacked mappings with explicit `key: value` pairs, applied left to right.
Building a dict from a base, plus some additions, plus some overrides is one readable literal, with the last-wins rule resolving conflicts in written order.

**Calls assemble arguments from multiple sources.**
The fourth block shows `connect(*address, **options)`: the positional arguments come from a list, the keyword arguments from a dict, two separate objects spread into one call with no temporary.
The call site assembles its arguments from wherever they happen to live.

**Multiple unpackings in one call.**
The fifth block shows the specific capability 3.5 newly allowed: `total(*first, *second, 10)` unpacks *two* iterables and a literal into one call.
Before 3.5 a call could unpack only a single iterable; PEP 448 removed that limit, so arguments can be gathered from any number of sources in one expression.

**The idioms it replaced.**
The sixth block places the old and new forms side by side.
`a + b` becomes `[*a, *b]`; copy-and-update becomes `{**d1, **d2}`.
The old forms still work, but the unpacking literals state the intent - "a new collection combining these" - directly, without a mutation step or a helper, which is why they became the idiomatic way to merge.

## The two-track note

The grammar - how the interpreter constructs a literal with spliced iterables, how a call binds arguments gathered from multiple unpackings, why the dict-merge is last-wins - is Deep Volume B's to formalize, and it connects to the argument model of Chapter 243 and the assignment-side star of Chapter 244.
What the timeline records is the release act: in 3.5, PEP 448 generalized `*` and `**` to literals and multi-source calls.
The modern consequence, verified above, is that `[*a, *b]`, `{**d1, **d2}`, and `f(*a, *b, **kw)` are everyday idioms - so much so that the later dedicated dict-merge operator `|` (3.9) built on the same intuition, and the unpacking literals remain the general tool for combining any iterables or mappings.

## Where this lands

Unpacking generalizations turned collection-combining from a procedure into an expression.
Reach for `[*a, *b]` (or `{*a, *b}`, `(*a, *b)`) to merge iterables into a new collection, `{**d1, **d2}` to merge mappings with last-wins precedence, and `f(*args, **kwargs)` - now from as many sources as you like - to assemble a call.
Prefer these to `+`-with-copies and copy-then-update whenever you want a *new* collection and clear intent; the unpacking literals say what you mean and never mutate their inputs.
Deep Volume B explains the grammar underneath; this chapter is the record of the release that let unpacking appear wherever a collection is built.
