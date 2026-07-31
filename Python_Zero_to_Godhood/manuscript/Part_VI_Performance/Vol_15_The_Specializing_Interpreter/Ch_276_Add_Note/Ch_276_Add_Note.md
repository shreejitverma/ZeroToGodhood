# Chapter 276: Add Note

## The constraint

An exception raised deep in a library carries the *local* truth - "invalid literal for int()" - but not the *contextual* truth the person reading the crash actually needs: *which* value, in *which* row, of *which* file.
The low-level code that raises the error does not know it is parsing row 47 of `orders.csv`; the high-level code that does know is several stack frames away.

Before Python 3.11, adding that context meant one of two lossy moves.
You could catch the exception and re-raise a *new* one with a richer message - `raise ValueError(f"row {n}: {exc}")` - but that discards the original exception's *type* and its *traceback*, replacing a precise error with a reworded one and losing the chain of where it actually happened.
Or you could wrap it in a new exception type, which nests messages awkwardly and changes what callers catch.
Either way, enriching an error meant damaging it.

The constraint Python 3.11 (2022, PEP 678) answered: **let context be *attached* to an existing exception as it propagates - without changing its type or traceback** - so each layer can annotate what it knows and the original error travels intact.

This is a two-track chapter.
The exception model is Deep Volume B's subject.
What this chapter owns is the release: the day an error could gather context on its way up the stack.

## What shipped

`Exception.add_note(str)` attaches a note to an existing exception (stored in `exc.__notes__`), leaving its type, message, and traceback unchanged; each catching layer can add a note and re-raise the *same* exception, and the notes print in the traceback.
Listing 276.1 shows this on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- add_note attaches context without changing the exception ---
  exception type is still : ValueError
  original message intact : "invalid literal for int() with base 10: 'notanumber'"
  exc.__notes__ : ['while parsing row 47']
  add_note() did NOT wrap or replace the ValueError - it is the SAME
  exception, same type, same message, same traceback, now carrying an
  extra note. the note lives in exc.__notes__
--- notes ACCUMULATE as the exception travels up through layers ---
  final exception type : ValueError
  all accumulated notes :
    - while parsing row 3
    - in file 'orders.csv'
  parse_row added 'while parsing row 3', then load_file added 'in
  file orders.csv' to the SAME exception. each layer contributed what
  it knew; the notes stack up in order, low-level first
--- the notes appear in the printed traceback ---
  traceback contains the note lines : ['while parsing row 1', "in file 'data.csv'"]
  the notes print beneath the exception in the traceback, so whoever
  reads the crash sees the gathered context - not just 'invalid
  literal for int()' with no idea where it came from
--- why this beats catch-and-re-raise-with-new-message ---
  re-raising `raise ValueError(f'row {n}: {exc}')` DISCARDS the
  original exception's type and its traceback, and nests messages
  awkwardly. add_note keeps the exact exception and its traceback
  and simply annotates it - context WITHOUT loss
--- the constraint answered ---
  an exception from deep code lacked the caller's context, and adding
  it meant re-raising a NEW exception that lost the original type and
  traceback. add_note() (3.11) attaches context strings to the SAME
  exception as it propagates, so each layer annotates what it knows
  and the traceback shows the full, accumulated story
```

## Why each part answers the constraint

**Context without mutation of the exception.**
The first block shows the core property: after `add_note`, the exception is *still* a `ValueError`, its original message is intact, and the note lives in `exc.__notes__`.
`add_note` did not wrap or replace anything - it is the same exception, same type, same traceback, now carrying an annotation.
Code that catches `ValueError` still catches it; the type-based contract is preserved.

**Notes accumulate through layers.**
The second block shows the pattern that makes this powerful.
`parse_row` catches the error and adds "while parsing row 3," then re-raises the *same* exception; `load_file` catches it and adds "in file 'orders.csv'."
The two notes accumulate on one exception, in order, low-level first.
Each layer contributes exactly what it knows - the row from the row-parser, the filename from the file-loader - and the exception collects the full story as it rises.

**The notes reach the traceback.**
The third block confirms the notes print in the traceback (extracted here to stay machine-independent).
So whoever reads the crash sees "while parsing row 1" and "in file 'data.csv'" beneath the error, not a bare "invalid literal for int()" with no indication of where it came from.
The context that was scattered across the call stack is gathered into the one place a debugger looks.

**Why it beats re-raising.**
The fourth block states the comparison.
Re-raising with a new message discards the original type and traceback and nests messages awkwardly; `add_note` keeps the exact exception and its traceback and simply annotates it.
It is context *without loss* - the enrichment that the old approaches could not do without damage.

## The two-track note

The exception model - how exceptions propagate, how `__notes__` is stored and rendered, how this relates to exception chaining (`raise from`) and exception groups (Chapter 21) - is Deep Volume B's to develop.
What the timeline records is the release act: in 3.11, PEP 678 added `Exception.add_note`, so context can be attached to a live exception rather than fused into a replacement.
The modern consequence, verified above, is that libraries annotate errors with the context each layer knows - the framework, ORM, and validation libraries that catch and re-surface errors now add notes instead of rewrapping - and tracebacks carry a richer, loss-free story.

## Where this lands

`add_note` is a small addition that fixed a real tension between preserving an exception and enriching it.
Reach for it whenever you catch an exception, know something useful about the context, and want to pass that along without changing what the exception *is* - the row number, the filename, the operation in progress, the retry count.
Add the note and `raise` (bare) to re-raise the same exception; let each layer contribute its piece.
Prefer it to catch-and-re-raise-with-a-new-message, which throws away the original error's identity and traceback.
Deep Volume B explains the exception model; this chapter is the record of the release that let an error gather context as it travels.
