# Chapter 284: Copy Replace

## The constraint

Working with immutable objects means you never mutate them - you build a *new* object that differs in a few fields.
This "functional update" is the core operation of immutable-style code, and Python had accumulated a different spelling of it for every type.

Dataclasses had `dataclasses.replace(obj, field=value)`.
Named tuples had `obj._replace(field=value)`.
`datetime` objects had `obj.replace(year=...)`.
Each did the same thing - copy the object with some fields changed - under a different name, with a different call convention.
And a *custom* immutable class had no standard story at all: you wrote your own `with_field` methods or a bespoke `replace`, and generic code that wanted to "copy this object with changes" had to know exactly which kind of object it held.

The constraint Python 3.13 (2024) answered: **give "copy with these fields changed" one standard function across types** - a single `copy.replace(obj, **changes)` that dispatches through a `__replace__` protocol any type can implement.

This chapter owns no Deep-Volume mechanism; it is a standard-library unification built on ordinary method dispatch.
What it owns is the release: the day functional update got one spelling.

## What shipped

`copy.replace(obj, **changes)` returns a copy of `obj` with the named fields changed, by calling `obj.__replace__(**changes)`.
Dataclasses and `datetime` types gained `__replace__` automatically, and any custom type can opt in by defining it.
Listing 284.1 shows this on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- copy.replace() returns a NEW object with some fields changed ---
  base : Config(host='localhost', port=8000, debug=False)
  prod : Config(host='prod.example.com', port=443, debug=False)
  base is unchanged : True
  copy.replace(base, host=..., port=...) built a NEW Config with those
  fields overridden and the rest copied. the original is untouched -
  the functional-update pattern immutable code lives on
--- unspecified fields are carried over unchanged ---
  copy.replace(base, debug=True) : Config(host='localhost', port=8000, debug=True)
  host and port copied from base : True
  you name only what changes; everything else is inherited from the
  original. that is what makes it ergonomic for objects with many
  fields where you want to tweak one
--- it works on datetime, which grew __replace__ ---
  date 2024-01-15 with year=2025 : 2025-01-15
  datetime.date already had a .replace() method; in 3.13 it also
  supports copy.replace(), so the same generic function works on it -
  the point of a unifying protocol
--- custom types opt in by defining __replace__ ---
  original  : Money(100, 'USD')
  amount=80 : Money(80, 'USD')
  to EUR    : Money(92, 'EUR')
  Money defined __replace__(self, **changes) returning a new Money.
  now copy.replace() works on it exactly like on a dataclass - any
  immutable type joins the protocol by implementing one method
--- the standard-across-types payoff ---
  dataclasses.replace(cfg, ...), nt._replace(...), dt.replace(...) were
  three different spellings. copy.replace(obj, ...) is ONE, dispatching
  through __replace__ - so generic code can 'copy-with-changes' any
  supporting object without knowing which kind it is
--- the constraint answered ---
  immutable-object updates needed a per-type replace method with a
  different name for each type, and no story for custom classes.
  copy.replace() + __replace__ (3.13) unified it: one function that
  copies an object with named fields changed, for dataclasses,
  datetime, and any type that opts in. functional update, standardised
```

## Why each part answers the constraint

**Copy with changes, original untouched.**
The first block shows `copy.replace(base, host="prod.example.com", port=443)` building a new `Config` with those fields overridden while `base` stays unchanged.
This is the functional-update pattern - the operation immutable code performs constantly - now available through one standard function.

**Unspecified fields carry over.**
The second block shows the ergonomic property: `copy.replace(base, debug=True)` changes only `debug` and copies `host` and `port` from the original.
You name only what changes, and everything else is inherited - which is what makes this pleasant for objects with many fields where you want to tweak one or two.

**It works on datetime.**
The third block shows `copy.replace` on a `datetime.date`: `copy.replace(d, year=2025)` moves the year while keeping month and day.
`date` already had its own `.replace()` method, but in 3.13 it also supports the generic `copy.replace` - which is the entire point of a unifying protocol: the same function works across types that previously each had their own method.

**Custom types opt in.**
The fourth block shows a custom immutable `Money` class implementing `__replace__(self, **changes)` to return a new `Money`.
Once it does, `copy.replace(price, amount=80)` works on it exactly as on a dataclass.
Any immutable type joins the protocol by implementing one method - so custom classes finally have a standard functional-update story, not a bespoke one.

**One spelling for generic code.**
The fifth block states the payoff.
`dataclasses.replace`, `nt._replace`, and `dt.replace` were three different spellings; `copy.replace` is one, dispatching through `__replace__`.
This means *generic* code can "copy-with-changes" any supporting object without knowing which kind it is - a serializer, a builder, a state machine can call `copy.replace` on whatever immutable objects it is handed.

## The two-track note

There is no language mechanism here to defer to a Deep Volume; `copy.replace` is a small function plus a dunder protocol, built on ordinary method dispatch.
What the timeline records is the release act: in 3.13, `copy.replace` and `__replace__` unified functional update across dataclasses, `datetime`, and any opting-in type.
The modern consequence, verified above, is that "copy this object with these fields changed" is one function call regardless of the object's type, and immutable-style code - increasingly common as dataclasses and frozen types spread - has a standard, type-agnostic tool for its core operation.

## Where this lands

`copy.replace` is a small unification with real value for immutable-style code.
Reach for it whenever you need a modified copy of an immutable object - a config with one setting changed, a date with one field moved, a value object with one attribute updated - and prefer it to the per-type methods when you want code that works across types.
Implement `__replace__` on your own immutable classes to make them first-class participants.
The original is always left untouched, which is exactly the guarantee immutable code depends on.
No Deep Volume owns a copy mechanism; this chapter is the record of the release that gave functional update one standard spelling.
