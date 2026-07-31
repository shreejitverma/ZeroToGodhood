# Chapter 233: Coroutines via Send

## The constraint

Chapter 226 told the first half of the generator story: in Python 2.2, a function with `yield` became an iterator, and laziness became easy.
But that generator was a one-way street.
Values flowed *out* through `yield`, and the caller's only verb was "pull the next one" - `next(gen)`.
There was no way to hand a value *back into* a suspended generator, no way for the code driving it to influence what happened when it resumed.
A generator was a producer you could only read from.

That one-directionality was a real ceiling.
Plenty of computations are naturally two-way: a running total that you feed numbers into, a parser you push tokens at, a state machine you drive with events.
Expressing those as generators was impossible, because the generator could not receive.
The constraint Python 2.5 (2006, PEP 342) answered was exactly this: **make `yield` a two-way channel, so a value can flow back into the generator at the point where it suspended, and a generator can become something you talk to rather than only listen to.**

This is a two-track chapter.
The coroutine model in full - the suspend/resume frame machinery, how `send`/`throw`/`close` drive a suspended frame, how this generalizes into the event-loop-driven coroutines of `asyncio` - belongs to Deep Volume F (iteration, generators, coroutines).
What this chapter owns is the release: the day `yield` stopped being only a statement that emits and became an expression that also receives.

## What shipped

PEP 342 made `yield` an *expression*.
Written as `value = yield average`, it does two things at one suspension point: it yields `average` *out* to whoever is driving the generator, and when the generator is resumed, the `yield` expression *evaluates to* whatever value was sent *in*.
The new method that sends a value in is `.send(x)`; PEP 342 added `.throw()` and `.close()` alongside it.
Listing 233.1 builds a running-average coroutine to show the two-way flow, on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- yield as an expression: value flows OUT and IN at one point ---
  send(10) -> running average : 10.0
  send(20) -> running average : 15.0
  send(30) -> running average : 20.0
  `value = yield average` yields average OUT and binds the SENT value
  to `value` IN. that two-way flow at one suspension point is the
  whole of PEP 342 - a generator you push into, not just pull from
--- pull (next) vs push (send): the same yield, two directions ---
  next(g)     == g.send(None)  : pull a value out, send nothing in
  g.send(x)   : resume with `yield` evaluating to x - push in AND pull
  a plain generator (Chapter 226) only ever pulled; send() added the
  push, and 'a generator you push into' is the definition of a
  coroutine (Deep F)
--- priming: a coroutine must be advanced to its first yield ---
  send() before priming raises : TypeError(can't send non-None value to a just-started generator)
  after next() primes it, send(5) works : 5.0
  you cannot send into a generator that has not yet reached a yield -
  there is nowhere for the value to land. hence the priming next(),
  the wart that @coroutine decorators and later async/await hid away
--- throw() and close(): the caller also controls the coroutine ---
  after close(), send() raises StopIteration (coroutine is done)
  send() is the headline, but PEP 342 also gave throw() (raise INTO
  the generator) and close() (stop it). the caller now fully drives
  the coroutine's lifecycle - resume, inject, terminate
--- the constraint answered ---
  2.2 generators were a one-way pull: values only came OUT. PEP 342
  made yield an expression with send(), so values also go IN - a
  generator became a two-way coroutine you drive. that primitive is
  the seed of yield from (3.3) and async/await (3.5): async began
  the day yield learned to receive
```

## Why each part answers the constraint

**Two-way flow at one point.**
The first block is the entire feature in miniature.
The `running_average` coroutine holds its total and count as local state, and at `value = yield average` it hands the current average out and waits.
Each `send(10)`, `send(20)`, `send(30)` resumes it, binds the sent number to `value`, updates the running figures, and yields the new average - `10.0`, `15.0`, `20.0`.
The generator is now a stateful accumulator you feed, not a fixed sequence you drain.
That is the capability the pre-2.5 generator could not offer.

**`next` and `send` are the same suspension, driven two ways.**
The second block draws the equivalence: `next(g)` is exactly `g.send(None)` - resume, sending nothing in.
`g.send(x)` resumes with the `yield` expression evaluating to `x`.
The same `yield`, the same suspension point, now serves both directions.
A generator you only ever `next` through is a producer; a generator you `send` into is a coroutine.
The word "coroutine" here means precisely "a generator you push values into," and that is Deep Volume F's subject in full.

**Priming is the wart the release left behind.**
The third block shows the rough edge PEP 342 could not avoid.
You cannot `send` a real value into a brand-new generator, because it has not yet reached a `yield` - there is nowhere for the value to land.
The attempt raises `TypeError: can't send non-None value to a just-started generator`.
So every coroutine must first be "primed" with a `next()` (or `send(None)`) to advance it to its first `yield`.
This priming step was a persistent source of bugs, and it is exactly the kind of ceremony that later designs - the `@coroutine` priming decorator, and ultimately `async`/`await` - were built to hide.
The chapter shows the wart rather than papering over it, because the wart is part of why the later syntax exists.

**The caller drives the whole lifecycle.**
The fourth block rounds out the control surface: beyond `send`, PEP 342 gave `throw` (raise an exception *inside* the generator at its suspension point) and `close` (inject `GeneratorExit` to shut it down).
After `close()`, a further `send()` raises `StopIteration` - the coroutine is finished.
Between `send`, `throw`, and `close`, the driving code now controls resume, error injection, and termination.
That full lifecycle control is what an event loop needs to schedule coroutines, which is why this primitive sits directly beneath `asyncio`.

## The two-track note

The frame mechanics that make suspend-and-resume-with-a-value work, the formal coroutine model, and the long arc from `send` through `yield from` (3.3) to `async`/`await` (3.5) and the `asyncio` event loop are Deep Volume F's to develop.
What the timeline records is the pivot: in 2.5, `yield` became an expression, and with `send` a generator became a two-way channel.
Every later step in Python's async story is a refinement of this one primitive.
The modern consequence, verified above, is that a running-average coroutine written to the 2.5 model still runs byte-for-byte the same today, priming wart and all - and that "async began the day `yield` learned to receive" is not a metaphor but a literal reading of the release history.

## Where this lands

`send` is the hinge of Python's concurrency story.
Before it, generators were lazy producers; after it, they were drivable coroutines, and the entire path to `async`/`await` runs through this single change to what `yield` means.
You will rarely write a raw `send`-driven coroutine today - `async def` and `await` cover the cases that matter, and hide the priming - but understanding that they are refinements of "a generator you push into" is what makes the async model legible rather than magical.
Deep Volume F builds the full model; this chapter is the record of the release where a generator first became something you could talk back to.
