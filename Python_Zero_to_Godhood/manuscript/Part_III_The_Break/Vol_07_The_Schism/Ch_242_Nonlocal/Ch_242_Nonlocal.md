# Chapter 242: Nonlocal

## The constraint

Python closures could always *read* a variable from an enclosing function.
Write an inner function that refers to a name defined in the outer one, and it works - the inner function closes over the outer variable and sees its value.
But for Python's first eighteen years, closures could not *rebind* that variable.

The reason is Python's scoping rule: any name a function *assigns to* is a local of that function, for the entire function body.
So the moment you wrote `count = count + 1` inside an inner function, Python decided `count` was a new local of the inner function - and the reference to `count` on the right-hand side became a read of that not-yet-assigned local, raising `UnboundLocalError`.
The outer `count` was untouched.
There was no way to say "I mean the `count` from the enclosing function, and I want to reassign *it*."

This forced ugly workarounds.
The common one wrapped the state in a one-element list - `box = [0]` - so the inner function could `box[0] += 1`: it *mutated the container* rather than *rebinding the name*, sidestepping the local-assignment rule.
The other was to promote the state to a module `global`, polluting the namespace and breaking encapsulation.
Both existed only because the language lacked a way to reach one scope outward for assignment.

The constraint Python 3.0 (2008) answered: **give inner functions a way to rebind a variable in the nearest enclosing function scope, so a closure can carry mutable state directly.**

This is a two-track chapter.
Python's scope resolution - the LEGB rule (Local, Enclosing, Global, Built-in), how names are looked up and bound, why assignment defaults to local - belongs to Deep Volume B.
What this chapter owns is the release: the day the `nonlocal` keyword completed the closure by letting it write outward.

## What shipped

`nonlocal name` declares that `name` refers to a variable in the nearest enclosing *function* scope (not the global scope), so assignments to it rebind that outer variable rather than creating a new local.
Listing 242.1 shows the completed closure, the exact failure `nonlocal` fixes, and the hack it retired, on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- nonlocal lets an inner function REBIND an enclosing variable ---
  counter() : 1
  counter() : 2
  counter() : 3
  each call rebinds the enclosing `count`. without nonlocal, `count
  += 1` would make count a new LOCAL and fail with UnboundLocalError
  (reading a local before it is assigned)
--- the exact failure nonlocal fixes ---
  inner reassigns without nonlocal : UnboundLocalError: cannot access local variable 'total' where it is not associated with a value
  `total = total + n` makes total a local of add(); reading it on the
  right-hand side before assignment raises. this is THE closure
  gotcha nonlocal was invented to remove
--- read vs rebind: reading never needed nonlocal ---
  reader() before : HELLO
  reader() after writer() : CHANGED
  reading an enclosing variable always worked (Python 2 too). only
  REBINDING needed a way to say 'this is the outer one, not a new
  local' - that is precisely what nonlocal declares
--- the pre-3.0 workaround nonlocal retired ---
  list-in-a-box counter : 1, 2, 3
  before nonlocal you wrapped state in a one-element list and mutated
  box[0] - never rebinding the name, only its contents. nonlocal
  makes the plain variable work, so the hack is gone
--- the constraint answered ---
  Python 2 closures could read but not rebind an enclosing variable,
  forcing list-in-a-box or global workarounds for stateful inner
  functions. nonlocal (3.0) declares 'this name is the enclosing
  one', so inner functions can update it directly - completing the
  closure as a first-class way to carry state
```

## Why each part answers the constraint

**The completed closure.**
The first block shows `make_counter` returning an `increment` function that carries its own `count` across calls, yielding `1`, `2`, `3`.
The `nonlocal count` declaration is what makes `count += 1` rebind the enclosing variable rather than create a local.
This is a stateful function without a class and without a container hack - the closure doing exactly what a closure should.

**The exact failure it fixes.**
The second block reproduces the bug.
`broken` has an inner `add` that writes `total = total + n` *without* `nonlocal`.
Because it assigns to `total`, `total` is a local of `add` for the whole body, so reading it on the right-hand side before assignment raises `UnboundLocalError`.
This is the specific, confusing failure that puzzled Python programmers for years - the code looks like it should update the outer `total`, and instead it fails to even run.
`nonlocal` is the one-word declaration that resolves it.

**Read never needed it; only rebind did.**
The third block draws the precise boundary.
`reader` reads the enclosing `message` and works with no declaration - reading an enclosing variable always worked, in Python 2 as well.
`writer` *rebinds* `message`, and that is what needs `nonlocal`.
The keyword is not "make this a closure variable" - it already was one for reading.
It is specifically "this assignment targets the enclosing variable, not a new local."
That narrow meaning is why `nonlocal` is needed only where a name is reassigned.

**The hack it retired.**
The fourth block shows the pre-3.0 idiom: `box = [0]`, then `box[0] += 1` inside the inner function.
This worked because it *mutated the list's contents* rather than *rebinding the name* `box` - dodging the local-assignment rule entirely.
It produced correct counters and read terribly.
`nonlocal` lets the plain variable work, so the list-in-a-box pattern, and the encapsulation-breaking `global` alternative, are both gone.

## The two-track note

The scope-resolution rules - LEGB, why binding defaults to local, how `nonlocal` differs from `global` (enclosing function scope versus module scope), how the compiler classifies each name in a function body - are Deep Volume B's to formalize.
What the timeline records is the completion: in 3.0, `nonlocal` filled the one gap that had kept closures from carrying mutable state cleanly.
The modern consequence, verified above, is that stateful closures are written directly and idiomatically, the `UnboundLocalError` gotcha has a one-word fix, and the container hacks that predated the keyword are historical curiosities.

## Where this lands

`nonlocal` is a small keyword that closed a real hole in Python's closure model.
Reach for it whenever an inner function needs to *reassign* a variable owned by an enclosing function - a running total, a cached value, a state flag - and remember that reading such a variable never needs it, only rebinding does.
Prefer a class when the state grows beyond a value or two, but for a single stateful inner function, `nonlocal` is exactly the right tool.
Deep Volume B explains the scope rules underneath; this chapter is the record of the release that let a closure finally write to the scope it was born in.
