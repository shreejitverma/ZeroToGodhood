# Chapter 275: Fine-Grained Error Locations

## The constraint

When a Python program crashed, the traceback told you the *line* the error occurred on - and a line is often not precise enough.
Consider `data["a"]["b"]["c"]`: if a `TypeError: 'NoneType' object is not subscriptable` fires, *which* subscript was applied to `None`?
Consider `a + b + c`: if a `+` fails, was it `a + b` or `(a + b) + c`?
Consider `obj.contents.name`: if an `AttributeError` fires, was `contents` missing or `name`?
The line number was the same for every possibility, so you were left reading the code and reasoning out which sub-expression actually failed - a small tax paid on every debugging session, and a larger one when the line was dense.

The information to do better was, in principle, available at compile time: the compiler knows the exact column span of every sub-expression.
It just was not *recorded* in a way the traceback machinery could use.

The constraint Python 3.11 (2022, PEP 657) answered: **record the exact source column span of each operation, and underline the precise failing sub-expression in the traceback** - so a crash points at the operation, not just the line.

This is a two-track chapter.
The interpreter, bytecode, and code-object internals this rests on are Deep Volume J's subject.
What this chapter owns is the release: the day tracebacks gained column-level precision.

## What shipped

Python 3.11 records, per bytecode instruction, the `(start_line, end_line, start_col, end_col)` of the source that produced it (exposed via `code.co_positions()`), and the traceback formatter uses those spans to draw `^` carets under the exact failing sub-expression.
Listing 275.1 shows this on today's interpreters, extracting only the caret lines (not the file-path frames) so the output is machine-independent.

Verified output (CPython 3.13.5):

```text
--- carets point at the EXACT failing subscript, not just the line ---
    fn()
    ~~^^
    return data["a"]["b"]["c"]               # None["c"] fails; which subscript?
    ~~~~~~~~~~~~~~^^^^^
    -> TypeError: 'NoneType' object is not subscriptable
  the ^ carets underline `["c"]` specifically - the subscript that
  was applied to None. before 3.11 you only got the line and had to
  reason out which of the three subscripts blew up
--- which term of an arithmetic expression was the problem ---
    fn()
    ~~^^
    return a + b + c                         # a + b fails: b is None
    ~~^~~
    -> TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'
  in `a + b + c` the carets mark `a + b`, the failing operation. the
  line has three operands; the location tells you it was b, not c
--- attribute access in a chain: which attribute is missing ---
    fn()
    ~~^^
    return obj.contents.name                 # obj.contents is fine? no - missing
    ^^^^^^^^^^^^
    -> AttributeError: 'Box' object has no attribute 'contents'
  `obj.contents` does not exist, and the carets sit under `.contents`
  - not the whole chain. in a long a.b.c.d access, you see exactly
  which hop failed
--- the mechanism: code.co_positions() carries column spans ---
  sample.__code__.co_positions() yields column spans : True
  each bytecode instruction now records (start_line, end_line,
  start_col, end_col). the traceback machinery reads those to draw the
  carets. it is exact source-position tracking in the code object (Deep J)
--- the constraint answered ---
  a traceback pointed only at a LINE, so when a line had several
  places the error could originate you had to guess. PEP 657 (3.11)
  records per-instruction column spans and underlines the exact
  sub-expression with ^ carets. the traceback now points at the
  precise operation that failed, not just the line it was on
```

## Why each part answers the constraint

**The exact subscript.**
The first block shows `data["a"]["b"]["c"]` failing, with the carets `~~~~~~~~~~~~~~^^^^^` underlining the `["c"]` subscript specifically - the one applied to `None`.
Before 3.11 the traceback gave only the line, and you had to reason out which of the three subscripts blew up.
Now the carets point at it directly.

**The failing arithmetic term.**
The second block shows `a + b + c` failing at `a + b` (because `b` is `None`), with the carets `~~^~~` marking that operation - the `^` under the `+` of `a + b`.
On a line with three operands, the location tells you the problem is `b`, not `c`, without any guessing.

**The missing attribute in a chain.**
The third block shows `obj.contents.name` where `contents` is missing, with the carets under `.contents` (the whole `obj.contents` span) rather than the entire chain.
In a long `a.b.c.d` access, this shows exactly which hop failed - the difference between "an attribute error somewhere on this line" and "`contents` is the missing one."

**The mechanism.**
The fourth block exposes the underlying machinery: `code.co_positions()` yields the column spans that make the carets possible.
Each bytecode instruction now carries `(start_line, end_line, start_col, end_col)`, and the traceback machinery reads those to draw the underlines.
This is exact source-position tracking baked into the code object (Deep Volume J) - the carets are a rendering of data the compiler now records per instruction.

## The two-track note

The code object, bytecode, and the compiler that emits per-instruction position data are Deep Volume J's to develop; the traceback is a rendering layer over that data.
There is a small cost to storing the extra position information (a modestly larger code object), a trade the release made deliberately in favor of drastically better error messages - fitting Part VI's thesis that CPython traded complexity for value.
What the timeline records is the release act: in 3.11, PEP 657 added column-precise error locations.
The modern consequence, verified above, is that tracebacks point at the exact failing operation, which is one of the most quietly impactful debugging improvements in the language's history - every crash on a dense line is now self-explaining.

## Where this lands

Fine-grained error locations are a feature you benefit from without doing anything: upgrade to 3.11+ and your tracebacks simply get more precise.
Read the carets - they tell you which subscript, which operator, which attribute, which call argument produced the error, turning "somewhere on this line" into "exactly here."
When you need the raw position data programmatically (for tooling, coverage, or custom error rendering), `code.co_positions()` exposes it.
Deep Volume J explains the bytecode and code-object internals; this chapter is the record of the release that made tracebacks point at the exact expression, not just the line.
