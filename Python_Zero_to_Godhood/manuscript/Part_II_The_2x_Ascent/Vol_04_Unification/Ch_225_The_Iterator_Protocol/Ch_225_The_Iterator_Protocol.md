# Chapter 15: The Iterator Protocol

Volume 4 covers Python 2.2-2.3, the "Unification" era, when the language's deepest structures were made consistent. This chapter is one of that era's quietest and most far-reaching additions: **Python 2.2 (2001) introduced the iterator protocol**, and in doing so redefined what `for` *means*.

Before 2.2, `for x in obj` worked by calling `obj[0]`, `obj[1]`, `obj[2]`, and so on until an `IndexError`, it required **integer indexing**. This tied looping to sequences with numeric indices and excluded everything else: you could not naturally `for` over a dict (indexed by keys, not integers), a set (no order to index), a file (a stream, not an indexed sequence), or, crucially, a lazy or infinite sequence (no materialised elements to index). The iterator protocol **decoupled iteration from indexing**: `for` now calls `iter(obj)` to get an iterator, then `next()` repeatedly until `StopIteration`. Anything that defines `__iter__`/`__next__` can be looped over, and that single abstraction became the foundation of `for`, comprehensions, unpacking, `*args`, and the entire "iterable" vocabulary. Deep F owns the mechanism (the protocol's internals, generators, coroutines); this chapter owns the release that made `for` universal, and the listing demonstrates it on the verification interpreters.

## Section index

- **15.1** The constraint: iteration was chained to integer indexing
- **15.2** The protocol: two methods, one abstraction
- **15.3** One protocol, every iterable
- **15.4** The protocol powers far more than for-loops
- **15.5** What it enabled: generators and laziness
- **15.6** Edges: the protocol's subtleties
- **15.7** Connections
- **15.8** Exercises
- **15.9** Summary and cross-references

Listings live under `code/ch225/` and are re-executed by `make verify` on the verification interpreters.

---

## 15.1 The constraint: iteration was chained to integer indexing

The pre-2.2 `for` loop had a specific, limiting implementation: to iterate `obj`, Python called `obj.__getitem__(0)`, `obj.__getitem__(1)`, and so on, incrementing the integer index until `__getitem__` raised `IndexError`. This worked for lists, tuples, and strings, sequences with integer indices, and for those types it was fine. But it *chained iteration to integer indexing*, and that chain excluded a great deal.

A dictionary is indexed by *keys*, not integers, so the old `for` could not naturally loop it (what would `dict[0]` mean?). A set has no order and no indices at all. A file is a *stream* of lines, not an indexed sequence. And a lazy or infinite sequence, the numbers `1, 2, 3, ...` forever, or a database cursor fetching rows on demand, has no materialised `obj[i]` to return, because the elements do not exist until you ask for the next one. The constraint 2.2 answered is that **iteration and indexing are different concepts**: "give me the next element" (iteration) is more general than "give me element `i`" (indexing), because many things can produce a next element without supporting random access. Chaining `for` to indexing forced everything iterable to also be indexable, which most iterable things are not.

---

## 15.2 The protocol: two methods, one abstraction

```python
# code/ch225/l01_the_iterator_protocol.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- for works on anything with the protocol, no indexing needed ---
  a hand-built iterator : [3, 2, 1]
  for called iter() then next() until StopIteration - it never
  indexed anything. this is the decoupling 2.2 introduced: iteration
  no longer requires obj[0], obj[1], ... (which needed integer keys)
--- the protocol is two methods, and that is the whole abstraction ---
  iter(list) gives an iterator : list_iterator
  next(it) : 10, next(it) : 20, next(it) : 30
  next(it) past the end raises : StopIteration
  __iter__ gives an iterator; __next__ advances or raises
  StopIteration. every loop in Python is these two calls in a
  hidden while-loop (Deep F owns the machinery)
```

**The protocol is two methods, and every loop in Python is those two methods in a hidden while-loop.**
`__iter__` returns an iterator (an object with `__next__`); `__next__` returns the next element or raises `StopIteration` to signal the end. That is the *entire* abstraction. `for x in obj` desugars to: `it = iter(obj); while True: try: x = next(it) except StopIteration: break; <body>`. The hand-built `CountdownIterator` shows it working with no indexing at all, `for` called `iter()` then `next()` until `StopIteration`, and never touched `[0]`. Two methods replaced the integer-indexing requirement, and because they are so minimal, *anything* can implement them, which is the decoupling's whole payoff.

**`StopIteration` as the terminator is a deliberate protocol choice.**
The end of iteration is signalled by an *exception* (`StopIteration`), not a sentinel return value, which fits Python's exception model (Chapter 7) and means `__next__` can return *any* value (including `None`) as a real element without ambiguity, the end is unambiguously the exception, not a special value. This is why `StopIteration` is a normal exception that `for` catches internally, and why raising it manually (or letting it leak from a generator, PEP 479, Deep F) has subtle consequences. The protocol's minimalism, two methods, exception-terminated, is what makes it universally implementable and is the design Deep F elaborates.

---

## 15.3 One protocol, every iterable

```text
--- one protocol, every 'iterable' - built-ins included ---
  a dict iterates its keys   : ['a', 'b']
  a set iterates its members : [1, 2, 3]
  a str iterates its chars   : ['h', 'i']
  range is lazily iterable   : [0, 1, 2]
  none of these support integer indexing the old for-loop needed
  (a set has no order to index, a dict indexes by KEY) - yet all
  loop, because they define the protocol. that is its power
```

**The built-in types the old `for` could not handle all iterate via the protocol, and that is the decoupling's concrete payoff.**
A dict iterates its keys; a set iterates its members; a range produces its numbers lazily. *None* of these supports the integer indexing the old `for` required, a set has no order to index, a dict indexes by key not position, a range does not materialise its elements, yet all of them loop, because all of them define the iterator protocol. This is the abstraction working: the *same* two-method protocol serves indexed sequences (lists), unordered collections (sets), key-value mappings (dicts), and lazy generators (ranges), because each implements "give me the next element" in its own way. The old indexing-based `for` could serve only the first; the protocol serves all, and that generality is why Python's iteration vocabulary is so uniform, everything iterable speaks one protocol.

**Uniformity is the point: one protocol means one vocabulary.**
Because dicts, sets, files, lists, and generators all implement the *same* protocol, the *same* tools work on all of them: `for`, `list()`, `sum()`, `sorted()`, comprehensions, unpacking. You learn the iteration vocabulary once and it applies everywhere, and you can write functions that accept "any iterable" and they work on all of these types without knowing which. This is the "one protocol, many implementations" pattern (the same shape as WSGI in Chapter 126, the object model in Chapter 4), and it is why "iterable" is a first-class concept in Python: it names anything that speaks the protocol, and the whole standard library is written against that concept, not against specific types.

---

## 15.4 The protocol powers far more than for-loops

```text
--- the protocol powers far more than for-loops ---
  unpacking a, b, c = iterator : 3, 2, 1
  comprehension over iterator  : [30, 20, 10]
  sum/max/any over iterable    : sum=10, max=4
```

**The iterator protocol underlies unpacking, comprehensions, `*args`, and every iteration builtin, not just `for`.**
`a, b, c = CountdownIterator(3)` unpacks an iterator (unpacking consumes the protocol); `[x*10 for x in ...]` is a comprehension (built on the protocol); `sum(...)`, `max(...)`, `any(...)`, `sorted(...)` all consume iterables. Define `__iter__`/`__next__` *once*, and your object works with the *entire* iteration vocabulary, every tool that "loops over" something. This is the leverage of a single, minimal protocol: it is not just `for` that gained universality in 2.2, it is unpacking, comprehensions, argument splatting (`*iterable`), and the dozens of builtins and standard-library functions that consume iterables. One protocol, and your custom object slots into all of it.

**This is why implementing the protocol is high-leverage.**
A class that implements the iterator protocol does not just "support `for`", it becomes a full participant in Python's iteration ecosystem: it can be summed, sorted, unpacked, comprehended, splatted, and passed to any function expecting an iterable. The two methods buy participation in a huge vocabulary, which is why custom iterables (a paginated API client, a streaming parser, a lazy sequence) implement the protocol rather than materialising lists, they get the whole vocabulary and the laziness (§15.5) for the cost of two methods. The protocol's minimalism and its reach are the same property: minimal to implement, maximal in what implementing it grants.

---

## 15.5 What it enabled: generators and laziness

**The iterator protocol is the foundation generators (also 2.2) and the entire lazy-evaluation story are built on.**
Python 2.2 added generators (`yield`) *alongside* the iterator protocol, and this is not a coincidence: a generator is the *easiest way to create an iterator*. Writing `__iter__`/`__next__` by hand (like `CountdownIterator`) is verbose; a generator function with `yield` produces an iterator automatically, the function's local state *is* the iterator's state, and each `yield` is a `__next__` return. So the protocol (the abstraction) and generators (the ergonomic way to implement it) arrived together, and between them they made *laziness* practical: a sequence that produces elements on demand, never materialising the whole thing, which is Chapter 91's streaming (Deep K) and the constant-memory processing of arbitrarily large or infinite data.

**Laziness is the protocol's deepest consequence.**
Because iteration is "give me the next element" rather than "give me element `i`", an iterator need not have all its elements at once, it can produce them one at a time, which means it can be *infinite* (`itertools.count()`), *streaming* (a file read line by line, a socket, Chapter 106), or *computed on demand* (a generator). The old indexing `for` could not express any of this (you cannot index an infinite sequence). The iterator protocol can, and Chapter 91's entire streaming discipline, constant memory over arbitrarily large data, generators as pipelines, early exit propagating backward, rests on the 2.2 decision to make iteration mean "next", not "index". The protocol is the abstraction; laziness is what the abstraction makes possible; and Deep F and Deep K own the two halves.

---

## 15.6 Edges: the protocol's subtleties

**An iterator is exhausted after one pass.**
`__next__` advances state, so once an iterator raises `StopIteration`, it is spent, looping it again yields nothing (Chapter 91's silent-exhaustion edge). This is why `__iter__` on a *container* (list) returns a *fresh* iterator each call (re-iterable) while `__iter__` on an *iterator* returns `self` (single-pass). Confusing the two, treating a one-shot iterator as re-iterable, is a common bug the protocol's design (iterable vs iterator) distinguishes but does not prevent.

**`iter` and `next` are the public interface; `__iter__` and `__next__` are the protocol.**
Call `iter(obj)` and `next(it)`, not `obj.__iter__()` and `it.__next__()` directly, the builtins add behaviour (e.g. `next(it, default)` returns a default instead of raising). The dunder methods *implement* the protocol; the builtins *consume* it, and using the builtins is the idiom (the same iter/next-are-public rule as Chapter 91).

**`StopIteration` leaking from a generator is a bug PEP 479 fixed.**
A `StopIteration` raised *inside* a generator (rather than the generator simply returning) used to silently terminate the generator, masking bugs; PEP 479 (Python 3.5+, mandatory 3.7) made a `StopIteration` escaping a generator body a `RuntimeError` instead. This is the protocol's terminator exception interacting badly with generators, and Deep F owns the full story, the edge here is that `StopIteration` is load-bearing and must not leak.

**And iterating while mutating is undefined.**
Modifying a container during iteration over it (adding to a dict in a `for` over its keys) raises `RuntimeError` for dicts/sets ("changed size during iteration") and produces undefined behaviour for lists (Chapter 119's identical CSV lesson). The iterator holds a position into the container's internal state, and mutation invalidates that position, iterate a copy, or collect changes and apply after.

---

## 15.7 Connections

**Backward.**
The object model where the protocol is dunder methods on any object is Chapter 4; the exception model `StopIteration` uses is Chapter 7; the "one protocol, many implementations" pattern is the extensibility decision (Chapter 1) applied to iteration.

**Forward.**
The full protocol mechanism, generators, coroutines, `yield from`, is Deep F (Chapters covering iteration); laziness and streaming built on it are Chapter 91 (Deep K); the async iteration protocol (`__aiter__`/`__anext__`) that extends it is Deep J (Chapter 102's era); `itertools` (the standard library of iterator tools) is Chapter 33 (Deep Q); PEP 479's `StopIteration` fix is Deep F.

**Across books.**
The iterator protocol is Python's; **Book I**'s C++ iterators are a different design (pointer-like objects with `++` and `*`, a pair marking begin/end) serving the same purpose, decoupling algorithms from containers, so `std::sort` works on any container's iterators the way Python's `sorted` works on any iterable. The shared trading system streams market data as an iterable in Python (a generator over the tick feed, Chapter 91) and as an iterator range in C++, the same "produce elements on demand" abstraction in both, which is the market-data pipeline's shape.

---

## 15.8 Exercises

**1. Build an iterator by hand.** Implement an iterator over the Fibonacci sequence with `__iter__`/`__next__`; loop it with `for`, comprehend it, and unpack the first three. Confirm no indexing is involved.

**2. Iterable vs iterator.** Write a container whose `__iter__` returns a fresh iterator (re-iterable) and an iterator whose `__iter__` returns `self` (one-shot); demonstrate the re-iteration difference and explain the exhaustion edge.

**3. The universality test.** For your hand-built iterator, use it with `for`, `list`, `sum`, `sorted`, unpacking, `*args`, and a comprehension; confirm all work from the two methods. This is §15.4's leverage, felt.

**4. Make it lazy and infinite.** Convert your iterator to a generator (`yield`); make it infinite; take the first ten with `itertools.islice`. Explain why the old indexing `for` could not express this (Chapter 91).

**5. The design question.** The iterator protocol decoupled iteration from indexing at the cost of iterators being single-pass and stateful (the exhaustion edge). Argue whether this trade, generality and laziness versus re-iterability, was right, and compare with a design where iteration always returns a re-iterable snapshot (safer, but no laziness, no infinity). Use Chapter 91's streaming as the case for the stateful design.

---

## 15.9 Summary and cross-references

- **Python 2.2 (2001) introduced the iterator protocol**, decoupling iteration from integer indexing: `for` now calls `iter(obj)` then `next()` until `StopIteration`, where before it called `obj[0]`, `obj[1]`, ... requiring integer keys.
- **The protocol is two methods** (`__iter__` returns an iterator, `__next__` advances or raises `StopIteration`), and every loop in Python is those two methods in a hidden while-loop, minimal to implement, universal in reach.
- **One protocol serves every iterable**: dicts (by key), sets (unordered), files (streams), ranges (lazy), none of which the old indexing `for` could handle, all loop because all speak the protocol, one vocabulary for all.
- **The protocol powers far more than `for`**: unpacking, comprehensions, `*args`, and `sum`/`max`/`sorted`/`any` all consume it, so implementing two methods buys participation in the entire iteration vocabulary.
- **It is the foundation of generators (also 2.2) and laziness**: iteration meaning "next" not "index" allows infinite, streaming, and computed-on-demand sequences, the entire Chapter 91 streaming discipline, and the edges (single-pass exhaustion, mutate-during-iteration, `StopIteration` leaks) are the protocol's subtleties Deep F owns.

**Cross-references.** The object model → Chapter 4. Exceptions and `StopIteration` → Chapter 7. Generators, coroutines, the full protocol → Deep F. Laziness and streaming → Chapter 91. Async iteration → Chapter 102. `itertools` → Chapter 33. Mutate-during-iteration → Chapter 119. C++ iterators → Book I.
