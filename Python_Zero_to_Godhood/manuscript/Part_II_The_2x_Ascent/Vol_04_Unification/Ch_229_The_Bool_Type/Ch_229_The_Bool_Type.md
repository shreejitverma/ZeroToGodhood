# Chapter 229: The Bool Type

## The constraint

For its first eleven years, Python had no Boolean type.
Truth was `1` and falsehood was `0`, comparisons like `3 < 5` returned the integer `1`, and there were no names `True` and `False` in the language at all - programmers who wanted them wrote `True, False = 1, 0` at the top of a module.
This was not broken, exactly, but it was unnamed: `if flag == 1` and `if flag` meant subtly different things, functions returned `0`/`1` where they meant no/yes, and there was no type to hang the concept of truth on.

Python 2.3 (2003, PEP 285) set out to give truth a name.
But it did so under a hard constraint that shaped every detail of the result: **the language could not break the decade of existing code that treated truth as the integers 1 and 0.**
Millions of lines summed comparison results, indexed lists with them, and did arithmetic on them.
A brand-new `bool` type that was *not* an integer would have broken all of it.
So PEP 285 made a deliberate, heavily-debated decision: `bool` would be a real type with two singleton values, `True` and `False` - but it would be a *subclass of `int`*, so that `True` genuinely *is* `1` and `False` genuinely *is* `0`.
That one choice is the whole chapter.

This is a two-track chapter.
The type/subtype machinery - what it means for `bool` to subclass `int`, how `isinstance` and method resolution follow the subclass relationship, how the `__bool__` protocol lets any object answer `bool()` - all belongs to Deep Volume A (the object and type model).
What this chapter owns is the release: the day truth got a name, and the compatibility constraint that forced that name to also be a number.

## What shipped

Listing 229.1 walks through the consequences of the subclassing on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- True and False are singletons of a real type ---
  type(True)  : bool
  True, False : True, False
  before 2.3 there was no True/False - comparisons returned 1 and 0
  and you wrote your own True, False = 1, 0. PEP 285 made them a type
--- the deliberate choice: bool is a SUBCLASS of int ---
  issubclass(bool, int) : True
  isinstance(True, int) : True
  True == 1  : True   (True IS 1)
  False == 0 : True   (False IS 0)
  PEP 285 made bool subclass int so that a DECADE of code treating
  truth as 1/0 kept working unchanged. backward compatibility was
  the reason, and it is why the two values equal 1 and 0 exactly
--- the consequence: True and False do arithmetic ---
  True + True       : 2   (1 + 1)
  sum([True, False, True, True]) : 3
  counting Trues by sum() : 3 of 5
  because True IS 1, sum() over booleans COUNTS them - a genuinely
  useful idiom (how many predicates held?), and a direct consequence
  of the subclassing, not a coincidence
--- the trap the subclassing creates: never compare == True ---
  x = 3
  bool(x)     : True   (3 is truthy)
  x == True   : False   (3 == 1 is False!)
  x is True   : False   (3 is not the True singleton)
  `if x == True` asks '== 1', so a truthy 3 FAILS it. write `if x`
  (truthiness) - never `== True`. the subclassing is exactly why the
  comparison misleads: True is 1, and 3 != 1
--- truthiness: any object answers bool(), not just True/False ---
  bool(0), bool(''), bool([]), bool(None) : False, False, False, False
  bool(42), bool('x'), bool([0]) : True, True, True
  `if x` calls x.__bool__() (Deep A): empty/zero/None are falsy,
  everything else truthy. bool the TYPE named the two answers; the
  PROTOCOL lets every object give one. that is why `if seq:` is the
  Pythonic emptiness test, not `if len(seq) == 0`
--- the constraint answered ---
  before 2.3, truth had no name - just 1 and 0. PEP 285 gave it a
  type with two singletons, but subclassed int so every program
  that did arithmetic on comparisons kept working. that one design
  choice explains all of bool's behaviour: names for truth, full
  compatibility, sum-counts-Trues, and the `== True` trap
```

## Why each part answers the constraint

**Names for truth.**
The first block is the surface win: `type(True)` is `bool`, and `True`/`False` are keywords the language provides.
A function that returns `True` now says "yes" in a way `return 1` never did.
This is the readable half of PEP 285, and on its own it would have been uncontroversial.

**The subclassing is the compatibility mechanism.**
The second block is where the constraint shows through.
`issubclass(bool, int)` is `True`; `isinstance(True, int)` is `True`; `True == 1` and `False == 0` are both `True` - not by coincidence but by design.
Because `bool` *is* an `int`, every pre-2.3 program that summed comparison results, used a Boolean as a list index, or did any arithmetic on truth kept running byte-for-byte unchanged when 2.3 introduced the type.
The new name was layered on top of the old number without disturbing it.
This is the central engineering fact of the release: PEP 285 chose backward compatibility over conceptual purity, and the subclassing is the shape of that choice.

**`sum` counts Trues - the useful consequence.**
Because `True` is `1`, `sum([True, False, True, True])` is `3`, and `sum(predicate(x) for x in items)` counts how many items satisfy the predicate.
This is a genuinely good idiom, used constantly in real Python, and it exists *only* because of the subclassing.
It is the clearest demonstration that the compatibility choice was not merely a grudging concession - it made truth composable with arithmetic in a way that is often exactly what you want.

**The `== True` trap - the harmful consequence.**
The same subclassing that makes `sum` count is the reason `if x == True` is a bug.
`x == True` means `x == 1`.
So a perfectly truthy `x = 3` *fails* `x == True`, because `3 != 1` - even though `bool(3)` is `True` and `if x` would take the branch.
The listing shows all three: `bool(3)` is `True`, `3 == True` is `False`, `3 is True` is `False`.
The rule that falls out is absolute: test truthiness with `if x`, never with `if x == True`.
The trap and the `sum` idiom are the same fact seen from two sides - that is why this chapter treats them together rather than as unrelated tips.

**Truthiness is a protocol, not just two values.**
The final block draws the line between the *type* and the *protocol*.
`bool` the type named the two answers.
But `if x` does not require `x` to be a `bool` - it calls `x.__bool__()` (Deep Volume A), and every object gives an answer: `0`, `''`, `[]`, `None` are falsy, everything else is truthy.
That is why `if seq:` is the Pythonic emptiness test rather than `if len(seq) == 0`: the emptiness question is answered by the object's own truthiness protocol.
The 2.3 release named the two poles; the protocol - older than the type - is what lets every value fall on one side.

## The two-track note

The subtype relationship this whole chapter turns on is Deep Volume A's to formalize: what a subclass *is*, how the MRO and `isinstance` walk it, why `bool` overriding `__repr__` (so `True` prints as `True`, not `1`) is a clean use of subclassing.
The `__bool__` protocol that makes truthiness universal is likewise Deep A's mechanism.
What the timeline owns is narrower and factual: in 2003, PEP 285 gave truth a named type, and a compatibility constraint - do not break a decade of arithmetic-on-comparisons - forced that type to subclass `int`.
Every behavior verified above, the good idiom and the sharp trap alike, is the modern, byte-identical consequence of that single constrained decision.

## Where this lands

`bool` is the smallest type in the language and one of the most instructive, because its entire design is a visible negotiation between a new abstraction and old code.
Reach for `if x` and you use the protocol; write `sum(flags)` and you use the subclassing; avoid `== True` and you respect its one sharp edge.
Deep Volume A explains the type machinery underneath; this chapter is the record of the release that added the name and, in the same stroke, chose compatibility over purity - and got a surprisingly useful type out of the bargain.
