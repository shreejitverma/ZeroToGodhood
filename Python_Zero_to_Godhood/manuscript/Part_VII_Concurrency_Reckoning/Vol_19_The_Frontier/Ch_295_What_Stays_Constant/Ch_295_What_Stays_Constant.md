# Chapter 295: What Stays Constant

## The frontier, and what lies beneath it

This chapter closes the numbered timeline - nineteen volumes that ran from the inheritance ABC left on Python's syntax, through the 2.x ascent, the Python 3 break, the ergonomics and typing era, the performance work, and into the concurrency reckoning and its frontier.
It is a long story of change.
And it ends by pointing at the thing that barely changed at all: the **data model**.

Two theses have been true since Python 1.0, and they are exactly as true on a 3.14 free-threaded build.
*Everything is an object* (Chapter 216): every value, every function, every class is a first-class object with a type.
And *behavior is defined by protocols, not by type* (the duck-typing thesis): the operators and builtins - `len()`, `for`, `in`, `[]`, `==`, `if` - dispatch to *dunder methods* that any type can implement, not to a fixed, privileged set of built-in types.

Because of this, a class you write today plugs into the language's core operators *exactly* like a builtin.
That is not a new feature; it is the oldest one, and it is why decades-old Python still reads clearly, and why learning the model once pays off across every release this book documented.

## What this looks like

Listing 295.1 defines a custom `Deck` type that implements the core protocols and shows it participating in the language's operators like a builtin, on today's interpreter.

Verified output (CPython 3.13.5):

```text
--- everything is an object, with a type (Chapter 216) ---
  the deck is an object : True
  functions are objects too : True
  even a class is an object : True
  the oldest thesis in the language - EVERYTHING is a first-class
  object with a type - is unchanged after 19 volumes of releases
--- len() dispatches to __len__: protocol, not type ---
  len(deck) : 4
  len() does not check 'is this a list?' - it calls __len__. any object
  that defines it has a length. this is duck typing at the operator
  level, and it has worked this way since the beginning
--- for/in/[] all come from __iter__ and __getitem__ ---
  list(deck)       : ['A', 'K', 'Q', 'J']   (for uses __iter__)
  deck[0], deck[-1]: A, J   (__getitem__)
  deck[1:3]        : ['K', 'Q']   (slicing, same protocol)
  'Q' in deck      : True   (membership via iteration)
  iteration, indexing, slicing, and membership - the whole sequence
  experience - fall out of two dunder methods. the custom Deck behaves
  like a builtin because the operators target the PROTOCOL
--- == and truthiness come from __eq__ and __bool__ (Chapter 229) ---
  deck == Deck(['A','K','Q','J']) : True
  bool(deck)        : True   (non-empty -> truthy)
  bool(Deck([]))    : False   (empty -> falsy)
  `if deck:` takes the branch : yes
  equality and truthiness are protocols too. `if deck:` asks the
  object, exactly as `if some_list:` does - one model, every type
--- the payoff: learn the model once, use it forever ---
  the protocols shown here predate almost everything in this book and
  will outlast the frontier chapters. f-strings, pattern matching, and
  free-threading are all built ON this model; none of them changed it.
  that is why a Python program from 20 years ago still reads clearly
--- the constraint answered ---
  the whole timeline - 19 volumes of change - rests on a data model
  that barely moved: everything is an object, and behaviour comes from
  protocols any type can implement. a custom class plugs into len, for,
  in, [], ==, and truthiness like a builtin because operators dispatch
  to dunder methods, not to fixed types. the frontier moves; the core holds
```

## Why each part matters

**Everything is an object.**
The first block confirms the founding thesis: the `Deck` instance, the `len` builtin, and even the `Deck` class itself are all objects.
Nineteen volumes of releases did not disturb this - functions, classes, modules, and types remain first-class objects you can pass around, inspect, and store.

**`len` dispatches to a protocol.**
The second block shows `len(deck)` returning 4, because `len()` does not check "is this a list?" - it calls `__len__`.
Any object that defines it has a length.
This is duck typing at the operator level: the operator targets the *capability*, not the *type*, and it has worked this way since the beginning.

**Sequences fall out of two methods.**
The third block shows the whole sequence experience - iteration (`list(deck)`), indexing (`deck[0]`, `deck[-1]`), slicing (`deck[1:3]`), and membership (`'Q' in deck`) - emerging from `__iter__` and `__getitem__`.
The custom `Deck` behaves like a builtin sequence because the operators dispatch to the protocol.
You do not inherit from a magic base class; you implement the methods, and the language treats your object as the sequence it acts like.

**Equality and truthiness too.**
The fourth block shows `==` (via `__eq__`) and truthiness (via `__bool__`, Chapter 229) are protocols as well: `deck == Deck([...])` is `True`, a non-empty deck is truthy, an empty one is falsy, and `if deck:` asks the object exactly as `if some_list:` does.
One model, every type - the same protocol machinery underlies both builtins and your own classes.

**Learn it once.**
The fifth block states the payoff that closes the book's timeline.
The protocols shown here predate almost everything in these nineteen volumes and will outlast the frontier chapters.
F-strings, pattern matching, free-threading - every feature this book documented was built *on* this model, and none of them changed it.
That is why a Python program from twenty years ago still reads clearly today, and why the effort of learning the data model is the highest-leverage investment a Python programmer can make: it is the one thing that does not expire.

## Where this lands, and the close of the timeline

The frontier will keep moving.
There will be a 3.15, a 3.16, features not yet designed and problems not yet named.
The concurrency reckoning will play out, the JIT will mature, typing will keep evolving.
But underneath all of it sits a small, stable core - everything is an object, and behavior comes from protocols any type can implement - that has held since the language began and shows every sign of holding indefinitely.

This is the right note to end the numbered timeline on, because it explains the timeline's own shape.
Python could accumulate two decades of features without fracturing, could break to Python 3 and recover, could add pattern matching and remove the GIL, all while old code kept reading clearly - *because the changes were additions to a stable model, not revisions of it*.
The releases came and went; the data model stayed.
The frontier moves; the core holds.

That closes Volume 19, The Frontier, and with it the timeline volumes of *Python: Zero to Godhood*.
What remains - the Deep Volumes and the boundary volumes of Part VIII - are not chronology but *mastery*: the mechanisms the timeline used, examined in depth, and the edges where Python meets C, the operating system, the package index, and the world.
The story of *when* is told; the study of *how* and *how well* continues.
