# Chapter 253: Singledispatch

## The constraint

Some functions must behave differently depending on the *type* of their argument.
A serializer formats an `int` one way, a `list` another, a custom object a third.
A pretty-printer, a converter, a validator - all commonly branch on type.
The default way to write this in Python is an `isinstance` ladder:

```python
def describe(value):
    if isinstance(value, int):
        ...
    elif isinstance(value, list):
        ...
    elif isinstance(value, str):
        ...
    else:
        ...
```

This has two problems, and the second is the serious one.
First, one function now knows about every type it handles, growing without bound.
Second, and worse: to support a *new* type, you must *edit this function*.
That violates the open/closed principle - a design should be open for extension but closed for modification - and it means a library's dispatch function cannot be extended by its users at all, because they cannot edit the library's source.

The constraint Python 3.4 (2014, PEP 443) answered: **invert the structure - let a function be a base implementation plus a set of separately-registered per-type implementations, so dispatch is automatic and a new type is added by registering, not by editing.**

This is a two-track chapter.
The type model dispatch relies on - how a type relates to its bases, the method resolution order that decides which registration matches - belongs to Deep Volume C.
What this chapter owns is the release: the day single-dispatch generic functions became a standard-library tool.

## What shipped

`functools.singledispatch` turns a function into a *generic function*: you write a base implementation, then register type-specific implementations with `@base.register`.
Dispatch on the first argument's type is automatic, respects inheritance, and the registry is inspectable.
Listing 253.1 shows it on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- one call site, implementation chosen by the argument's TYPE ---
  describe(42) -> the integer 42 (even=True)
  describe([1, 2, 3]) -> a list of 3 items
  describe('hi') -> the text 'hi' (2 chars)
  describe(3.14) -> a float: 3.14
  describe() dispatched on the type of its first argument: int, list,
  and str hit their registered functions; float fell through to the
  base. no isinstance ladder - the registry does the routing
--- adding a new type does NOT touch existing implementations ---
  after registering dict: describe({'b':2,'a':1}) -> a dict with keys ['a', 'b']
  a brand-new case was added by registering ONE function. the int,
  list, str, and base implementations were never edited - open for
  extension, closed for modification (the open/closed principle)
--- dispatch respects inheritance: base registration serves subclasses ---
  describe(Celsius(21.0)) -> some number: 21.0
  Celsius has no registration of its own, but it IS a Number, so the
  Number implementation handles it. registering a base class covers
  its whole subtree (Deep C's MRO decides the match)
--- the registry is inspectable ---
  types with a specific implementation : ['Number', 'dict', 'int', 'list', 'str']
  describe.registry maps each registered type to its function, and
  'object' is the base fallback. the dispatch table is data you can
  read, not a buried if/elif chain
--- the constraint answered ---
  type-varying behaviour meant an isinstance ladder in one function
  you had to edit for every new type. singledispatch (3.4) turns it
  into a base function plus per-type registrations: dispatch is
  automatic, inheritance-aware, and extensible without editing
  existing code - overloading by type, the standard-library way
```

## Why each part answers the constraint

**Automatic dispatch on the first argument's type.**
The first block shows the routing: `describe(42)` hits the `int` implementation, `describe([1,2,3])` the `list` one, `describe("hi")` the `str` one, and `describe(3.14)` - which has no registration - falls through to the base function.
There is no `isinstance` ladder in the source; the registry routes each call to the right implementation based on the first argument's type.
The registration can name the type via an annotation (`def _(value: int)`) or explicitly (`@describe.register(str)`).

**Extension without modification.**
The second block is the core payoff.
Support for `dict` is added by registering *one new function* - and the `int`, `list`, `str`, and base implementations are never touched.
This is the open/closed principle made concrete: the generic function is open for extension (register more types) and closed for modification (existing implementations stay put).
Critically, this works across module boundaries - a user of a library can register an implementation for the library's generic function without editing the library.

**Inheritance-aware dispatch.**
The third block shows that dispatch respects the type hierarchy.
`Celsius`, a subclass of `float`, has no registration of its own, but it *is* a `Number`, so the `Number` implementation handles it.
Registering a base class covers its entire subtree, and when multiple registrations could match, the method resolution order (Deep Volume C) decides which is most specific.
This is what makes single dispatch a real type-based mechanism rather than an exact-type lookup.

**The registry is data.**
The fourth block shows `describe.registry` - the mapping from registered type to implementation - is inspectable, with `object` as the base fallback.
The dispatch table is readable data, not logic buried in an `if`/`elif` chain, which makes the generic function's behavior discoverable and testable.

## The two-track note

The type machinery dispatch depends on - the method resolution order, how the most-specific registration is chosen when several apply, how abstract base classes (Chapter 235) participate as registerable types - is Deep Volume C's to develop.
What the timeline records is the release act: in 3.4, `functools.singledispatch` made single-dispatch generic functions a standard tool, later joined by `singledispatchmethod` (3.8) for methods.
The modern consequence, verified above, is that type-based function overloading is a registration exercise rather than an `isinstance` ladder, and that it is extensible by third parties - the property that makes it valuable for library design.

## Where this lands

`singledispatch` is Python's answer to type-based overloading, done in a way that fits a dynamic, duck-typed language: not compile-time method resolution, but a runtime registry that respects inheritance and stays open to extension.
Reach for it when a function's behavior genuinely varies by the type of its first argument and you want new types to be addable without editing existing code - serializers, formatters, converters, visitors.
Prefer it to an `isinstance` ladder whenever extensibility matters; keep a simple `if`/`elif` when the set of types is small, fixed, and private.
Deep Volume C explains the dispatch machinery; this chapter is the record of the release that made overloading by type a standard-library tool.
