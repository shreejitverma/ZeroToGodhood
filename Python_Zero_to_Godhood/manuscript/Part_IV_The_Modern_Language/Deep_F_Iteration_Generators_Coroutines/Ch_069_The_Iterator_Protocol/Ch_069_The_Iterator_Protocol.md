# Chapter 69: The Iterator Protocol

A function returns an iterator over parsed records, a caller loops it to count them, then loops it again to
process them, and the second loop does nothing, silently. No error, no exception, just an empty pass over what
looked like a full collection. The cause is the distinction at the heart of Python's iteration: an **iterable**
can be looped many times (each `for` gets a *fresh* iterator), but an **iterator** is **single-use**, once
consumed, it is exhausted and yields nothing more. The function returned an *iterator*, not a re-iterable, and
the second loop drained an empty one. Understanding iterable-versus-iterator is the difference between code that
works and code that mysteriously processes nothing the second time. And when you *implement* an iterator, the
idiomatic tool, a **generator**, is not just shorter than a hand-written `__iter__`/`__next__` class but
measurably faster: **2x** here, because the generator resumes a frame in C while the class pays a Python method
call per item.

This chapter opens **Deep F** (iteration, generators, coroutines) with the iterator protocol: the iterable/
iterator roles, the `iter`/`next`/`StopIteration` mechanics, and why generators are the right way to produce a
sequence. It is the *mechanism* beneath Chapter 9's laziness and Chapter 33's `itertools`.

## Section index

- **69.1** Iterable, iterator, and single use
- **69.2** Generators implement the protocol in C
- **69.3** Measurement: generator vs iterator class
- **69.4** Edges and failure modes
- **69.5** Connections
- **69.6** Exercises
- **69.7** Summary and cross-references

Listings live under `code/ch069/` and are re-executed by `make verify` on both interpreters.

---

## 69.1 Iterable, iterator, and single use

```python
# code/ch069/l01_iterator_protocol.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- iterable vs iterator ---
  iter(list) is a NEW iterator (not the list) : True
  an iterator's __iter__ returns itself       : True
--- an iterator is single-use; an iterable is not ---
  list looped twice : [10, 20, 30] [10, 20, 30]
  iterator drained  : [10, 20, 30] []  (second pass is empty)
--- next() drives the protocol; StopIteration ends it ---
  next(g): 0  next(g): 1
  next past the end raises StopIteration : True
--- a generator IS an iterator with the same output as the class ---
  class output : [0, 1, 2, 3, 4]
  gen output   : [0, 1, 2, 3, 4]
  identical    : True
```

There are two roles. An **iterable** has `__iter__`, which returns a *fresh* iterator each call, so `iter(lst)`
is a new object, not the list, and a list can be looped any number of times. An **iterator** has `__next__`
(returning the next value, raising `StopIteration` when done) and *is its own iterable*, its `__iter__` returns
`self`. That "returns self" is exactly why an iterator is **single-use**: looping it a second time calls
`__iter__` (getting the same, now-exhausted, iterator) and immediately hits `StopIteration`. The listing makes
this concrete: the *list* looped twice gives `[10, 20, 30]` both times; the *iterator* gives `[10, 20, 30]` then
`[]`.

The `for` statement is sugar over this protocol: `for x in obj` calls `iter(obj)` once, then `next()` repeatedly
until `StopIteration`. So a `for` over a list re-iterates freely (fresh iterator each time), and a `for` over an
iterator consumes it. The rule that avoids the opening bug: **return an iterable (or a list) if the caller may
loop more than once; return an iterator only for a single pass, and document it.**

---

## 69.2 Generators implement the protocol in C

You can implement an iterator two ways. The **hand-written class** defines `__iter__` (returns `self`) and
`__next__` (advances state, raises `StopIteration` at the end), the `CountIter` in the listing. The
**generator function** uses `yield`, and Python's generator machinery implements `__iter__`/`__next__` *for you*,
each `next()` runs the function body until the next `yield` (returning that value) and suspends; falling off the
end raises `StopIteration` automatically. The listing confirms they produce the *identical* sequence.

The generator is better on every axis that matters here. It is far **shorter** (four lines of obvious logic
versus a stateful class with manual index bookkeeping and an explicit `StopIteration`). It is less **error-prone**
(the class must remember to return `self` from `__iter__`, raise `StopIteration` correctly, and manage state by
hand, each a common bug). And it is **faster**, §69.3, because the generator resumes a suspended frame at the C
level, while the class's `__next__` is a *Python method call per item*, paying Python-level call dispatch on
every value.

The rule: **use a generator function (or a generator expression) to produce a sequence; reserve a hand-written
iterator class for when the iterator must also be a rich object** (extra methods, mutable configuration, a
meaningful identity beyond iteration). For the overwhelmingly common case, "yield a series of values", the
generator is shorter, safer, and faster. This is why the standard library and idiomatic code implement iteration
with generators, and why `itertools` (Chapter 33) composes them.

---

## 69.3 Measurement: generator vs iterator class

**Methodology.** `code/ch069/bench_gen_vs_class.py`. Consuming a 1000-element sequence produced by a generator
function versus an equivalent hand-written iterator class. `min` per call; ratio relative to the generator.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| consume 1000 items | min per call | ratio |
|---|---|---|
| generator function | **27,641 ns** | 1.00x |
| hand-written iterator class | **55,774 ns** | **2.02x** |

The generator is **2x** faster. The difference is the per-item cost of `next()`: the class's `__next__` is a
Python method, so each of the 1000 items pays Python-level call dispatch (frame setup, argument handling,
`self` binding); the generator resumes its suspended frame directly in C, with no per-item Python call. Over
1000 items that per-item overhead doubles the cost.

The rule: **prefer generators to hand-written iterator classes for producing sequences.** They are faster (2x
here, and the gap is per-item, so it holds at any length), shorter, and less bug-prone. The specializing
interpreter (Chapter 17) narrows many such gaps, but the *structural* difference here, a Python method call per
item versus a C frame resume, is real and persistent. Reach for an iterator class only when iteration is a
*secondary* feature of an object that needs to be more than an iterator; when the whole job is "produce these
values in order", the generator is both the idiomatic and the fast choice, exactly the pattern the rest of Deep F
builds on.

---

## 69.4 Edges and failure modes

**Returning an iterator where the caller loops twice.** §69.1. The second loop is silently empty. Return a list
or a re-iterable (an object whose `__iter__` makes a fresh iterator), or document the single-pass contract.

**Hand-writing `__iter__`/`__next__` for a plain sequence.** §69.3. Slower (2x), longer, and easy to get wrong
(forgetting `return self`, mishandling `StopIteration`). Use a generator unless the iterator must be a rich
object.

**An iterable whose `__iter__` returns `self`.** If a container's `__iter__` returns `self` (making it its own
single-use iterator), it can only be looped once, surprising callers who expect a container to re-iterate. A
re-iterable's `__iter__` must return a *fresh* iterator each call.

**Catching `StopIteration` too broadly.** `StopIteration` raised *inside* a generator (e.g. from a `next()` on
an inner iterator) does not end the generator, PEP 479 (3.7+) converts it to a `RuntimeError` to prevent silent
truncation. Do not rely on `StopIteration` propagating out of generator bodies; handle exhaustion explicitly.

**Mutating a collection while iterating it.** Iterators over `list`/`dict`/`set` detect concurrent modification
and raise `RuntimeError` (dict/set) or behave surprisingly (list). Iterate a copy, or collect changes and apply
them after.

**Assuming `len()` on an iterator.** An iterator has no length (it does not know how many values remain);
`len(iterator)` raises `TypeError`. Materialize to a list if you need a length, accepting the memory cost
(Chapter 9).

---

## 69.5 Connections

**Backward.** The laziness and constant memory of generators (the *why* to use them) are Chapter 9; this chapter
is the *how* (the protocol). `itertools` composing iterators is Chapter 33. The `for` statement and comprehensions
built on the protocol are Chapter 3. The method-call overhead the class pays is the specialization story of
Chapter 17.

**Forward.** Generator `send`/`throw`/`close` (two-way communication, the coroutine mechanism) and `yield from`
delegation are the next Deep F chapters. Async generators and `async for` (Chapters 10-11) extend the protocol to
`__aiter__`/`__anext__`. The C-level generator frame is a **Deep J** interpreter topic.

**Across books.** The iterator protocol is how Book II streams data into **Book III** without materializing it. A
**Book III** ingest pipeline yields documents from a generator (single-pass, constant memory), and every stage is
an iterator composed with the next, so a corpus of any size flows through in bounded memory. The §69.1 single-use
contract is also the source of the "why did my second pass process nothing" bug that appears when a stream is
consumed twice, which **Deep U** designs around at the pipeline seam.

---

## 69.6 Exercises

**1. Expose the single-use bug.** Return an iterator from a function, loop it twice, and show the second loop is
empty. Then return a list (or re-iterable) and show both loops work. Explain the `__iter__`-returns-self
mechanism.

**2. Implement both ways.** Write an iterator as a class and as a generator producing the same sequence, and
confirm they match. Explain what the generator machinery does for you that the class does by hand.

**3. Measure the gap.** Run §69.3's benchmark and confirm the generator is faster than the class. Explain the
per-item method-call cost and why the gap is length-independent per item.

**4. Build a re-iterable.** Write a container class whose `__iter__` returns a *fresh* generator each call, and
show it can be looped multiple times. Explain the difference from an iterator whose `__iter__` returns `self`.

**5. The design question.** Python separates iterable (re-loopable) from iterator (single-use), and offers
generators as the idiomatic iterator. Argue why this design is right. Your answer must use the §69.3 measurement,
explain the single-use contract and the bug it causes, and say when a hand-written iterator class is still
justified.

---

## 69.7 Summary and cross-references

- An **iterable** (`__iter__` returns a *fresh* iterator) can be looped many times; an **iterator** (`__next__`
  + `__iter__` returns `self`) is **single-use**, a second loop is silently empty. `for` is sugar over `iter()` +
  `next()` until `StopIteration`.
- A **generator function** implements the protocol in C: shorter, safer, and faster than a hand-written
  `__iter__`/`__next__` class.
- **Measured:** consuming 1000 items is **2x** faster from a generator than from an iterator class (27.6 us vs
  55.8 us), because the class pays a Python `__next__` call per item while the generator resumes a C frame.
- **Return a re-iterable/list if callers loop more than once; use generators to produce sequences;** reserve
  iterator classes for rich objects. Beware PEP 479, concurrent modification, and `len()` on iterators.

**Cross-references.** Generator laziness and memory → Chapter 9. `itertools` → Chapter 33. `for`/comprehensions →
Chapter 3. Method-call specialization → Chapter 17. `send`/`throw`/`yield from`, async generators → the rest of
Deep F and Chapters 10-11. The generator frame → Deep J. The streaming seam → Deep U.
