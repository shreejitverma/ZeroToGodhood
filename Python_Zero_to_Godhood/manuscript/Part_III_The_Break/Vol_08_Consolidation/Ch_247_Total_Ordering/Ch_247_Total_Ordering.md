# Chapter 247: Total Ordering

## The constraint

To make a class fully orderable in Python - usable with `<`, `<=`, `>`, `>=`, `==`, `!=`, and with `sorted()`, `min()`, and `max()` - the data model asks you to implement the rich-comparison methods: `__lt__`, `__le__`, `__gt__`, `__ge__`, and `__eq__` (with `__ne__` derived from `__eq__` automatically).
That is up to six methods, and they must all agree with one another.

Writing them by hand is tedious, and worse, it is a place for a specific and nasty kind of bug.
The six comparisons encode one underlying order, but nothing checks that your six implementations are *mutually consistent*.
Get `__le__` subtly wrong - a stray `<` where you meant `<=`, an inverted condition - and you have a type where `a <= b` and `a > b` can both be true, or where `sorted()` produces an order that depends on the initial arrangement.
These bugs are painful to trace precisely because the methods look independently correct; the fault is in their disagreement.

The constraint Python 3.2 (2011) answered: **let a class declare a full ordering from a minimal, single source of truth, so the four ordering operators are derived consistently rather than hand-maintained.**

This is a two-track chapter.
The comparison protocol - what the rich-comparison methods are, how `sorted` and `min`/`max` use them, reflected operations and `NotImplemented` - belongs to Deep Volume B.
What this chapter owns is the release: the day `@total_ordering` reduced a fully ordered type from six methods to two, with consistency guaranteed.

## What shipped

`functools.total_ordering` is a *class* decorator.
Define `__eq__` and exactly one ordering method (say `__lt__`), and the decorator supplies the other three ordering methods (`__le__`, `__gt__`, `__ge__`), derived from the two you wrote.
Listing 247.1 shows a `Version` type ordered by `(major, minor)` with only `__eq__` and `__lt__` written, on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- we defined only __eq__ and __lt__; the rest are derived ---
  a=v1.4, b=v2.0, c=v1.4
  a <  b : True   (defined)
  a <= c : True   (DERIVED from __lt__ and __eq__)
  b >  a : True   (DERIVED)
  b >= a : True   (DERIVED)
  a == c : True   (defined)
  a != b : True   (from __eq__)
  @total_ordering filled in <=, >, >= from the __lt__ and __eq__ we
  wrote. all six operators, two method definitions
--- the derived operators are present on the class ---
  Version defines __lt__ : True
  Version defines __le__ : True
  Version defines __gt__ : True
  Version defines __ge__ : True
  the decorator ADDED __le__/__gt__/__ge__ to the class; we wrote
  only __lt__. they are real methods, derived once at class creation
--- it just works with sorted(), min(), max() ---
  unsorted : [v2.0, v1.4, v1.10, v1.2]
  sorted   : [v1.2, v1.4, v1.10, v2.0]
  min      : v1.2
  max      : v2.0
  sorting and min/max only need a consistent ordering, which the
  derived operators provide. note v1.10 > v1.4 because we order by
  the (major, minor) TUPLE, not by string - the __lt__ we chose
--- the consistency guarantee: no hand-maintained contradictions ---
  a < b and b > a agree : True
  a <= c and c >= a agree : True
  because all four ordering ops come from ONE __lt__, they cannot
  disagree. hand-writing six methods risks a typo that makes <= and
  > contradict each other - the decorator removes that whole class
  of bug
--- the constraint answered ---
  a fully ordered type needed six rich-comparison methods, tedious
  to write and easy to make inconsistent. @total_ordering (3.2)
  derives four of them from __eq__ plus one ordering method, so a
  sortable type is two definitions with consistency guaranteed -
  Deep B's comparison protocol, minus the boilerplate
```

## Why each part answers the constraint

**Six operators from two definitions.**
The first block shows the win directly.
`Version` defines only `__eq__` and `__lt__`, yet all six comparisons work: `<` and `==` are the ones we wrote, `!=` comes from `__eq__` as always, and `<=`, `>`, `>=` are *derived* by the decorator.
Two method definitions cover the full ordering surface.

**The derived methods are real.**
The second block confirms the derivation is concrete: `__le__`, `__gt__`, and `__ge__` are present in the class after decoration, even though the source defined only `__lt__`.
`@total_ordering` adds them as real methods at class-creation time - it is not runtime trickery, it is code generation from your single ordering method.

**It works with the ordering builtins.**
The third block shows the practical payoff: `sorted`, `min`, and `max` all work on `Version` instances, because those functions need only a consistent ordering, which the derived operators provide.
The block also makes a correctness point worth noting: `v1.10` sorts *after* `v1.4` because the type orders by the `(major, minor)` integer tuple, not by string - a reminder that the *choice* of `__lt__` is yours, and `total_ordering` faithfully propagates whatever order you defined.

**Consistency is the deeper guarantee.**
The fourth block states the reason this decorator matters beyond saving keystrokes.
Because all four ordering operators derive from the *one* `__lt__`, they cannot contradict each other: `a < b` and `b > a` necessarily agree, as do `a <= c` and `c >= a`.
Hand-writing six methods risks the typo that makes `<=` and `>` disagree - a bug that surfaces as mysterious sorting misbehavior.
`@total_ordering` removes that entire class of bug by construction, which is a stronger promise than "less code."

## The two-track note

The comparison protocol - the full set of rich-comparison methods, how Python dispatches `a < b` to `a.__lt__(b)` and falls back to the reflected `b.__gt__(a)`, the role of `NotImplemented`, how `sorted` and `min`/`max` consume the order - is Deep Volume B's to develop.
`total_ordering` is a convenience built on that protocol, and it has a known trade-off Deep B can situate: the derived methods add a small call-indirection overhead, so a performance-critical type that is compared in a tight inner loop may still want all six written by hand.
What the timeline records is the release act: in 3.2, `functools.total_ordering` made a fully ordered type a two-method declaration with guaranteed internal consistency.
The modern consequence, verified above, is that defining an orderable type is routine and low-risk - and that `dataclasses` (Part V) later folded the same idea in with `order=True`, generating consistent comparisons from the fields directly.

## Where this lands

`total_ordering` is a small, sharp consolidation: it took a six-method chore with a built-in consistency hazard and reduced it to `__eq__` plus one ordering method.
Reach for it whenever you write a class that needs to sort or compare - versions, money, coordinates, priorities - and define `__eq__` and `__lt__` in terms of a single key (often a tuple), letting the decorator supply the rest.
Consider writing all six by hand only when profiling shows the comparison overhead matters, or reach for `@dataclass(order=True)` when the order is just "compare the fields in order."
Deep Volume B explains the comparison protocol underneath; this chapter is the record of the release that made a consistent, fully ordered type two definitions instead of six.
