# Chapter 285: Deprecated

## The constraint

Deprecating an API is a communication problem with *two* audiences.
You need to tell users "this still works, but stop using it" at **runtime** - a `DeprecationWarning` when they call the deprecated thing, so a running program flags it in logs and test output.
And you need to tell them at **check time** - a static warning in their editor and CI, so they see it *before* the code runs, while they are writing the call.

Before Python 3.13, these were two disconnected mechanisms.
For the runtime warning, you hand-wrote a `warnings.warn(..., DeprecationWarning)` call inside the function body.
For the static signal, you wrote a docstring note (which no tool enforces) or reached for a type-checker-specific convention.
The two could drift: a function might warn at runtime but not be flagged statically, or vice versa, and keeping them in sync was manual work.

The constraint Python 3.13 (2024, PEP 702) answered: **one marker for both audiences** - a single decorator that emits the runtime warning *and* is understood by type checkers.

This is a two-track chapter.
The type system that reads the marker statically is Deep Volume I's subject.
What this chapter owns is the release: the day deprecation got a single standard annotation.

## What shipped

`warnings.deprecated(message)` is a decorator for functions and classes.
Applied, it makes the object emit a `DeprecationWarning` carrying the message when used, sets a `__deprecated__` attribute, and is recognized by type checkers as a deprecation marker.
Listing 285.1 shows this on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- calling a @deprecated function still works, but warns ---
  old_api(21) returned : 42   (it still WORKS)
  it emitted a warning : True
  warning category : DeprecationWarning
  warning message  : 'use new_api() instead'
  the function runs normally - deprecation does not break callers -
  but every call raises a DeprecationWarning carrying your message.
  no manual warnings.warn() inside the body; the decorator does it
--- the message is yours: say what to use instead ---
  the decorator argument becomes the warning text, so you point users
  at the replacement ('use new_api() instead'). a good deprecation
  always names the migration path, and this puts it in the warning
--- classes can be deprecated too: instantiation warns ---
  Legacy(5).value : 5   (still constructs)
  constructing it warned : True
  message : 'use Modern instead'
  putting @deprecated on a CLASS warns when it is instantiated, so a
  whole type can be phased out with the same one-line marker
--- the decorator also sets a marker attribute for tools ---
  old_api.__deprecated__ : 'use new_api() instead'
  besides the runtime warning, the decorator records the message on
  __deprecated__, which a static type checker reads to flag USES of
  the deprecated API in the editor and CI (Deep I) - before the code
  ever runs. one annotation serves both the runtime and the checker
--- the payoff: one marker for both audiences ---
  before PEP 702 you wrote a warnings.warn() in the body (runtime
  only) AND separately signalled the checker somehow. @deprecated is
  a single decorator that BOTH warns at runtime AND is understood
  statically - no drift between what the code does and what tools see
--- the constraint answered ---
  deprecating an API meant two disconnected signals: a hand-written
  runtime warning and a separate static hint. warnings.deprecated
  (3.13, PEP 702) is one decorator on a function or class that emits
  the DeprecationWarning AND marks it for type checkers. deprecation
  became a single, standard annotation for both runtime and tooling
```

## Why each part answers the constraint

**It warns without breaking.**
The first block shows `old_api(21)` still returning `42` - deprecation does not break callers - while emitting a `DeprecationWarning` carrying the message.
The warning is produced by the decorator, not by a hand-written `warnings.warn()` in the body, so the function's code stays about what it does, not about announcing its own obsolescence.

**The message names the migration.**
The second block emphasizes that the decorator argument becomes the warning text, so you point users at the replacement ("use new_api() instead").
A good deprecation always names the migration path, and putting it in the warning means every caller who triggers it sees where to go.

**Classes work too.**
The third block shows `@deprecated` on a *class*: `Legacy(5)` still constructs, but instantiating it warns.
So a whole type can be phased out with the same one-line marker, not just individual functions - important when you are retiring an entire API surface.

**The static marker.**
The fourth block shows the other half: the decorator records the message on `__deprecated__`, which a static type checker reads to flag *uses* of the deprecated API in the editor and CI (Deep Volume I) - before the code ever runs.
This is the check-time audience: developers see the deprecation as they write the call, not only when it executes.

**One marker, both audiences.**
The fifth block states the unification.
Before PEP 702 you wrote a `warnings.warn()` for runtime *and* separately signalled the checker somehow, with the two able to drift.
`@deprecated` is a single decorator that both warns at runtime and is understood statically - so what the code does and what tools see cannot fall out of sync.

## The two-track note

The type system that reads `__deprecated__` and flags uses of deprecated APIs is Deep Volume I's to develop, alongside the broader typing story.
`warnings.deprecated` is the runtime half plus the standard marker that the static half keys on.
What the timeline records is the release act: in 3.13, PEP 702 added `warnings.deprecated`, unifying runtime and static deprecation into one annotation.
The modern consequence, verified above, is that libraries mark deprecated functions and classes with a single decorator, and both a running program and a type checker report the deprecation with the same message and migration guidance.

## Where this lands

`warnings.deprecated` is a small standardization that fixed a real coordination problem in API evolution.
Reach for it whenever you retire a function or class: decorate it with a message naming the replacement, and you get the runtime `DeprecationWarning` and the static checker flag from one annotation, guaranteed consistent.
Keep the deprecated thing working - deprecation is a transition, not a removal - and let the warning and the static hint drive callers toward the migration on their own schedule.
Deep Volume I explains how the static half reads the marker; this chapter is the record of the release that made deprecation a single standard annotation.
