# Chapter 281: Override

## The constraint

Here is a bug that has cost real teams real hours.
You write a subclass that overrides a base-class method - say `on_receive` - but you *misspell* it as `on_recieve`.
Or the override is correct, but months later someone renames the base method from `on_receive` to `handle_message`.
In both cases, your method still *exists* and still *runs* when called directly - but it is now a brand-new method that nothing dispatches to.
The base class's version runs instead, and your carefully-written override silently does nothing.

This is a nasty failure precisely because it is silent.
There is no error, no exception, no warning.
The code looks correct, the method is right there in the subclass, and yet the behavior is the base class's, not yours.
Tracking it down means realizing that a method you *thought* was overriding is not - a hypothesis that is easy to overlook because the method plainly exists.

The root cause is that Python has no way to *declare* "this method is meant to override a base method."
Overriding is implicit - a subclass method with a matching name simply replaces the base one - so there is nothing to check the name against.

The constraint Python 3.12 (2023, PEP 698) answered: **let a method declare that it overrides a base method, so a type checker can verify a matching base method actually exists** - turning a silent no-op into a caught mistake.

This is a two-track chapter.
The type system that enforces the declaration is Deep Volume I's subject.
What this chapter owns is the release: the day "I am overriding" became something you can state and have checked.

## What shipped

`typing.override` is a decorator that marks a method as intentionally overriding a base method.
A static type checker verifies that a base method of that name exists and errors if not.
At runtime it is a passthrough that sets `__override__ = True` on the function.
Listing 281.1 shows the mechanism and the bug it catches, on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- @override marks a method as intentionally overriding a base one ---
  GoodHandler().on_receive('x') : custom handles x
  the override actually took effect (not the base) : True
  @override declares intent: this method is meant to replace a base
  method of the same name. a type checker verifies that base method
  exists - so a rename or typo is caught statically, not in production
--- the bug it catches: a misspelled override silently does nothing ---
  TypoHandler().on_receive('x') : base handles x   <- BASE ran
  the typo'd on_recieve exists but is never called : True
  on_recieve (misspelled) did NOT override on_receive, so the BASE
  method runs and the 'override' is dead code. @override on that
  method would make a type checker report 'no base method on_recieve'
--- at runtime @override is a passthrough that sets a marker ---
  GoodHandler.on_receive.__override__ : True
  it did not change the method's behaviour : True
  @override returns the function unchanged, only tagging it with
  __override__ = True. the ENFORCEMENT is a static type checker's job
  (Deep I); at runtime the decorator is essentially free and inert
--- why declaring intent matters as a codebase evolves ---
  when a base class renames or removes a method, every @override that
  targeted it lights up in the type checker at once - you find every
  broken subclass immediately. without the marker, they silently stop
  overriding and misbehave at runtime, scattered and hard to trace
--- the constraint answered ---
  an override that misspells the name or misses a base rename still
  RUNS - as an uncalled new method - so the base version executes and
  the override silently vanishes. @override (3.12) states the intent;
  a checker confirms a matching base method exists, turning a silent
  no-op into a caught error. runtime cost is a single marker attribute
```

## Why each part answers the constraint

**Declaring intent.**
The first block shows `@override` on `GoodHandler.on_receive`, which correctly overrides the base method - the custom version runs, not the base.
The decorator declares "this method is meant to replace a base method of the same name," and a type checker verifies that base method exists.
So a typo or a base rename is caught *statically*, before the code ships, rather than surfacing as wrong behavior in production.

**The silent bug.**
The second block demonstrates exactly what goes wrong without the declaration.
`TypoHandler` defines `on_recieve` (misspelled), so calling `on_receive` runs the *base* method - `"base handles x"` - while the typo'd method exists but is never called.
The "override" is dead code.
Had `@override` been applied to `on_recieve`, a type checker would report "no base method `on_recieve` to override," catching the typo immediately.
This is the whole value proposition: the marker makes the silent failure loud.

**Runtime is inert.**
The third block shows what `@override` does at runtime: it returns the function unchanged and sets `__override__ = True` on it.
`GoodHandler.on_receive.__override__` is `True`, and the method's behavior is unaffected.
The *enforcement* is a static type checker's job (Deep Volume I); at runtime the decorator is essentially free, a marker tools can read.
This is the standard pattern for `typing` decorators - they inform static analysis without changing execution.

**Value over a codebase's life.**
The fourth block states the payoff that grows with the codebase.
When a base class renames or removes a method, *every* `@override` that targeted it lights up in the type checker at once - you find every broken subclass immediately, in one pass.
Without the marker, those subclasses silently stop overriding and misbehave at runtime, scattered across the codebase and hard to trace back to the base change.
`@override` turns a diffuse, delayed failure into a concentrated, immediate one.

## The two-track note

The type system that gives `@override` its meaning - how a checker resolves the base classes, looks for a matching method, and reports a violation - is Deep Volume I's to develop, alongside the broader story of gradual typing in Python.
`typing.override` is a declaration to that system, inert at runtime by design.
What the timeline records is the release act: in 3.12, PEP 698 added `@override`, letting the intent to override be stated and checked.
The modern consequence, verified above, is that override-related bugs - typos and missed base renames - are catchable statically, and large class hierarchies can be refactored with the type checker flagging every subclass that a base change breaks.

## Where this lands

`@override` is a small, zero-runtime-cost annotation with real value in any codebase that uses inheritance and a type checker.
Apply it to every method you intend to override a base method - it costs nothing at runtime and buys you static verification that the override is real.
The payoff is largest in deep or widely-used class hierarchies, where a base method rename would otherwise silently break subclasses; with `@override`, the checker finds them all.
Like all of `typing`, it does nothing on its own - its value is realized when you run a type checker over your code.
Deep Volume I explains the type system that enforces it; this chapter is the record of the release that let "I am overriding" be stated and checked.
