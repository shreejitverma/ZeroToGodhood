# Chapter 282: Error Suggestions

## The constraint

For most of Python's history, a typo produced a message that was technically true and practically useless:

```
NameError: name 'collections_lenght' is not defined
```

Yes - `collections_lenght` is not defined.
But the variable one line up is `collections_length`, and the interpreter *had that name available* the whole time.
It knew every name in scope; it simply did not use that knowledge to help.
The fix - "you meant `collections_length`" - was left entirely to the programmer to spot, which for a subtle transposition in a long name is exactly the kind of thing eyes skip over.

The same held for a mistyped attribute (`config.timeut` when the attribute is `timeout`) and a mistyped import (`from math import sqt` when it is `sqrt`).
In each case the interpreter knew the set of valid candidates and the mistyped one, so it *could* compute which valid name was closest - it just did not.

Starting in Python 3.10 and extended through 3.12, CPython closed this gap: for undefined names, missing attributes, and failed imports, it computes the closest valid candidate and appends **"Did you mean: ...?"** to the error.
The constraint answered: **turn a dead-end error into a pointer at the fix**, using the knowledge the compiler already has about your program.

This is a two-track chapter.
The interpreter that produces these messages is Deep Volume J's subject.
What this chapter owns is the release arc: the day errors started suggesting corrections.

## What shipped

When a `NameError`, `AttributeError`, or `ImportError` fires on a mistyped identifier, the interpreter searches the relevant pool of valid names for the closest match (by edit distance) and, if one is close enough, appends a "Did you mean" suggestion.
Listing 282.1 shows this on today's interpreters, printing only the exception type and the suggestion clause (never the file paths some messages include) so the output is machine-independent.

Verified output (CPython 3.13.5):

```text
--- a mistyped NAME suggests the closest defined name ---
  NameError -> Did you mean: 'collections_length'?
  the interpreter compared the undefined 'collections_lenght' to the
  names in scope and found 'collections_length' one edit away. the
  bare 'not defined' now comes with the likely fix attached
--- a missing ATTRIBUTE suggests the closest real attribute ---
  AttributeError -> Did you mean: 'timeout'?
  Config has no 'timeut', but it has 'timeout' - so the AttributeError
  points you there. this catches the everyday obj.atribute typo the
  moment it runs, with the answer in the message
--- string/builtin methods get suggestions too ---
  AttributeError -> Did you mean: 'upper'?
  'hi'.uppr() suggests .upper(). the suggestion pool includes the
  type's real methods, so a misremembered method name is corrected
  for builtins as well as your own classes
--- a bad IMPORT name suggests the right one ---
  ImportError -> Did you mean: 'sqrt'?
  importing 'sqt' from math suggests 'sqrt'. (the full message also
  names the module's file path, which we omit here so the output is
  the same on every machine - the SUGGESTION itself is what matters)
--- no close match means no misleading suggestion ---
  NameError -> (no suggestion)
  when nothing is within a small edit distance, no 'Did you mean' is
  offered - the interpreter does not guess wildly. suggestions appear
  only when there is a genuinely close candidate
--- the constraint answered ---
  a name/attribute/import typo gave a technically-true but dead-end
  error and left the fix to you. from 3.10 through 3.12 CPython finds
  the closest valid name and appends 'Did you mean: ...?', so the
  error points at the correction. it is the compiler's extra knowledge
  of your program turned into a better message
```

## Why each part answers the constraint

**Name typos.**
The first block shows an undefined `collections_lenght` producing a `NameError` with "Did you mean: 'collections_length'?".
The interpreter compared the undefined name against the names in scope and found the one a single transposition away.
The bare "not defined" message now carries the likely fix - the knowledge the interpreter always had, finally surfaced.

**Attribute typos.**
The second block shows `Config().timeut` producing "Did you mean: 'timeout'?".
The object has no `timeut`, but it has `timeout`, and the `AttributeError` points there.
This catches the everyday `obj.atribute` typo the moment it runs, with the correction in the message rather than left to inspection.

**Builtins too.**
The third block shows `"hi".uppr()` suggesting `.upper()`.
The suggestion pool includes the type's real methods, so a misremembered method name is corrected for builtins - not just your own classes.
This matters because misremembering a standard method's exact spelling is common (`.uppercase` vs `.upper`, `.length` vs `len`), and the suggestion resolves it.

**Import typos.**
The fourth block shows `from math import sqt` suggesting `sqrt`.
The interpreter searches the module's actual names for the closest match.
(The full message also names the module's file path, which the listing omits so the output is identical on every machine - but the suggestion itself is the useful part.)

**No wild guesses.**
The fifth block shows the restraint that keeps suggestions trustworthy: `zzzzzz`, with nothing like it in scope, gets *no* suggestion.
The interpreter only offers a correction when a candidate is within a small edit distance; it does not guess wildly.
This is what makes the feature reliable - when it suggests something, the suggestion is genuinely close, so you can trust it rather than second-guess it.

## The two-track note

The interpreter machinery - how the error path gathers the candidate names, computes edit distances, and decides whether a candidate is close enough - is Deep Volume J's to develop.
What the timeline records is a multi-release arc: 3.10 introduced suggestions for names and attributes, and later releases (through 3.12) extended and refined them, including for imports.
The modern consequence, verified above, is that a large fraction of everyday typos now come with the correction attached - one of the most broadly beneficial usability improvements in recent Python, because it shortens the most common debugging loop of all: "why is this name wrong?"

## Where this lands

Error suggestions are a feature you benefit from simply by running a recent Python: your typos now tell you what you probably meant.
Read the "Did you mean" clause - it is right far more often than not, precisely because the interpreter only offers it for close matches.
When there is no suggestion, that itself is information: the name you used is not a near-miss of anything valid, so the problem is likely conceptual (a missing import, a wrong scope) rather than a spelling slip.
Deep Volume J explains the interpreter internals; this chapter is the record of the release arc that turned dead-end errors into pointers at the fix.
