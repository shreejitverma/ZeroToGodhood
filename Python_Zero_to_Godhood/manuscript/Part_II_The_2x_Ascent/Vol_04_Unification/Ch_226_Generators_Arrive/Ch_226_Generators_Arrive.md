# Chapter 16: Generators Arrive

Chapter 15 showed the iterator protocol making `for` universal, and noted its one friction: writing an iterator by hand, `__iter__`, `__next__`, and explicit state management, is verbose. **Python 2.2 (2001) fixed that friction with generators** (PEP 255), and in doing so gave Python one of its most powerful and characteristic features. A function containing `yield` becomes an iterator *automatically*: the function's local variables *are* the iterator's state, and each `yield` is a `__next__` that pauses the function and resumes it exactly where it left off.

Generators and the iterator protocol arrived in the same release, and that is no accident, generators are the ergonomic way to *create* iterators. But their consequence runs far deeper than convenience. Because a generator produces values one at a time, holding only its current frame, it makes **laziness** trivial: a generator can be *infinite* (a list of all natural numbers is impossible; a generator producing them is three lines) or *streaming* (gigabytes processed in constant memory, Chapter 91). And the suspend-and-resume mechanism generators introduced, freeze the function mid-execution, thaw it later, is the seed that grew into coroutines and `async`/`await` (Deep J). Deep F owns that full machinery; this release chapter shows generators as they work today, on the verification interpreters, and reads what "iterators you can write easily" unlocked.

## Section index

- **16.1** The constraint: iterators were tedious to write
- **16.2** A function with yield is an iterator
- **16.3** yield pauses and resumes: laziness, mechanically
- **16.4** Infinite and streaming: what laziness enables
- **16.5** Generator expressions: laziness with comprehension syntax
- **16.6** Edges: the generator's subtleties
- **16.7** Connections
- **16.8** Exercises
- **16.9** Summary and cross-references

Listings live under `code/ch226/` and are re-executed by `make verify` on the verification interpreters.

---

## 16.1 The constraint: iterators were tedious to write

The iterator protocol (Chapter 15) was a triumph of generality: two methods, and any object could participate in Python's entire iteration vocabulary. But generality is not ergonomics, and *writing* an iterator by hand was tedious. Chapter 15's `CountdownIterator` needed a class, an `__init__` to store state, an `__iter__` returning `self`, and a `__next__` that manually tracked position and raised `StopIteration`, a dozen lines of boilerplate for a three-value countdown, and the state management (which variable holds "where am I") got harder as the iteration logic got more complex.

The friction was that the iterator's *state* had to be lifted out of the natural control flow into explicit instance attributes. A countdown is naturally `while n > 0: emit n; n -= 1`, a loop with a local variable, but to make it an iterator, you had to *invert* it: store `n` as `self.n`, and reconstruct one step of the loop each `__next__` call. This inversion (natural loop becomes explicit state machine) is error-prone and unreadable for anything nontrivial, a parser, a tree walk, a paginated fetch. The constraint 2.2's generators answered is that **the natural way to write iteration is a loop with local variables, and iterators forced you to abandon that**. Generators let you keep the loop.

---

## 16.2 A function with yield is an iterator

```python
# code/ch226/l01_generators_arrive.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- a generator function returns an iterator, automatically ---
  calling the function returns : generator
  it IS an iterator (has __next__) : True
  list(countdown(3)) : [3, 2, 1]
  no __iter__/__next__ written by hand - `yield` generated them.
  the function's locals ARE the iterator's state (Chapter 15's
  hand-built CountdownIterator, in three lines)
```

**A function containing `yield` returns a generator, which *is* an iterator, with no boilerplate.**
`countdown` is written as the natural loop, `while n > 0: yield n; n -= 1`, and calling it returns a `generator` object that has `__next__` and works with `for`, `list`, and everything else. The dozen-line hand-built `CountdownIterator` of Chapter 15 became three lines, and crucially, the *state* (`n`) is an ordinary local variable, not a lifted-out instance attribute. The `yield` keyword does all the work: it turns the function into a generator, makes the function's frame the iterator's state, and makes each `yield` a `__next__` return. This is the ergonomic fix, iterators you write as loops, and it is why almost every custom iterator in modern Python is a generator, not a hand-written protocol class.

**The compiler recognises `yield` and changes the function's nature.**
A function with `yield` anywhere in its body is compiled *differently*, calling it does not run the body but constructs a generator object with the body suspended at the start. This is why the presence of `yield` transforms an ordinary function into a generator function (Deep F owns the bytecode-level mechanism). The transformation is invisible in the source, the function looks normal, but its behaviour is fundamentally different: it produces a lazy iterator rather than computing and returning a value. This dual nature, looks like a function, behaves like an iterator factory, is the source of generators' power and of a few of their subtleties (§16.6).

---

## 16.3 yield pauses and resumes: laziness, mechanically

```text
--- yield PAUSES and RESUMES: the function runs between next()s ---
  after creating generator : trace=[]  (nothing ran yet)
  after first next()       : trace=['before yield 1']
  after second next()      : trace=['before yield 1', 'resumed, before yield 2']
  the body runs LAZILY - only when next() asks. yield freezes the
  frame mid-function and next() thaws it. this suspend/resume is
  what Deep F elaborates into coroutines and async/await
```

**`yield` freezes the function mid-execution and `next()` thaws it, so the body runs lazily, only when asked.**
The trace proves it: creating the generator runs *nothing* (`trace=[]`), the body has not executed. The first `next()` runs the body up to the first `yield` (`trace=['before yield 1']`) and pauses. The second `next()` resumes *right after* that yield and runs to the next one. This is the suspend-and-resume mechanism, `yield` freezes the entire function frame (locals, instruction pointer, everything) in place, and `next()` restores it and continues, and it is what makes generators *lazy*: the body executes incrementally, one `yield`-to-`yield` segment per `next()`, only as values are demanded. The function is not "called and returned"; it is "resumed and paused", repeatedly, which is a fundamentally different execution model from ordinary functions.

**This suspend/resume is the seed of coroutines and async.**
A function that can pause mid-execution and resume later, preserving its state, is doing something profound: it is *cooperatively yielding control*. In 2.2 this served iteration (yield a value, pause, resume for the next). But the *same* mechanism, freeze a frame, resume it later, is exactly what a coroutine needs, and Python's later evolution (`yield` receiving values via `send`, then `yield from` for delegation, then `async`/`await` as dedicated syntax) built directly on generators' suspend/resume. Chapter 102 (Deep J) shows `await` traversing a chain of suspended coroutine frames, and those frames are generators' frames, generalised. The 2.2 generator is where Python learned to pause a function, and everything asynchronous grew from that.

---

## 16.4 Infinite and streaming: what laziness enables

```text
--- laziness: a generator holds one frame, not the whole sequence ---
  first 5 of an INFINITE generator : [0, 1, 2, 3, 4]
  naturals() never ends, yet costs one frame of memory. a list of
  all naturals is impossible; the generator is trivial. that is
  laziness (Chapter 91): produce on demand, hold only the present
```

**A generator can be infinite, because it holds one frame, not the whole sequence.**
`naturals()` is `n = 0; while True: yield n; n += 1`, an *infinite* sequence, and `itertools.islice` takes the first five. A list of all natural numbers is impossible (infinite memory); the generator is trivial (one frame, one integer). This is laziness at its most dramatic: the generator produces values on demand and holds only its *current* state, so the sequence's *size* is irrelevant to its *memory*. An infinite generator, a generator streaming a terabyte file line by line, and a generator producing three values all cost the same, one frame, because none of them materialises the sequence. The old indexing `for` (Chapter 15) could not express any infinite or streaming sequence; generators make them ordinary.

**Laziness is the memory model that Chapter 91's entire streaming discipline rests on.**
Because a generator holds only the present, processing arbitrarily large data in *constant* memory becomes natural: a generator pipeline (read → transform → filter → write) passes one element through at a time, never holding the whole dataset, which is Chapter 91's constant-memory streaming (Deep K). This is the practical payoff of generators for real systems: the shared trading system streams its market-data feed as a generator (Chapter 91, Chapter 131), processing an unbounded tick stream without ever materialising it, and that is only possible because generators make lazy, streaming iteration trivial to write. Generators turned laziness from a theoretical possibility (you *could* hand-build a lazy iterator) into the default, easy way to process sequences, which reshaped how Python handles large and streaming data.

---

## 16.5 Generator expressions: laziness with comprehension syntax

```text
--- generator expressions: laziness with comprehension syntax ---
  [x*x ...] materialises : [0, 1, 4, 9, 16]
  (x*x ...) is lazy      : generator, summed = 30
  parentheses instead of brackets make a generator expression -
  the comprehension's readability with the generator's laziness,
  the shape a streaming pipeline is built from (Chapter 91)
```

**A generator expression is a comprehension that is lazy: parentheses instead of brackets, and nothing is materialised until asked.**
`[x*x for x in range(5)]` builds the whole list immediately; `(x*x for x in range(5))` builds a *generator* that produces values on demand. The syntax difference is one character (parens for brackets), and the semantic difference is materialisation versus laziness. Generator expressions (added shortly after generators, Python 2.4) give you the comprehension's readability with the generator's memory profile, which is why `sum(x*x for x in range(5))` is idiomatic: it streams the squares through `sum` without ever building the list. This is the shape a streaming pipeline is built from, chain generator expressions (each lazy) and data flows one element at a time from source to sink, which is Chapter 91's pipeline pattern in its most compact form.

**The list-vs-generator choice is the materialise-vs-stream decision, in syntax.**
`[...]` says "build the whole thing now" (fine for small data, needed for re-iteration or indexing); `(...)` says "produce on demand" (essential for large or infinite data, single-pass). The one-character syntax difference encodes a real memory-and-semantics choice (Chapter 91's whole subject), and knowing which to reach for, materialise when you need the list, stream when you do not, is part of writing memory-conscious Python. Generator expressions made the streaming choice as easy to *write* as the materialising one, which is the same "make laziness easy" achievement as generators themselves, applied to comprehension syntax.

---

## 16.6 Edges: the generator's subtleties

**A generator is single-pass and exhausted after one iteration.**
Like any iterator (Chapter 15's edge), a generator runs once, after it is consumed, looping it again yields nothing. `g = countdown(3); list(g); list(g)` gives `[3,2,1]` then `[]`. This is Chapter 91's silent-exhaustion bug, and it bites when a generator is passed to code that iterates it twice (once to count, once to process). The fix is to materialise (`list(g)`) if you need multiple passes, or to create a fresh generator each time.

**The body does not run until the first `next()`.**
Because calling a generator function only *constructs* the generator (§16.3), any code before the first `yield`, including argument validation, does not run until the generator is first iterated. A generator that should validate its arguments eagerly must be split (a normal function that validates, then returns an inner generator), Chapter 102's identical edge for coroutines. "The generator's arguments were wrong but it did not raise until I looped it" is this deferred execution.

**`return` in a generator ends it (and its value rides `StopIteration`).**
A `return` in a generator terminates iteration (raises `StopIteration`), and since Python 3.3 the returned value is carried on `StopIteration.value` (used by `yield from` delegation, Deep F). A bare `return` is the normal way to end a generator early; `return value` is meaningful only to `yield from`. Confusing generator `return` (ends iteration) with function `return` (produces the result) is a common early misunderstanding.

**And `StopIteration` raised inside a generator is a `RuntimeError` (PEP 479).**
If a `StopIteration` escapes a generator body (rather than the generator returning normally), Python 3.7+ converts it to `RuntimeError`, because a `StopIteration` leaking through a generator used to silently truncate it, masking bugs (Chapter 15's edge, Deep F's full story). This means calling `next()` on an inner iterator inside a generator needs care, an unexpected `StopIteration` from the inner iterator must not leak. The interaction of generators with the protocol's terminator exception is the subtlest corner, and PEP 479 made it safe.

---

## 16.7 Connections

**Backward.**
The iterator protocol generators implement is Chapter 15; the object model where a generator is an object is Chapter 4; the values (readability, the natural loop preserved) are Chapter 3; frames (which generators suspend) are Deep A and Deep H (Chapter 54).

**Forward.**
The full generator/coroutine machinery, `send`, `yield from`, `throw`, is Deep F; laziness and streaming pipelines are Chapter 91 (Deep K); `async`/`await` built on generators' suspend/resume are Deep J (Chapter 102); `itertools` (the lazy-iterator toolkit) is Chapter 33 (Deep Q); PEP 479's `StopIteration` fix is Deep F.

**Across books.**
Generators are Python's coroutine seed; **Book I**'s C++20 coroutines are a from-scratch design for the same suspend/resume capability (compiler-generated state machines), and the two converge on the same use, lazy generators and async I/O, from different mechanisms. The shared system's market-data pipeline is a Python generator chain and a C++ coroutine range, the same "produce on demand, hold the present" abstraction in both languages, which is Chapter 91's streaming realised on both sides of the boundary.

---

## 16.8 Exercises

**1. Rewrite the hand-built iterator.** Take Chapter 15's `CountdownIterator` class and rewrite it as a generator; count the lines saved and confirm identical behaviour. This is the ergonomic win, measured.

**2. Trace the suspend/resume.** Instrument a generator with print statements before and after each `yield`; call `next()` step by step and confirm the body runs incrementally. This is §16.3, felt.

**3. Build an infinite pipeline.** Chain three generator expressions (source → transform → filter) over an infinite generator; take the first ten with `islice`; confirm constant memory with `tracemalloc` (Chapter 91). Explain why the list version is impossible.

**4. Hit the deferred-validation edge.** Write a generator that should validate its arguments; show the validation does not run until first iteration; fix it with the eager-wrapper pattern. Relate to Chapter 102.

**5. The design question.** Generators unified "writing an iterator" with "writing a loop" by making `yield` suspend the frame, at the cost of single-pass semantics and deferred execution (the edges). Argue whether this trade was right, and how the *same* suspend/resume mechanism serving both iteration (2.2) and async (later) validates the design, one mechanism, two decades of features, or complicates it (the `StopIteration`/PEP 479 corner). Use Deep J's async as the payoff.

---

## 16.9 Summary and cross-references

- **Python 2.2 (2001) added generators (PEP 255)**: a function with `yield` becomes an iterator automatically, the function's locals *are* the iterator's state, turning Chapter 15's dozen-line hand-built iterator into three lines and letting you write iteration as the natural loop.
- **`yield` pauses and resumes the function frame**: creating a generator runs nothing, each `next()` runs one `yield`-to-`yield` segment, so the body executes lazily, on demand, this suspend/resume is the seed of coroutines and `async`/`await` (Deep J).
- **Laziness becomes trivial**: a generator holds one frame, not the whole sequence, so it can be *infinite* (all naturals in three lines) or *streaming* (gigabytes in constant memory, Chapter 91), which the old indexing `for` could never express.
- **Generator expressions** (parens for brackets) give comprehension readability with generator laziness, `sum(x*x for x in ...)` streams without materialising, the compact form of a streaming pipeline.
- **The edges** are the iterator's plus generators' own: single-pass exhaustion, deferred execution until first `next()`, `return` ending iteration (value on `StopIteration`), and PEP 479's fix for `StopIteration` leaking through a generator, all owned by Deep F.

**Cross-references.** The iterator protocol → Chapter 15. The object model → Chapter 4. Frames → Chapter 54, Deep A. The full coroutine machinery → Deep F. Laziness and streaming → Chapter 91. async/await → Chapter 102, Deep J. `itertools` → Chapter 33. C++ coroutines → Book I.
