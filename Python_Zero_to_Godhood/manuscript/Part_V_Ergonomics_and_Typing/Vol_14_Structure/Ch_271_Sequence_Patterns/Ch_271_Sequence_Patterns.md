# Chapter 271: Sequence Patterns

## The constraint

Chapter 270 covered the fundamentals of `match`/`case`.
This chapter covers the first structural pattern that shows why "structural" matters: the *sequence* pattern, which matches a value by its shape *as a sequence* - its length, its fixed elements, and a variable-length rest.

The code sequence patterns replace is a familiar mess: parsing a list of tokens, a command and its arguments, a structured record.
Before `match`, this meant nested `len()` checks and index arithmetic:

```python
if len(command) == 0:
    ...
elif len(command) == 2 and command[0] == "go":
    direction = command[1]
    ...
elif command[0] == "say":
    words = command[1:]
    ...
```

Every branch re-checks the length, re-indexes, and re-slices, and every one is a chance to get an off-by-one or a wrong index wrong.
The constraint sequence patterns answer: **match a value's length and element structure and bind its parts in one declarative pattern**, so "dispatch on how many parts and what they are" stops being index math.

This is a two-track chapter within the pattern-matching volume; the mechanism is Deep Volume B's, and this is the sequence-pattern facet of the 3.10 release.

## What shipped

A sequence pattern like `["go", direction]` matches a sequence of the right length whose fixed elements match and binds the captured ones; a starred element (`*rest`) captures a variable-length remainder.
Crucially, sequence patterns match lists, tuples, and other sequences - but *not* `str` or `bytes`.
Listing 271.1 shows this on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- match by length and fixed elements ---
  run([]) : empty command
  run(['quit']) : quitting
  run(['go', 'north']) : going north
  run(['move', 3, 4]) : moving to (3, 4)
  each case fixes a LENGTH and some element values/positions. `case
  ['go', direction]` means 'a 2-element sequence starting with go',
  binding the second element - length and shape checked together
--- the starred pattern captures a variable-length REST ---
  run(['say', 'hello', 'there']) : saying: hello there
  run(['say']) : saying: 
  run(['dance', 'a', 'b', 'c']) : unknown action 'dance' with args ['a', 'b', 'c']
  `['say', *words]` matches 'say' followed by ANY number of elements,
  binding them as a list. one starred name per pattern, exactly like
  the assignment unpacking of Chapter 244 - now inside match
--- fixed elements around a star: first, middle, last ---
  ends([1, 2, 3, 4]) : first=1, last=4
  ends([9]) : single=9
  ends([]) : empty
  the star can sit BETWEEN fixed patterns, so `[first, *_, last]`
  grabs the two ends and ignores the middle with *_ (a starred
  wildcard). structural, length-aware destructuring in one line
--- the crucial rule: strings and bytes do NOT match sequence patterns ---
  kind([1, 2]) : a 2-element sequence: 1, 2
  kind('ab')   : a string (NOT torn into characters)
  'ab' has two characters, but a sequence pattern does NOT match it -
  str and bytes are excluded on purpose, so you never accidentally
  destructure a string into characters. it falls to `case str()`
--- tuples and lists match the same patterns (any Sequence) ---
  point((1, 2))    : 2D (1, 2)
  point([1, 2, 3]) : 3D (1, 2, 3)
  the pattern `[x, y]` is about SEQUENCE STRUCTURE, not the literal
  bracket type - it matches a tuple or a list alike. write it with
  either brackets or parens; they mean the same in a pattern
--- the constraint answered ---
  dispatching on 'how many parts and what they are' meant nested
  len() checks and index math. sequence patterns (3.10) match a
  value's length and element structure and bind the parts - with a
  starred rest, mid-sequence stars, and a safety rule that str/bytes
  never match, so strings are not silently split
```

## Why each part answers the constraint

**Length and fixed elements, together.**
The first block shows `run` parsing a command list: `[]` matches the empty command, `["quit"]` matches exactly one element equal to `"quit"`, `["go", direction]` matches a two-element sequence starting with `"go"` and binds the second.
Each case checks a length *and* some element values/positions in one pattern - the nested `len()`-and-index logic collapsed into a declarative shape.

**The starred rest.**
The second block shows `["say", *words]` matching `"say"` followed by *any number* of elements, bound as a list.
`run(["say", "hello", "there"])` captures `["hello", "there"]`; `run(["say"])` captures the empty list.
This is the same starred unpacking as assignment (Chapter 244), now available inside a pattern - one starred name per pattern, capturing the variable-length remainder.

**Stars between fixed patterns.**
The third block shows the star sitting *between* fixed elements: `[first, *_, last]` grabs the two ends and ignores the middle (`*_` is a starred wildcard).
So `ends` extracts the first and last of a sequence regardless of its length, in one line - structural, length-aware destructuring that would otherwise be `seq[0]` and `seq[-1]` with a length guard.

**The str/bytes exclusion.**
The fourth block covers the rule that prevents a whole class of bugs.
A string like `"ab"` *is* a two-character sequence, but a sequence pattern deliberately does **not** match `str` or `bytes`.
So `kind("ab")` does not match `case [a, b]` and torn into characters - it falls through to `case str()`.
This exclusion is intentional and important: without it, every sequence pattern would risk accidentally destructuring a string into its characters, a silent and confusing error.
Strings and bytes are matched as scalar values, not sequences.

**Any sequence, not a specific bracket.**
The fifth block shows that the pattern is about sequence *structure*, not the literal bracket type: `[x, y]` matches both `(1, 2)` and `[1, 2]`.
You can write the pattern with brackets or parentheses interchangeably; both match any sequence (list, tuple, and other `Sequence` types) of the right shape.
The pattern describes structure, not container type.

## The two-track note

How the interpreter tests a subject against a sequence pattern - checking it is a sequence (but not str/bytes), verifying the length, matching and binding elements - is Deep Volume B's to develop, and it connects to the abstract-base-class machinery (Chapter 235) that defines what counts as a `Sequence`.
What the timeline records is the sequence-pattern facet of the 3.10 release: length-and-structure matching with starred capture, and the deliberate str/bytes exclusion.
The modern consequence, verified above, is that parsing token lists, command arguments, and structured records is declarative pattern matching rather than index arithmetic, with the string-safety rule protecting against the most common accidental misuse.

## Where this lands

Sequence patterns are the workhorse of `match` for anything list- or tuple-shaped: command parsers, token streams, structured tuples, AST nodes.
Reach for them when you dispatch on a sequence's length and element structure and want to bind the parts in the same step.
Use a starred name to capture a variable-length rest, `*_` to skip a middle, and remember the safety rule - strings and bytes never match sequence patterns, so match them with `case str()`/`case bytes()` when you mean the scalar value.
Deep Volume B explains the matching mechanism; this chapter is the record of the sequence-pattern facet of structural pattern matching.
