# Chapter 291: Finally Control Flow

## The constraint

Chapter 232 established that `finally` is the strongest guarantee in the language: it runs no matter how the block exits - on success, on a handled error, on an unhandled error propagating through, on an early `return`.
That power has a dark corner.

If you put a `return`, `break`, or `continue` *inside* a `finally` block, that control transfer *hijacks* the block's exit and *discards* whatever was in progress.
A `return` in `finally` overrides whatever the `try` was going to return - and, far worse, it *swallows a propagating exception*.
An exception that was on its way up the stack simply vanishes when the `finally` returns, and the caller sees a normal return where there should have been an error.
The genuine failure disappears without a trace.

This is almost never what anyone intends.
It is a bug - and, before 3.14, an *invisible* one: the code compiled and ran, silently eating exceptions and overriding returns, with nothing to flag the mistake.

The constraint Python 3.14 (2025, PEP 765) answered: **make the compiler warn on control flow that leaves a `finally` block**, surfacing the footgun without breaking the rare code that uses it deliberately.

This is a two-track chapter.
Exception unwinding is Deep Volume B's subject.
What this chapter owns is the release: the day the `finally` trap got a warning label.

## What shipped

PEP 765 makes the compiler emit a `SyntaxWarning` when a `return`, `break`, or `continue` appears inside a `finally` block.
The code still compiles and runs - the change is a warning, not an error - so existing code is not broken, only flagged.
Listing 291.1 shows the warnings and the underlying bug on the 3.14 builds (gated to 3.14+).

Verified output (CPython 3.14.6):

```text
--- `return` in a finally block now warns at compile time ---
  return in finally -> SyntaxWarning: "'return' in a 'finally' block"
  the compiler flags it as a SyntaxWarning. the code still COMPILES
  (nothing breaks), but the footgun is now visible instead of silent
--- break and continue in a finally warn too ---
  break in finally -> SyntaxWarning: "'break' in a 'finally' block"
  continue in finally -> SyntaxWarning: "'continue' in a 'finally' block"
  all three control-flow statements in a finally are flagged, because
  each hijacks the block's exit and discards whatever was in progress
--- the actual bug: a finally return SWALLOWS an exception ---
  a function that raises but returns from finally : 'finally ate the exception'
  the ValueError was RAISED, but the finally's return overrode the
  whole unwinding - so the caller sees a normal return and NEVER sees
  the exception. a genuine error vanished without a trace
--- and it overrides the try's return value ---
  try returns 'from try', finally returns 'from finally' : 'from finally'
  the finally's return replaces the try's - another silent surprise.
  whatever the try was going to return is simply discarded
--- the fix: never transfer control out of a finally ---
  put cleanup in finally, but let control flow (return/break/continue/
  raise) happen in the try or after the block. finally is for cleanup,
  not for deciding what the function returns or where the loop goes
--- the constraint answered ---
  return/break/continue inside finally silently swallow exceptions and
  override returns - almost always a bug, and invisible before 3.14.
  PEP 765 makes the compiler warn on it, surfacing the trap while
  still compiling the code. the strongest guarantee's sharpest edge
  finally comes with a warning label
```

## Why each part answers the constraint

**`return` in finally warns.**
The first block shows the compiler emitting `SyntaxWarning: "'return' in a 'finally' block"` for a function that returns from its `finally`.
The code still compiles - nothing is broken - but the footgun is now *visible* instead of silent.
This is the core of PEP 765: turn a silent trap into a flagged one.

**`break` and `continue` too.**
The second block shows the same warning for `break` and `continue` in a `finally` within a loop.
All three control-flow statements are flagged, because each hijacks the block's exit and discards whatever was in progress - the loop iteration, the return, or the propagating exception.

**The exception-swallowing bug.**
The third block demonstrates why this matters most.
A function raises `ValueError`, but its `finally` block `return`s - and the caller receives `'finally ate the exception'`, a *normal return*.
The `ValueError` was raised, but the `finally`'s return overrode the entire unwinding, so the exception never reaches the caller.
A genuine error vanished without a trace - the single most dangerous consequence of this pattern, and exactly what the warning is meant to catch.

**Overriding the return.**
The fourth block shows the milder but still surprising case: a `try` that returns `'from try'` with a `finally` that returns `'from finally'` yields `'from finally'`.
The `finally`'s return silently replaces the `try`'s.
Whatever the `try` was going to return is simply discarded - another silent surprise that the warning now surfaces.

**The fix.**
The fifth block states the rule: put *cleanup* in `finally`, but let *control flow* - `return`, `break`, `continue`, `raise` - happen in the `try` or after the block.
`finally` is for cleanup, not for deciding what the function returns or where the loop goes.
Follow that rule and the warning never fires, because you never transfer control out of a `finally`.

## The two-track note

The unwinding semantics - how a `finally` block runs during exception propagation, and precisely how a control transfer inside it discards the pending exception or return - are Deep Volume B's to develop, and this chapter is the direct sequel to Chapter 232's treatment of the unified `try`.
What the timeline records is the release act: in 3.14, PEP 765 made control flow leaving a `finally` a `SyntaxWarning`.
The modern consequence, verified above, is that one of the language's most insidious silent bugs - a `finally` that eats exceptions - is now flagged at compile time, while the rare deliberate uses still compile.
This is a recurring pattern in the language's maturation: taking a silent, dangerous behavior and giving it a warning label rather than an outright removal, so the footgun becomes visible without breaking anyone.

## Where this lands, and the close of Deferred and Supported

Control flow in `finally` is a small warning with a large safety benefit: it targets a bug that could silently discard real errors.
The rule is simple and worth internalizing regardless of Python version: never `return`, `break`, or `continue` out of a `finally` block - do your cleanup there and let control flow happen elsewhere.
On 3.14+, the compiler will remind you; on earlier versions, the discipline is yours to keep.
Deep Volume B explains the unwinding; Chapter 232 explains the `finally` guarantee this is the sharp edge of; this chapter is the record of the release that gave that edge a warning label.

This closes Volume 18, Deferred and Supported.
The volume's name captures 3.14's two headline threads: PEP 649's *deferred* annotations (Chapter 24), the lasting resolution of the annotation-evaluation question that PEP 563 (Chapter 265) had only provisionally answered, and free-threading moving from experimental to *supported* status.
Its landmark additions were template strings (Chapter 25) and the subinterpreters of `concurrent.interpreters` (Chapter 287), joined by the ergonomic and standard-library gains gathered here: parenthesis-free `except`, `compression.zstd`, time-ordered UUIDs, and the `finally` warning.
Part VII continues with Deep Volume L - the full free-threading and subinterpreters story these releases built toward - and then Volume 19, the frontier.
