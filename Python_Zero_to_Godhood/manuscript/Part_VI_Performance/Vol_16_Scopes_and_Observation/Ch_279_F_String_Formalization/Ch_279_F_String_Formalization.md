# Chapter 279: F-String Formalization

## The constraint

When f-strings arrived in 3.6 (Chapter 12), they were not parsed by Python's real parser.
They were handled by a separate, limited *sub-parser* that ran on the string's contents, and that sub-parser carried a set of frustrating, arbitrary restrictions that had nothing to do with what the programmer wanted to express.

You could not reuse the *same* quote character inside the braces: `f"{data["name"]}"` was a `SyntaxError`, because the inner `"` was seen as closing the f-string.
You had to switch the inner subscript to single quotes - `f"{data['name']}"` - a workaround that failed as soon as you nested one more level.
You could not put a *backslash* in the expression part, so `f"{'\n'.join(rows)}"` was forbidden, forcing an awkward temporary variable.
Comments were banned, and nesting was shallow.

None of these limits reflected anything meaningful about f-strings; they were artifacts of the separate sub-parser's simplicity.
The constraint Python 3.12 (2023, PEP 701) answered: **fold f-strings into the real grammar**, so the braces accept *any* valid Python expression, and the arbitrary restrictions disappear.

This was made possible by the PEG parser (Chapter 15) that replaced the old LL(1) parser - a formalized f-string grammar was simply not expressible before it.

This is a two-track chapter.
The tokenizer and parser are Deep Volume J's subject.
What this chapter owns is the release: the day an f-string's braces could hold anything a normal expression can.

## What shipped

PEP 701 re-implemented f-strings as part of the PEG grammar, removing the quote-reuse, backslash, comment, nesting, and single-line restrictions - without changing what f-strings *mean*.
Listing 279.1 shows the newly-allowed forms on today's interpreters (all of which post-date 3.12, so these forms parse).

Verified output (CPython 3.13.5):

```text
--- reuse the SAME quote character inside the braces ---
  f'{data["name"]} ...' -> Ada is a engineer
  the inner double quotes no longer collide with the f-string's outer
  ones. before 3.12 you HAD to switch the inner subscript to single
  quotes; now the same quote nests freely
--- backslashes are allowed in the expression part ---
  f"{'\n'.join(rows)}" produced 3 lines
  a backslash escape like '\n' inside the braces used to be a
  SyntaxError, forcing an awkward temporary variable. now the escape
  works directly in the expression
--- arbitrary nesting of f-strings ---
  nested f-string result : '      42'   (right-aligned in 8)
  f-strings nest to any depth now - here an inner f-string computes a
  width-aligned value that the outer one embeds. the old sub-parser
  choked on deep nesting; the real grammar does not
--- multi-line expressions inside the braces ---
  a multi-line f-string expression summed evens to : 6
  the expression between the braces can now span multiple physical
  lines and be laid out for readability - impossible under the old
  single-line-only f-string parser
--- it is the SAME formatting, just without the parse limits ---
  a normal f-string still works exactly as before : 1,234.50
  PEP 701 changed only what the PARSER accepts inside the braces, not
  what f-strings MEAN. every old f-string still behaves identically;
  the new forms are additions, not changes (Chapter 246's mini-language
  is untouched)
--- the constraint answered ---
  f-strings were parsed by a separate, restricted sub-parser that
  banned same-quote reuse, backslashes, comments, and deep nesting.
  PEP 701 (3.12) folded them into the real PEG grammar, so the braces
  accept ANY valid expression. the arbitrary limits are gone; the
  meaning is unchanged
```

## Why each part answers the constraint

**Same-quote reuse.**
The first block shows `f"{data["name"]} is a {data["role"]}"` working - the inner double quotes no longer collide with the f-string's outer ones.
This was the single most common f-string annoyance, forcing a switch to single quotes for any inner string, and it is simply gone.

**Backslashes in expressions.**
The second block shows `f"{'\n'.join(rows)}"` working - a backslash escape inside the braces, which used to be a `SyntaxError` requiring a temporary variable.
Now common idioms like joining on a newline work directly in the expression.

**Arbitrary nesting.**
The third block shows an f-string nested inside another: `f"{f'{value:>{width}}'}"`, where the inner f-string computes a width-aligned value the outer one embeds.
The old sub-parser choked on deep nesting; the real grammar handles any depth, which matters for building formatted strings compositionally.

**Multi-line expressions.**
The fourth block shows the expression between the braces spanning multiple physical lines - a `sum(...)` laid out across several lines for readability.
The old single-line-only parser made this impossible; now a complex embedded expression can be formatted like any other code.

**Meaning unchanged.**
The fifth block makes the crucial point: a normal f-string, `f"{price:,.2f}"`, still works exactly as before.
PEP 701 changed only what the *parser accepts* inside the braces, not what f-strings *mean*.
Every existing f-string behaves identically, and the format mini-language (Chapter 246) is untouched - the new forms are purely additive.

## The two-track note

The tokenizer and parser changes that made this possible - representing f-strings as a sequence of tokens the PEG grammar understands, rather than a monolithic string handed to a sub-parser - are Deep Volume J's to develop, and they build directly on the PEG parser of Chapter 15.
What the timeline records is the release act: in 3.12, PEP 701 formalized f-strings in the grammar, removing the arbitrary restrictions.
The modern consequence, verified above, is that f-string braces accept any expression - same-quote strings, backslashes, nested f-strings, multi-line expressions - and the workarounds those restrictions forced are no longer needed.

## Where this lands

F-string formalization is a quiet cleanup with a real daily payoff: the small frustrations that made you rewrite an f-string to appease the parser are gone.
Reuse quotes freely, use backslash escapes in the braces, nest f-strings when it reads well, and lay out a complex embedded expression across lines when clarity demands it.
The one caveat is compatibility direction: code using these forms requires 3.12+, so a library supporting older Pythons must still avoid them.
Deep Volume J explains the tokenizer and parser; Chapter 15 explains the PEG parser this rests on; this chapter is the record of the release that made an f-string's braces hold any valid expression.
