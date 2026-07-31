# Chapter 232: The Unified Try

## The constraint

Before Python 2.5, the `try` statement came in two mutually exclusive shapes.
You could write `try`/`except` to handle errors, or you could write `try`/`finally` to guarantee cleanup - but you could not write both in a single `try`.
The grammar forbade it.
So the extremely common need - "handle some of the errors that might occur here, *and* run this cleanup no matter what happens" - forced a two-level nest:

```python
try:                      # outer: guarantee cleanup
    try:                  # inner: handle errors
        work()
    except SomeError:
        recover()
finally:
    cleanup()
```

Everyone wrote this shape, and no one liked it.
The nesting added a level of indentation that carried no meaning beyond "the grammar made me," and it visually separated the cleanup from the operation it protected.
The constraint Python 2.5 (2006) answered was small and precise: **let one `try` statement carry `except`, `else`, and `finally` together, so the four roles of structured error handling live in one flat block.**

This is a two-track chapter.
Exception unwinding itself - how the interpreter walks the stack looking for a handler, how `finally` blocks are guaranteed to run during that walk, what happens to an in-flight exception when a `finally` clause itself returns - belongs to Deep Volume B (execution and exceptions).
What this chapter owns is the release: the day the four-clause `try` became one statement, and the precise guarantee each clause carries.

## What shipped

Python 2.5 unified the grammar so a single `try` may have any of `except` clauses, an `else` clause, and a `finally` clause - all at once.
Listing 232.1 exercises all four roles and the guarantees each one gives, on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- one try, all four clauses: the 2.5 unification ---
  divide(10, 2) -> 5.0
    else: ran because no exception was raised
    finally: always runs (cleanup goes here)
  except + else + finally in ONE try - before 2.5 you nested a
  try/except inside a try/finally to get both. now it is one
  statement with four roles, each with a precise trigger
--- the error path: except fires, else is skipped, finally still runs ---
  divide(10, 0) -> None
    except: caught division by zero
    finally: always runs (cleanup goes here)
  raise -> except runs, else is SKIPPED, finally runs anyway. `else`
  is the 'only if no exception' clause; `finally` is the 'no matter
  what' clause. the two are not redundant - they trigger oppositely
--- finally runs even when the try RETURNS or RE-RAISES ---
    finally: ran before the return completed
  return inside try: returned from try
    finally: ran while the exception was propagating
  uncaught error still propagated after finally : boom
  finally is the strongest guarantee in the language: it runs on
  success, on a handled error, on an UNhandled error, and even as a
  return or raise leaves the block. that is why cleanup lives there
--- why it matters: cleanup after the block is NOT safe ---
  f = open(...); work(); f.close()   # close SKIPPED if work() raises
  try: work() finally: f.close()      # close ALWAYS runs
  putting f.close() after the block skips it on any error; putting
  it in finally guarantees it. `with` (Chapter 5) is exactly this
  finally-guarantee packaged so you cannot forget it
--- the constraint answered ---
  pre-2.5, a try had except OR finally, never both, so 'handle some
  errors AND always clean up' meant nesting two trys. 2.5 unified
  them into one four-clause statement: try/except/else/finally, each
  clause a precise guarantee - the foundation `with` builds on
```

## Why each part answers the constraint

**Four clauses, one statement.**
The first block shows the unified form doing what previously required a nest: `divide(10, 2)` runs the `try`, takes no exception, runs the `else`, and runs the `finally`.
The `else` clause is the piece most programmers underuse - it runs *only* when the `try` body raised nothing, which lets you separate "the operation that might fail" (in `try`) from "the follow-up that should run only on success" (in `else`), so a stray exception from the follow-up is not accidentally caught by the `except` meant for the operation.

**`else` and `finally` trigger oppositely - that is why both exist.**
The second block runs the error path: `divide(10, 0)` raises, so `except` catches it, `else` is *skipped*, and `finally` runs anyway.
This is the clarifying contrast.
`else` is the "only if nothing went wrong" clause; `finally` is the "no matter what happened" clause.
They are not two names for the same thing - they fire under opposite conditions, and a well-structured `try` uses each for its own guarantee.

**`finally` is the language's strongest guarantee.**
The third block pushes `finally` to its limits.
It runs when the `try` body executes a `return` (the cleanup happens *before* the return value is delivered to the caller).
It runs when an exception is propagating *unhandled* (the cleanup happens as the exception passes through, and then the exception continues on its way).
Success, handled error, unhandled error, early return, in-flight raise - `finally` runs in every one.
There is no control-flow path out of the `try` body that skips it, which is exactly the property cleanup code needs.

**This is why cleanup belongs in `finally`, not after the block.**
The fourth block states the practical rule the guarantee implies.
Writing `f = open(...); work(); f.close()` *skips the close* if `work()` raises, leaking the file handle on precisely the error path where cleanup matters most.
Moving the close into a `finally` guarantees it runs on every path.
And that guarantee is exactly what the `with` statement (Chapter 5) packages: a context manager's `__exit__` is a `finally` you cannot forget to write, which is why `with open(...)` superseded the manual `try`/`finally` for the common cases.
The unified `try` is the foundation; `with` is the ergonomic layer built on top of it.

## The two-track note

The unwinding mechanics - how the interpreter guarantees `finally` during stack unwinding, the subtle and discouraged case where a `return` or `break` *inside* a `finally` swallows a propagating exception, how exception chaining interacts with cleanup - are Deep Volume B's to detail.
The ergonomic layer that turns the `finally` guarantee into `with` is Chapter 5's.
What the timeline records is the enabling release: in 2.5, the four roles of error handling stopped requiring two nested statements and became one flat, four-clause `try`.
The modern consequence, verified above, is that the guarantees each clause carries are exactly as sharp today as when the grammar was unified, and they are what everything from `with` blocks to database transaction wrappers ultimately rest on.

## Where this lands

The unified `try` is a small grammar change with an outsized clarifying effect: it made the structure of "attempt, handle, confirm, clean up" expressible in one block, with each clause carrying a guarantee you can state in one sentence.
Reach for `else` to keep success-only follow-up out of the `try` body; reach for `finally` whenever a resource, lock, or state change must be undone no matter how the block exits; and reach for `with` when the cleanup fits the context-manager shape.
Deep Volume B explains how the interpreter keeps the `finally` promise; this chapter is the record of the release that let all four clauses finally share one statement.
