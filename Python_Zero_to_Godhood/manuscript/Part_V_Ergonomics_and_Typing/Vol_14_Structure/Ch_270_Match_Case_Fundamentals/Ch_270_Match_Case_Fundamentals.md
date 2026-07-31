# Chapter 270: Match Case Fundamentals

## The constraint

Code that branches on the *shape* of data - is this value a particular constant, an instance of a certain type, a sequence of a certain length, a mapping with certain keys? - was, for Python's whole history, a long `if`/`elif` chain, often tangled with `isinstance` checks and manual unpacking.
It was verbose, and the verbosity hid bugs: a forgotten branch, an unpacking that assumed the wrong structure, a check in the wrong order.

Many languages answer this with a `switch` statement.
But a C-style `switch` is weak: it only compares a single value against constants, requires explicit `break` to avoid fall-through, and cannot look *inside* a value.
It would handle "is `code` equal to 200 or 404" but not "is this a two-element sequence whose first element is zero, and if so, bind the second."

Python 3.10 (2021, PEP 634-636) introduced something more powerful: **structural pattern matching**, a `match` statement that tests the *structure* of a value and *binds* parts of it in the same step.
The constraint it answered: **replace shape-testing `if`/`elif` chains with a construct that matches structure and destructures in one operation.**

This volume is devoted to pattern matching, because it is the single feature large enough to warrant one - and the PEG parser (Chapter 15) is what made its syntax possible at all.
This first chapter covers the fundamentals; the following chapters cover sequence, mapping, and class patterns, and the guards and combinators that complete it.

This is a two-track chapter.
Evaluation and control flow are Deep Volume B's.
What this chapter owns is the release: the day Python gained matching on shape.

## What shipped

The `match` statement takes a subject and tries a series of `case` patterns top to bottom, running the first that matches.
The fundamental patterns are *literal* patterns (compare to a constant), *capture* patterns (bind a name), *class* patterns (match by type), and the *wildcard* `_` (match anything).
Listing 270.1 shows these on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- literal patterns: match a value against constants ---
  http_status(200) : OK
  http_status(404) : Not Found
  http_status(500) : Server Error
  http_status(418) : Unknown
  each `case 200:` compares code to a literal, like a switch. the
  final `case _:` is the wildcard - it matches anything, serving as
  the default branch
--- the capture pattern BINDS a name to the matched value ---
  unpack_point((0, 0)) : origin
  unpack_point((0, 5)) : on the y-axis at 5
  unpack_point((3, 0)) : on the x-axis at 3
  unpack_point((2, 4)) : at (2, 4)
  `case (0, y)` matches any pair whose first element is 0 AND binds
  the second to y in one step. matching and destructuring together -
  the thing a switch cannot do
--- matching on TYPE, not just value ---
  describe(0) : zero
  describe(42) : the integer 42
  describe('hi') : the string 'hi'
  describe([1, 2]) : something else: [1, 2]
  `case int():` matches any integer, `case str() as s:` any string
  (binding it to s). match tests the KIND of value, so one statement
  handles 'zero', 'any int', 'any str', and 'anything else' by shape
--- match does NOT fall through - exactly one case runs ---
  after check(1), branches taken : ['one']
  unlike C's switch, there is no fall-through and no `break` needed:
  the FIRST matching case runs, then the whole statement is done.
  cases are tried top to bottom, so order more specific before general
--- a name alone is a CAPTURE, not a comparison (the classic gotcha) ---
  classify('red')  : matched the literal red
  classify('blue') : captured as 'blue'
  a bare name like `other` is a CAPTURE pattern: it always matches and
  binds. it does NOT compare against a variable named other. to match
  against a constant you need a literal or a dotted name (Enum.RED)
--- the constraint answered ---
  testing the shape of data was long if/elif chains, and a C switch
  only compares to constants. match/case (3.10) matches STRUCTURE and
  BINDS parts in one step: literals, type patterns, captures, and _
  for default. it is structural dispatch, not a fall-through switch
```

## Why each part answers the constraint

**Literal patterns and the wildcard.**
The first block shows the switch-like use: `case 200:` compares the subject to a literal, and `case _:` is the wildcard that matches anything, serving as the default.
This is the familiar part - matching a value against constants - and on its own it is a cleaner spelling of an `if`/`elif` chain over equality.

**Capture patterns bind.**
The second block shows the capability a switch lacks.
`case (0, y)` matches any two-element sequence whose first element is `0` *and* binds the second element to `y` - in one step.
The `unpack_point` function classifies points by matching and destructuring together: `(0, 0)` is the origin, `(0, y)` is on the y-axis with `y` captured, and so on.
Matching and destructuring in a single operation is the essence of structural pattern matching.

**Type patterns match by kind.**
The third block shows matching on *type*: `case int():` matches any integer, `case str() as s:` matches any string and binds it to `s`.
So `describe` handles "zero" (a literal), "any int," "any str," and "anything else" (the wildcard) in one statement, dispatching on the *kind* of value rather than a specific value.
This replaces an `isinstance` ladder with declarative patterns.

**No fall-through.**
The fourth block establishes a key semantic difference from C's `switch`: there is no fall-through and no `break`.
The *first* matching case runs, and then the entire `match` statement is done.
Cases are tried top to bottom, which means ordering matters - put more specific patterns before more general ones, or the general one will shadow the specific.

**The capture gotcha.**
The fifth block covers the single most important pitfall.
A bare name in a pattern - `case other:` - is a *capture* pattern: it always matches and binds the subject to that name.
It does **not** compare the subject against a variable named `other`.
So `classify` matches `"red"` against the *literal* `"red"`, but `case other:` captures anything else.
To match against a named constant, you need a literal or a *dotted* name (like `Color.RED` or `module.CONSTANT`), which are treated as value patterns.
This distinction - bare name captures, dotted name compares - trips up nearly everyone once, and understanding it is essential to using `match` correctly.

## The two-track note

Evaluation, control flow, and how the interpreter compiles the `match` statement into pattern-testing bytecode are Deep Volume B's to develop; the syntax itself was only expressible because of the PEG parser (Chapter 15), which replaced the LL(1) parser that could not have handled `match` and `case` as soft keywords.
What the timeline records is the release act: in 3.10, PEP 634-636 added structural pattern matching.
The modern consequence, verified above, is that shape-based dispatch - on literals, types, and structure, with binding - is a first-class statement, and the "bare name captures" rule is the one piece of its semantics every user must internalize.

## Where this lands

`match`/`case` is Python's structural dispatch construct, and this chapter covered its foundation: literal patterns for constants, capture patterns for binding, class patterns for type, the wildcard for default, top-to-bottom first-match semantics with no fall-through, and the crucial bare-name-captures rule.
Reach for `match` when you are branching on the *shape* of data and would otherwise write an `if`/`elif` chain with unpacking; keep an `if` for simple boolean conditions where there is no structure to match.
The following chapters build on this foundation with sequence patterns, mapping patterns, class patterns, and the guards and combinators that make `match` genuinely expressive.
Deep Volume B explains the evaluation; this chapter is the record of the release that added matching on shape.
