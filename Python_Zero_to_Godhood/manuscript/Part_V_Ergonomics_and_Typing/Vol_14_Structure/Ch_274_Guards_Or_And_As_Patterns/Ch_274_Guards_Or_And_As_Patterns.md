# Chapter 274: Guards, Or, and As Patterns

## The constraint

The previous four chapters built up structural pattern matching: the fundamentals (Chapter 270), and sequence, mapping, and class patterns (Chapters 271-273).
Those match *shape* - and shape alone is not quite enough for a complete dispatch tool.
Three things remain that shape cannot express:

A pattern can check that a value is a `Point(x, y)`, but it cannot check a *relationship* between `x` and `y` - "is `x` equal to `y`?", "is the value in this range?", any predicate over the bound values.

A pattern can match one shape, but writing several near-identical cases for alternatives - `case "sat":` then `case "sun":` with the same body - is repetitive.

And a pattern can destructure a value into its parts, but sometimes you need *both* the parts *and* the intact original, to pass it along.

Python 3.10 completes `match` with three constructs for exactly these: **guards**, **OR-patterns**, and **as-patterns**.
Together with the structural patterns, they make `match` a full dispatch tool.

This chapter closes the pattern-matching facets of the 3.10 release; the mechanism is Deep Volume B's.

## What shipped

A *guard* (`case pattern if condition:`) adds a boolean condition evaluated with the bound names in scope.
An *OR-pattern* (`case a | b:`) matches any of several alternatives in one case.
An *as-pattern* (`case pattern as name:`) binds the whole value a sub-pattern matched.
Listing 274.1 shows all three on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- a GUARD adds a condition the pattern alone cannot check ---
  quadrant(Point(x=1, y=2)) : quadrant I
  quadrant(Point(x=-1, y=3)) : quadrant II
  quadrant(Point(x=5, y=5)) : on the line y = x
  quadrant(Point(x=2, y=-1)) : somewhere else
  `case Point(x, y) if x == y:` matches the shape AND tests a
  condition on the bound values. the guard runs only if the pattern
  matched; if the guard is false, matching CONTINUES to the next case
--- the guard sees the BOUND names - relationships, ranges, predicates ---
  classify(-4) : negative
  classify(10) : even
  classify(7) : odd
  a guard is arbitrary Python, evaluated with the captured names in
  scope. it expresses what patterns cannot: <, %, membership, any
  predicate over the values the pattern pulled out
--- OR-patterns: one case, several alternatives with | ---
  day_type('sat') : weekend
  day_type('wed') : weekday
  day_type('xyz') : unknown
  `case 'sat' | 'sun':` matches if the value matches ANY alternative,
  collapsing what would be several near-identical cases into one.
  each alternative is a full pattern, not just a literal
--- OR-patterns can bind, if every alternative binds the same name ---
  unwrap([9])  : single value 9
  unwrap((7,)) : single value 7
  every branch of an OR-pattern must bind the SAME names, so whichever
  alternative matched, x is defined afterwards. here 'a one-element
  list or tuple' is one case that works for both
--- AS-patterns: keep the whole matched value AND its parts ---
  origin object: Point(x=0, y=0)
  point Point(x=3, y=4) with x=3, y=4
  `case Point(x, y) as p` binds x and y from inside AND binds the
  whole Point to p. you get the destructured parts and the intact
  value together - useful when you need to pass the original along
--- the constraint answered ---
  patterns match shape; guards add conditions on the bound values;
  OR-patterns fold alternatives into one case; as-patterns keep the
  whole value alongside its parts. with the structural patterns of
  Chapters 270-273, these complete match/case as a full structural
  dispatch tool - shape, condition, alternation, and capture together
```

## Why each part answers the constraint

**Guards add conditions on bound values.**
The first block shows `quadrant` combining a pattern with a condition: `case Point(x, y) if x == y:` matches the `Point` shape *and* tests that `x` equals `y`.
The guard runs only if the pattern matched, and - crucially - if the guard is *false*, matching does not stop; it *continues to the next case*.
This is what lets a guard refine a match without swallowing values that should fall through to a later branch.

**Guards are arbitrary predicates.**
The second block shows the generality: `classify` uses guards for `v < 0`, `v % 2 == 0`, and falls through to odd.
A guard is arbitrary Python evaluated with the captured names in scope, so it expresses everything patterns cannot - comparisons, arithmetic, membership, any predicate over the values the pattern pulled out.
The pattern extracts the values; the guard reasons about them.

**OR-patterns fold alternatives.**
The third block shows `case "sat" | "sun":` matching if the value matches *any* alternative, so `day_type` handles weekend days in one case instead of two.
Each alternative is a full pattern, not just a literal, so you can alternate over shapes, types, or structures - collapsing several near-identical cases into one.

**OR-patterns can bind, consistently.**
The fourth block shows OR-patterns with capture: `case [x] | (x,):` matches a one-element list *or* a one-element tuple, binding `x` either way.
The rule that makes this sound is that *every* alternative must bind the *same* names, so that whichever alternative matched, the bound names are defined afterward.
Here "a one-element list or tuple" is a single case that works for both containers and leaves `x` bound.

**As-patterns keep the whole and the parts.**
The fifth block shows `case Point(x, y) as p:` binding `x` and `y` from *inside* the pattern *and* binding the whole `Point` to `p`.
You get the destructured parts and the intact original together - useful when a branch needs both the extracted fields and the complete value, for instance to pass the original object along after inspecting its parts.

## The two-track note

How the interpreter evaluates guards (after a structural match, with bindings in scope, falling through on false), compiles OR-patterns (trying alternatives left to right, enforcing consistent bindings), and handles as-patterns (binding the sub-pattern's subject) is Deep Volume B's to develop.
What the timeline records is the completing facet of the 3.10 release: the guards, alternation, and whole-value capture that turn structural matching into full dispatch.
The modern consequence, verified above, is that `match` handles shape (the structural patterns), condition (guards), alternation (OR-patterns), and capture (as-patterns) together - the full vocabulary a dispatch construct needs.

## Where this lands, and the close of Structure

Guards, OR-patterns, and as-patterns are the finishing pieces of structural pattern matching.
Reach for a guard when a match depends on a relationship or predicate a pattern cannot express - and remember a false guard falls through to the next case.
Reach for an OR-pattern to fold alternatives into one branch, ensuring each alternative binds the same names.
Reach for an as-pattern when a branch needs both the destructured parts and the intact value.
Deep Volume B explains the evaluation; this chapter closes the pattern-matching facets of the 3.10 release.

This closes Volume 14, Structure, and with it Part V's timeline volumes.
The volume was devoted to a single feature - structural pattern matching - because it was large enough to warrant one, and because it is the clearest payoff of the PEG parser (Chapter 15) that replaced the old LL(1) parser: `match` and `case` as soft keywords, and the rich pattern grammar, were simply not expressible before.
Across its chapters - fundamentals, sequence, mapping, class patterns, and the guards and combinators here - the volume traced how Python gained declarative dispatch on the shape of data.
Part V's thesis was that once the runtime stabilized, the arguments moved to the surface - what code should look like - and pattern matching, alongside f-strings, dataclasses, and the type system, was the largest of those surface changes.
The book continues into Part VI, where the arguments move again, this time to performance.
