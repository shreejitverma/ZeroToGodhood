# Chapter 231: Conditional Expressions

## The constraint

For its first fifteen years, Python had no ternary operator.
Every other language the newcomer knew had `cond ? a : b`, and Python simply did not - not because the need was absent, but because no proposed syntax had ever satisfied Guido van Rossum that it was worth the grammar.
The language shipped `if`/`else` as a *statement*, and a statement cannot appear inside a `return`, a function argument, or a comprehension.
So whenever a programmer needed to choose a value inline, they reached for a workaround, and the workaround the community settled on was quietly, dangerously wrong.

The idiom was `cond and a or b`.
It leans on short-circuit evaluation: if `cond` is true, `cond and a` yields `a`, and `a or b` yields `a`; if `cond` is false, `cond and a` yields `cond` (falsy), and `... or b` yields `b`.
It works - until `a` is itself falsy.
When `cond` is true but `a` is `0`, `''`, `[]`, or `None`, `cond and a` evaluates to that falsy `a`, and then `... or b` steps in and returns `b` instead.
The expression silently returns the wrong branch, and it does so only for certain data values, which is the worst kind of bug: invisible in every test that happened to use truthy values.

The constraint Python 2.5 (2006, PEP 308) finally answered was this: **give the language a correct one-expression conditional, and choose a syntax good enough to justify fifteen years of resistance.**

This is a two-track chapter.
Expression evaluation - short-circuiting, operand order, what "an expression" is versus a statement - belongs to Deep Volume B (the execution and evaluation model).
What this chapter owns is the release: the day the ternary arrived, the specific word order PEP 308 chose, and the retirement of the `and/or` trap.

## What shipped

PEP 308 chose a form deliberately unlike C's `?:`.
Instead of `cond ? a : b`, Python writes `a if cond else b` - **value first, condition second, fallback last**.
Listing 231.1 shows why that order and that correctness matter, on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- the conditional expression: value first, condition second ---
  'odd' if n % 2 else 'even'  (n=7) : odd
  abs via expression : 7
  reads left to right as English: the USUAL value, the condition
  that qualifies it, then the fallback. one expression, so it works
  where a statement can't - in a return, an arg, a comprehension
--- why it was needed: the `and/or` fake has a silent bug ---
  cond=True, a=0, b=99
  cond and a or b : 99   <- WRONG (wanted a=0, got b=99)
  a if cond else b: 0   <- correct
  `cond and a or b` collapses to `b` whenever a is FALSY, even with
  cond true - because `True and 0` is 0, then `0 or 99` is 99. the
  ternary has no such hole: it selects on the CONDITION, not on
  whether the chosen value happens to be truthy
--- it is an expression, so it nests where statements cannot ---
  classify(-3), classify(0), classify(5) : neg, zero, pos
  inside a comprehension : ['even', 'odd', 'even', 'odd', 'even']
  because it is an expression it goes inside return, inside a
  comprehension, inside a function argument - places an if-STATEMENT
  cannot reach. that is the whole reason a ternary earns its keep
--- only the chosen branch is evaluated (short-circuit) ---
  result : 1, evaluated branches : ['A']
  the else branch never ran - the expression evaluates ONLY the
  selected side, like if/else, so putting an expensive or unsafe
  call in the untaken branch is fine (Deep B's evaluation rules)
--- the constraint answered ---
  Python lacked a ternary and the `and/or` workaround was quietly
  wrong for falsy values. PEP 308 added `a if cond else b` - value
  first so the common case reads first - giving a correct, nestable,
  short-circuiting one-expression conditional and ending the trap
```

## Why each part answers the constraint

**The word order is the design.**
`a if cond else b` puts the *usual* result first and the qualifying condition second, which reads like the English sentence "odd, if n is odd, else even."
This was the crux of PEP 308's long deliberation: C's `cond ? a : b` leads with the test, but Python's authors judged that the common-case value is what the reader wants first, with the condition as a modifier.
Whether one prefers it or not, the order is not arbitrary - it is the specific choice that ended fifteen years of "no."

**Correctness is the reason it exists.**
The second block is the whole justification.
With `cond=True, a=0, b=99`, the old `cond and a or b` returns `99` - the wrong branch - because `True and 0` is `0` and `0 or 99` is `99`.
The conditional expression returns `0`, correctly, because it selects on the *condition*, never consulting whether the chosen value happens to be truthy.
This is not a style improvement; it is a correctness fix for a bug that hid in production code for years, surfacing only when the "true" branch's value was falsy.

**Being an expression is the capability.**
The third block shows the thing a statement could never do: the conditional nests inside a `return` (`classify` chains two of them for a three-way choice), and inside a comprehension (`"even" if k % 2 == 0 else "odd"` per element).
An `if`-statement cannot appear in either place.
This is why the feature earns its keep - not because it is shorter than an `if`/`else` block, but because it reaches into expression positions where a block is syntactically impossible.

**Short-circuiting makes the untaken branch safe.**
The fourth block confirms the conditional evaluates *only* the selected side: with the condition true, only `side("A", 1)` runs and the log shows `['A']` - the `else` branch never executed.
This matters for correctness as much as speed: you can put an expensive computation, or one that would raise on the current data, in the branch that will not be taken, exactly as you would with a full `if`/`else`.
Deep Volume B owns the evaluation semantics; the release fact is that the ternary honors them.

## The two-track note

The evaluation model - what short-circuiting means, why only one operand runs, how the expression composes with the rest of the grammar - is Deep Volume B's to formalize.
The `and/or` trap is a special case of Python's truthiness protocol (Chapter 229) meeting boolean short-circuiting, and Deep B is where that interaction is laid out in full.
What the timeline records is narrower: in 2006, after fifteen years of deliberate absence, PEP 308 added a ternary in a distinctive value-first order, and in doing so retired a workaround that had been silently returning wrong answers for falsy operands.
The modern consequence, verified above, is that the correct form and the buggy form still sit one line apart, and the correct one has been in the language since 2.5.

## Where this lands

The conditional expression is one of the clearest cases in the language's history of restraint paying off: Python waited until it had a syntax worth keeping rather than shipping C's `?:` early.
Reach for `a if cond else b` for a genuine two-way value choice inline; keep the full `if`/`else` block when the branches do more than produce a value.
And never write `cond and a or b` again - it is the trap this release was built to close.
Deep Volume B explains the evaluation; this chapter is the record of the day Python decided its ternary was finally good enough to add.
