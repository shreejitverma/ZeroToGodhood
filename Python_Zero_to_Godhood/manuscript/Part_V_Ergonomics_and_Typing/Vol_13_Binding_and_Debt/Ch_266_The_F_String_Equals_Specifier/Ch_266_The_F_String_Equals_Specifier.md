# Chapter 266: The F-String Equals Specifier

## The constraint

The single most common debugging line in any language is "print this variable with its name":

```python
print("count =", count)
```

Look at what that line makes you do: you write the name `count` *twice* - once as a text label, once as the value to print.
The two are not linked; they are two independent pieces of text that happen to say the same thing today.
And that is the bug.
Rename the variable and update only the value, and the label lies.
Copy-paste the line to debug a *different* variable, change the value expression, and forget to change the label - now it prints `count = 30` when the value is actually `subtotal`.
These lying labels are a real and maddening source of debugging confusion: the output actively misleads you about what it is showing.

The redundancy is the root cause.
The label and the value both come from the same expression, so having to type it twice is not just tedious - it is the opportunity for them to disagree.

The constraint Python 3.8 (2019) answered: **generate the label from the expression itself, so the name and the value can never diverge** - making the most common debug print correct by construction.

This is a two-track chapter.
String formatting and f-strings are Deep Volume D's and Chapter 246's territory.
What this chapter owns is the release: the day the ubiquitous debug print stopped being able to lie.

## What shipped

The `=` specifier in an f-string - `f"{count=}"` - expands to the *text of the expression*, an `=`, and the value's `repr`, all derived from the single expression you wrote.
It works on arbitrary expressions, composes with format specs, and preserves whitespace around the `=`.
Listing 266.1 shows all of this on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- f"{expr=}" prints the expression text AND its value ---
  f'{count=}' -> count=42
  f'{name=}'  -> name='Ada'
  one expression produced both the label 'count=' and the value 42.
  you wrote `count` once; the = specifier echoed the source text and
  appended its repr. no more typing the name twice
--- the bug it prevents: a label that lies ---
  hand-written, miscopied : total = 30   <- label LIES
  with = specifier        : subtotal=30   <- label cannot lie
  the manual 'total =', subtotal prints the WRONG name (a real bug
  from renaming or pasting). the = form derives the label from the
  expression, so it always matches the value shown
--- it works on whole EXPRESSIONS, not just variable names ---
  sorted(xs)=[1, 2, 3]
  len(xs) * 2=6
  xs[0] + xs[1]=4
  the text captured is the whole expression source, and the value is
  its result. great for 'what does this actually evaluate to?' checks
  without inventing a label
--- format specs still apply after the = ---
  pi=3.142   (round to 3 places, still labelled)
  ratio=25%   (as a percent)
  put a normal format spec after the =, and it formats the VALUE while
  keeping the generated label. the debug helper composes with the
  whole format mini-language (Chapter 246)
--- whitespace around = is preserved in the label ---
  f'{x = }' -> x = 5
  spaces you put around the = are echoed, so you control the look
  ('x=5' vs 'x = 5'). a tiny touch, but it means the output reads
  exactly how you wrote the expression
--- the constraint answered ---
  the everyday debug print made you type a variable's name twice -
  once as a label, once as the value - and the two drifted apart into
  lying labels. the f-string = specifier (3.8) generates the label
  from the expression itself, so name and value can never disagree.
  the most common debug line became correct by construction
```

## Why each part answers the constraint

**One expression, both label and value.**
The first block shows the core: `f"{count=}"` produces `count=42`, and `f"{name=}"` produces `name='Ada'` (note the `repr`, with quotes, which is what you want for debugging).
You wrote `count` once; the `=` specifier echoed the source text as the label and appended the value.
The redundancy is gone.

**The lying label, prevented.**
The second block shows the exact bug and its fix side by side.
The hand-written, miscopied `"total ="` prints alongside `subtotal`'s value `30` - the label says `total` but the number is `subtotal`'s, a lie born of a rename or paste.
The `=` form, `f"{subtotal=}"`, derives the label from the expression, so it *cannot* disagree with the value shown.
This is the correctness argument: not merely less typing, but a label that is guaranteed accurate.

**Whole expressions, not just names.**
The third block shows it works on arbitrary expressions: `f"{sorted(xs)=}"` prints `sorted(xs)=[1, 2, 3]`, and similarly for `len(xs) * 2` and `xs[0] + xs[1]`.
The captured text is the whole expression source and the value is its result - ideal for "what does this actually evaluate to?" checks, with no need to invent a label for a compound expression.

**Format specs compose.**
The fourth block shows the `=` combining with the format mini-language of Chapter 246: `f"{pi=:.3f}"` gives `pi=3.142` (three decimals, still labelled), and `f"{ratio=:.0%}"` gives `ratio=25%`.
The format spec after the `=` formats the value while the generated label is preserved, so the debug helper integrates with all the formatting you already know.

**Whitespace is preserved.**
The fifth block shows a small nicety: `f"{x = }"` produces `x = 5`, echoing the spaces you wrote around the `=`, so you control whether the output reads `x=5` or `x = 5`.
The label mirrors your source exactly.

## The two-track note

The f-string mechanism - how the expression is parsed, evaluated, and formatted - is Deep Volume D's and Chapter 246's to develop; the `=` specifier is a small extension that additionally captures and emits the expression's *source text*.
What the timeline records is the release act: in 3.8, the `=` debug specifier made the label a byproduct of the expression rather than a hand-typed duplicate.
The modern consequence, verified above, is that `f"{expr=}"` is the standard quick-debug print in Python - correct by construction, composable with format specs, and immune to the lying-label bug that plagued the two-argument `print`.

## Where this lands

The `=` specifier is one of the smallest features in the language and one of the most-used in daily debugging, precisely because it removes an error from the thing everyone does constantly.
Reach for `f"{expr=}"` any time you would have written `print("name =", name)` - it is shorter, it works on whole expressions, it composes with format specs, and its label can never drift from its value.
Deep Volume D and Chapter 246 explain f-string formatting; this chapter is the record of the release that made the ubiquitous debug print correct by construction.
