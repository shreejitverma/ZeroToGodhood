# Chapter 260: Generator Stop

## The constraint

A generator signals that it is finished by raising `StopIteration`.
Normally this happens *implicitly*: when the generator's body falls off the end, the machinery raises `StopIteration`, and the `for` loop or `list()` consuming it understands "done" and stops.
This is the iterator protocol working exactly as designed (Chapter 226, Deep Volume F).

But there was a dangerous ambiguity in how it worked.
`StopIteration` is an ordinary exception, and if it was raised *inside* a generator's body for some *other* reason - not because the generator was done, but because of a bug - it looked identical to the normal "done" signal.
The classic case: calling `next(it)` on an iterator that has already been exhausted raises `StopIteration`.
If that `next` call happened inside a generator, the `StopIteration` it raised would propagate up and be interpreted as "this generator is finished," so the generator would *silently stop early*.

This is one of the worst failure modes in programming: not a crash, not an error, not a traceback - just *fewer items than intended*, quietly, with the wrong output surfacing somewhere far downstream where it is nearly impossible to trace back to the cause.
A bug (running an iterator dry) masqueraded as normal completion.

The constraint PEP 479 answered: **make an accidental `StopIteration` escaping a generator's body a loud error rather than a silent early exit**, by converting it to `RuntimeError`.
It was opt-in in Python 3.5 (`from __future__ import generator_stop`) and became the default in 3.7.

This is a two-track chapter.
The generator and iterator protocol - how `StopIteration` drives iteration, how a generator's frame produces and terminates - is Deep Volume F's.
What this chapter owns is the release: the day an accidental `StopIteration` inside a generator became a visible error.

## What shipped

Under PEP 479, a `StopIteration` that propagates out of a generator's body is replaced with a `RuntimeError` (`generator raised StopIteration`), so it cannot silently be mistaken for normal completion.
The implicit "fell off the end" completion is unaffected.
Listing 260.1 shows the trap and the fix on today's interpreters, where the behavior is the default.

Verified output (CPython 3.13.5):

```text
--- a generator ending normally: StopIteration is implicit and fine ---
  list(counts_to_three()) : [1, 2, 3]
  falling off the end raises StopIteration internally - the correct,
  intended way to say 'done'. that path is unchanged by PEP 479
--- the trap: next() on an exhausted iterator INSIDE a generator ---
  broken() loops forever calling next(it); when it exhausts, next()
  raises StopIteration from INSIDE the generator body
  list(broken([10, 20])) -> RuntimeError: generator raised StopIteration
  since 3.7 the escaping StopIteration becomes a RuntimeError, so the
  bug is LOUD. before PEP 479 this returned [10, 20] silently, hiding
  that next() had run off the end - the invisible-truncation failure
--- the correct version: catch StopIteration or use a for-loop ---
  list(fixed([10, 20])) : [10, 20]
  a for-loop consumes the iterator and stops cleanly at the end -
  StopIteration never escapes the body. this is the right way to
  delegate iteration; raw next() in a generator needs a guard
--- why the old behaviour was so dangerous ---
  'silently produced fewer items than intended' is nearly impossible
  to debug: no error, no traceback, just wrong output somewhere
  downstream. PEP 479 converts the accidental StopIteration into a
  RuntimeError with a traceback pointing AT the bug - turning a silent
  data-corruption failure into an ordinary, findable exception
--- confirming the modern default is active ---
  a bare `raise StopIteration` in a generator -> RuntimeError
  on this interpreter the PEP 479 behaviour is the default (3.7+):
  StopIteration cannot leak out of a generator to fake an early exit
--- the constraint answered ---
  a StopIteration raised inside a generator was indistinguishable
  from a normal finish, so an accidental one (next() on a dry
  iterator) silently truncated output - a hidden, brutal bug. PEP 479
  converts an escaping StopIteration to RuntimeError (opt-in 3.5,
  default 3.7), making the mistake a loud, traceable error
```

## Why each part answers the constraint

**Normal completion is unchanged.**
The first block confirms PEP 479 does not touch the intended path: `counts_to_three` falls off the end, raises `StopIteration` internally, and `list()` collects `[1, 2, 3]` exactly as before.
The fix targets only the *accidental* case, not the normal one.

**The trap, now loud.**
The second block reproduces the bug.
`broken` loops forever calling `next(it)`; when `it` exhausts, `next` raises `StopIteration` from inside the generator body.
On 3.7+, this becomes `RuntimeError: generator raised StopIteration` - a loud, traceable error.
The verified output shows exactly that.
Before PEP 479, this same code returned `[10, 20]` *silently*, hiding that `next` had run off the end - producing correct-looking output that happened to be a truncation, with no signal that anything went wrong.

**The correct version.**
The third block shows the right way to consume an iterator inside a generator: a `for` loop, which handles exhaustion internally and stops cleanly, so `StopIteration` never escapes the body.
`fixed` yields `[10, 20]` correctly.
The lesson is that delegating iteration with a `for` loop (or `yield from`) is safe, while raw `next()` inside a generator needs a guard - and PEP 479 is what makes the unguarded version fail loudly instead of silently.

**Why the old behavior was so dangerous.**
The fourth block states the principle.
"Silently produced fewer items than intended" is among the hardest bugs to diagnose - no error, no traceback, just wrong output somewhere downstream.
PEP 479 converts that silent data-corruption failure into an ordinary exception with a traceback pointing at the offending line, moving the failure from "invisible and brutal" to "findable and normal."

**The modern default is active.**
The fifth block confirms it directly: a bare `raise StopIteration` inside a generator raises `RuntimeError` on this interpreter, proving the PEP 479 behavior is the default (3.7+).
`StopIteration` can no longer leak out of a generator to fake an early exit.

## The two-track note

The generator and iterator mechanics - how `StopIteration` terminates iteration, how a generator frame produces values and signals completion, how `yield from` delegates - are Deep Volume F's to develop.
PEP 479 is a targeted correctness fix at the boundary between the exception model and the iterator protocol: it disambiguates "the generator is done" (implicit `StopIteration`) from "a `StopIteration` bubbled up by accident" (now `RuntimeError`).
What the timeline records is the staged rollout: opt-in via `from __future__ import generator_stop` in 3.5, default in 3.7.
The modern consequence, verified above, is that a whole category of silent truncation bugs now fails loudly, and the safe idiom - delegate iteration with `for` or `yield from`, guard any raw `next()` - is what the change nudges you toward.

## Where this lands, and the close of Native Syntax

`generator_stop` (PEP 479) is a small change with an outsized safety benefit: it turned one of the most insidious silent-failure modes in the language into an ordinary, traceable exception.
The practical guidance is simple: inside a generator, consume other iterators with `for` loops or `yield from` rather than bare `next()`, and if you must use `next()`, give it a default (`next(it, sentinel)`) or catch `StopIteration` locally - never let it escape the generator body.
Deep Volume F explains the iterator protocol this rests on; this chapter is the record of the release that made an accidental `StopIteration` a visible error.

This closes Volume 11, Native Syntax.
The volume's headline was `async` and `await` becoming native keywords (Chapter 11) - the moment the coroutine machinery that began with `send` (Chapter 233) and matured through `yield from` (Chapter 9) got dedicated syntax and stopped being a clever reuse of generators.
Around that landmark, 3.5 was a syntax-and-correctness release: unpacking generalizations (Chapter 257), `math.isclose` (Chapter 258), `subprocess.run` (Chapter 259), and the `generator_stop` fix here.
Part IV now hands off to Deep Volume J, the full `asyncio` and structured-concurrency model that native `async`/`await` made expressible - the destination this entire part has been following generators toward.
