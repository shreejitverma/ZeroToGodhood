# Chapter 9: Iterators, Generators, and `yield from` (Python 3.3)

A data engineer needs the sum of the squares of the first billion integers. They write the obvious
thing, `sum([i*i for i in range(1_000_000_000)])`, and the process is killed by the operating system
before it finishes, because the list comprehension tried to build a billion-element list in memory
first. They delete two characters, the square brackets, making it `sum(i*i for i in range(...))`, and
it runs in constant memory and completes.

The difference between those two lines is the difference between a list and a generator, and it is not
small. Measured on a million squares, the list costs **38.6 MB** and the generator costs **400
bytes**, a ratio of about **101,000x**, and the generator's cost does not grow with the count: it is
one suspended frame whether it will yield a thousand items or a trillion. That single property, laziness
through a suspended frame, is what this chapter builds, and it is the mechanism that runs all the way
forward to `async`/`await`.

This chapter is the canonical home for the iteration model that pervades Python: `for` loops,
comprehensions, unpacking, `in`, and ultimately `async for` all rest on it. We build it from the
bottom: the iterator protocol, then generators as the ergonomic way to write iterators, then `yield
from` (PEP 380), the delegation operator that turned generators into composable coroutines and laid
the last stone before native `async`/`await` (Chapter 11). Chapter 5 introduced generator
`send`/`throw`/`close` at the 2.5 milestone; here we complete the model. We close with implicit
namespace packages (PEP 420), the other headline 3.3 feature.

## Section index

- **9.1** The iterator protocol
- **9.2** Generators: iterators written as suspended frames
- **9.3** `yield from`: delegation and the coroutine bridge (PEP 380)
- **9.4** Implicit namespace packages (PEP 420)
- **9.5** Measurement: the memory-for-speed trade
- **9.6** Edges and failure modes
- **9.7** Connections
- **9.8** Exercises
- **9.9** Summary and cross-references

Listings live under `code/ch009/` and are re-executed by `make verify` on both interpreters.

---

## 9.1 The iterator protocol

**Why this exists.** Python decouples *consuming* a sequence from *being* a sequence, so the same
`for` loop drives a list, a file, a database cursor, an infinite counter, or a network stream. The
contract has two halves: an **iterable** implements `__iter__()`, returning a fresh **iterator**; an
**iterator** implements `__next__()`, returning the next item or raising `StopIteration`, and
`__iter__()` returning `self` (so an iterator is also iterable).

```python
# code/ch009/l01_iterator_protocol.py
class Countdown:
    def __init__(self, n):
        self.n = n
    def __iter__(self):
        return self
    def __next__(self):
        if self.n <= 0:
            raise StopIteration
        self.n -= 1
        return self.n + 1
```

Verified output (CPython 3.13.5):

```text
--- a hand-written iterator; for-loops speak exactly this protocol ---
  list(Countdown(3)): [3, 2, 1]
--- the core opcodes of any for-loop ---
   GET_ITER
   FOR_ITER
   STORE_FAST
   JUMP_BACKWARD
   END_FOR
```

A `for` loop compiles to `GET_ITER` (call `__iter__` once) followed by a `FOR_ITER` loop (call
`__next__`, jump out on `StopIteration`). The crucial detail: `StopIteration` is *control flow*, not
an error. `FOR_ITER` catches it internally to end the loop, which is why a stray `StopIteration` raised
*inside* a generator body is a bug, and PEP 479 converts such a leak into `RuntimeError` (§9.6).

**The senior-engineer contrast.** Java separates `Iterable` from `Iterator` with a *look-ahead*
model, `hasNext()` then `next()`. Python has no `hasNext()`; the iterator is exhaustion-by-exception,
`StopIteration` on `next()`. C++ iterators are *positions* compared against an `end()` sentinel.
Python's model is the most minimal of the three: one method, one sentinel exception, and a hard rule
that **iterators are single-pass and stateful**. Once exhausted, they stay exhausted, which is the
source of a whole class of silent bugs (§9.6).

---

## 9.2 Generators: iterators written as suspended frames

**Why this exists.** Writing the `Countdown` class is tedious; the state machine (`self.n`, the
`StopIteration`) is boilerplate. A **generator function**, any `def` containing `yield`, lets you write
the logic and have CPython synthesize the iterator.

```python
# code/ch009/l02_generators.py
def gen_squares(n):
    for i in range(n):
        yield i * i
```

Verified output (CPython 3.13.5):

```text
--- a generator wraps a live, suspended frame ---
  type(g)              : generator
  g.gi_frame is not None: True
  list(g)              : [0, 1, 4, 9]
--- laziness means one frame, not N items, regardless of size ---
  gen_squares(10**9) created: generator
  it allocated ONE frame, not a billion-element list.
  taking the first 5 with next(): [0, 1, 4, 9, 16]
```

**What the interpreter actually does** (the mechanism from Chapter 5, now named). A generator wraps a
`PyGenObject` holding a `gi_frame`. At each `yield`, CPython saves the resume offset (`f_lasti`) and
the evaluation-stack depth in that frame, marks the generator suspended, and returns control; the
frame is *not* freed, it lives on the heap. `next()`/`send()` re-attach the frame and resume. This is
what makes generators lazy and *O*(1) in memory, and it is the chapter opening quantified:
`gen_squares(10**9)` allocates one frame, not a billion-element list. The two-way protocol,
`send(value)`/`throw(exc)`/`close()`, was Chapter 5; a generator is a producer (`next`) *and* a
consumer (`send`).

---

## 9.3 `yield from`: delegation and the coroutine bridge (PEP 380)

**Why this exists.** Before 3.3, a generator that wanted to yield everything from a sub-generator *and*
correctly forward `send`/`throw`/`close` and capture the sub-generator's return value had to hand-write
a fragile loop. **PEP 380's `yield from`** makes the delegating generator a transparent channel:
yielded values pass straight out, sent values pass straight in, thrown exceptions are raised inside the
sub-generator, `close()` propagates, and when the sub-generator returns, its return value becomes the
value of the `yield from` expression (carried out via `StopIteration.value`).

```python
# code/ch009/l03_yield_from.py
def subgen():
    received = yield "a"
    yield f"got {received}"
    return "subgen-result"

def delegator():
    result = yield from subgen()       # transparent channel; captures the return
    print("  delegator captured return:", result)
    yield "after"
```

Verified output (CPython 3.13.5):

```text
--- yield from routes send() into the sub-generator and captures return ---
  next(d)   : a
  d.send('X'): got X
  delegator captured return: subgen-result
  next(d)   : after
--- the everyday use: composition without manual loops ---
  flatten([1,[2,[3,4],5],6]): [1, 2, 3, 4, 5, 6]
```

Trace the routing: `next(d)` produces `"a"` from `subgen`; `d.send("X")` routes `"X"` into `subgen`,
where it becomes the value of `received`, producing `"got X"`; the next `next(d)` runs `subgen` to its
`return`, whose value `"subgen-result"` is captured into `result`, and then `delegator` continues to
`"after"`. That send-routing and return-capture is what a hand-written loop got wrong, and it is why
`yield from` is more than a flattening shortcut, though flattening is its everyday use.

**The coroutine bridge.** `yield from` made it possible to write a generator that delegates to another
generator that performs I/O and yields control upward, the exact pattern early `asyncio` used
(`@asyncio.coroutine` plus `yield from`) before Python 3.5 gave it dedicated syntax. When you read
`await expr` in Chapter 11, picture `yield from` with a typed, awaitable-only channel: the suspension
mechanism is the same heap frame you have been building since Chapter 5.

---

## 9.4 Implicit namespace packages (PEP 420)

**Why this exists.** Through 3.2, a directory was a package only if it contained `__init__.py`. That
blocked a real use case: distributing one logical package (`company.core`, `company.plugins`) across
multiple installs, since each separate distribution would need its own `company/__init__.py` and they
would collide. **PEP 420** lets a package span directories with *no* `__init__.py`: a namespace
package. During `import foo`, `PathFinder` scans `sys.path`; if it finds no `__init__.py` but one or
more directories named `foo`, it accumulates *all* of them into a namespace package whose `__path__` is
the list of them and whose `__file__` is `None`.

```python
# code/ch009/l04_namespace_packages.py
# builds path1/company/core and path2/company/extra in a temp dir,
# with NO company/__init__.py in either, then imports one 'company' from both.
```

Verified output (CPython 3.13.5):

```text
--- one importable 'company' namespace, two contributing directories ---
  company.__file__      : None
  number of __path__ entries: 2
  company.core.VALUE    : from path1
  company.extra.VALUE   : from path2
```

Two distinct directories contribute submodules to one importable `company` namespace, and the
signature is `__file__ is None` with a multi-entry `__path__`. This is how large ecosystems ship
plugins (`zope.*`, `google.cloud.*`, an internal `company.*`) as independent, separately-installable
distributions. The trade-off, and the footgun: namespace packages are slightly slower to resolve (the
finder must scan all of `sys.path` rather than stop at the first hit), and accidentally omitting an
`__init__.py` from a *regular* package silently turns it into a namespace package, a subtle "why is my
package data missing" bug. Use namespace packages deliberately, for genuinely split distributions; use
a normal `__init__.py` package otherwise. The complete import machinery is **Deep G**.

---

## 9.5 Measurement: the memory-for-speed trade

The chapter opened with the memory number. Here is the full trade, both directions, because a generator
is not simply "better than a list."

**Methodology.** `code/ch009/bench_generator_vs_list.py`. Memory is peak allocation for a million
squares via `tracemalloc`, which is deterministic. Speed is `min` over 15 batches of building and fully
consuming (`sum`) a smaller collection, M = 10,000, small enough that the list fits comfortably.
CPython 3.13.5, `-O2`, Apple M3 Pro, macOS 27.0, arm64.

| dimension | list comprehension | generator |
|---|---|---|
| memory (1M squares) | 38.6 MB | **400 bytes** (~101,000x smaller) |
| build-and-consume speed (M=10k) | 1.00x | **1.24x slower** |

The two numbers point in opposite directions, and that is the whole lesson.

**Memory is a rout, and one-directional.** A generator is a single suspended frame regardless of how
many items it will produce, so its footprint is constant and tiny. For large or streamed data, this is
not an optimization, it is the difference between running and being killed by the OS, which is the
chapter's opening scenario.

**Speed favors the list for small, fully-consumed data**, by about 1.24x. When you will materialize
and consume everything anyway, the list comprehension does its work in a tight C loop, while the
generator pays a Python-level resume, a frame re-attach and a `yield`, per item. So the generator's
laziness is pure overhead when you were going to consume all of it immediately and it fits in memory.

The rule: **reach for a generator for size and laziness, not for speed on small data.** Use it when the
sequence is large, infinite, streamed, or when you might stop early; use a list comprehension when the
data is small, fits comfortably, and you need it materialized (for `len`, indexing, or a second pass).
The two-character difference in the chapter opening is a memory decision, and it only pays when memory
is the constraint.

---

## 9.6 Edges and failure modes

**Iterators are single-pass.** §9.1. Exhausting a generator (or any iterator) leaves it empty; a second
`for`/`sum`/`list` over it yields nothing, silently. This bites hardest with `zip`, `map`, and
`dict.items()` views passed to a function that iterates twice. Re-create the generator, or materialize
to a list when you need multiple passes.

**`list()`-ing a generator you only iterate once.** §9.5. Discards the memory win for nothing. Iterate
directly; materialize only for `len`, random access, or reuse.

**A bare `StopIteration` inside a generator.** PEP 479 converts it to `RuntimeError`, because a leaked
`StopIteration` would silently end the enclosing loop rather than propagate. Never raise it manually to
end a generator; just `return`.

**`return` inside a generator.** Sets `StopIteration.value` for `yield from` capture (§9.3); it does
*not* return a value to a plain `next()` caller. A plain consumer never sees it.

**The namespace-package footgun.** §9.4. A dropped `__init__.py` silently creates a namespace package.
If package data or `__init__` side effects vanish, check for an accidentally-omitted `__init__.py`
first.

**Hand-rolling `itertools`.** Before writing generator plumbing, reach for `itertools` (`chain`,
`islice`, `tee`, `groupby`): it is C-speed and composable (**Deep Q**). In particular, `itertools.tee`
is the right tool for the two-passes-over-one-iterator problem above.

---

## 9.7 Connections

**Backward.** Generator `send`/`throw`/`close` and the frame-suspension origin are Chapter 5, at the
2.5 milestone; this chapter names and completes that mechanism. Comprehensions versus generator
expressions, and the isolation of the comprehension's loop variable, are Chapter 3. The `f_lasti`
resume offset a generator saves is Chapter 2's code-object machinery.

**Forward.** Native `async`/`await`, which generalizes `yield from` into a typed, awaitable-only
channel over the same heap frame, is Chapter 11, and `asyncio` proper is Chapters 10-11. The complete
import machinery behind namespace packages is **Deep G**. `itertools` is **Deep Q**. Benchmarking
memory and speed together is **Deep K**.

**Across books.** Laziness is also how Python feeds a data pipeline into **Book III** without
materializing it: a generator that reads records from a file, transforms them, and yields them one at a
time is the streaming stage that keeps a retrieval-index build's memory flat regardless of corpus size.
The order-book's tick stream is exactly such a generator, consumed once, never listed. The Book II to
Book III seam (**Deep U**) is built on the *O*(1)-memory property this chapter measures.

---

## 9.8 Exercises

**1. Reproduce the OOM avoidance.** Write the chapter's opening two lines (list vs generator) at a size
large enough that the list is uncomfortable but not fatal, and measure both memory footprints to the
standard of §9.5. Then find the size at which the generator's speed disadvantage (§9.5) is outweighed
by the list becoming too large to allocate at all.

**2. Catch the single-pass bug.** Write a function that takes an iterable and computes both its sum and
its length by iterating it twice. Show that it works for a list argument and silently returns a wrong
length (zero) for a generator argument. Then fix it two ways, once by materializing and once with
`itertools.tee`, and state the memory cost of each fix.

**3. Trace the routing by hand.** For the `yield from` listing in §9.3, write down, before running,
exactly what each of `next(d)`, `d.send("X")`, and the final `next(d)` returns and why, tracking where
`"X"` goes and where `"subgen-result"` ends up. Then confirm. Which single line would you change to make
`result` come back as `None` instead?

**4. Build the namespace footgun.** Create a regular package with an `__init__.py` that sets a
package-level constant, confirm the constant is importable, then delete the `__init__.py` and show the
constant is gone while the submodules still import. Explain, using §9.4, exactly what changed in how
`PathFinder` resolved the package.

**5. The design question.** Python's iterator protocol is exhaustion-by-exception with no `hasNext()`,
unlike Java. Argue the trade. Your answer must address why a single-pass, no-look-ahead iterator is a
better fit for generators and infinite sequences than Java's model, what it costs when you genuinely
need to peek, and how `itertools.tee` and materialization recover the look-ahead Java has built in.

---

## 9.9 Summary and cross-references

- The **iterator protocol** is `__iter__` (returns an iterator) plus `__next__` (next item or
  `StopIteration`); `for` compiles to `GET_ITER`/`FOR_ITER`. Iterators are **single-pass**.
- **Generators** synthesize iterators from `yield`-containing functions by **suspending a heap frame**
  (`gi_frame`/`f_lasti`), giving *O*(1)-memory laziness and the two-way `send`/`throw`/`close` protocol.
- **`yield from`** (PEP 380) delegates transparently to a sub-generator, routing values and exceptions
  and **capturing its return value**, and is the direct conceptual ancestor of `await`.
- **Implicit namespace packages** (PEP 420) let one package span multiple directories with no
  `__init__.py` (`__file__ is None`, multi-entry `__path__`), enabling split distributions.
- **Measured:** a generator over a million squares costs **400 bytes** against the list's **38.6 MB**
  (~101,000x), but is about **1.24x slower** to build and consume small data. Generators are for size
  and laziness, not speed.

**Cross-references.** Generator `send`/`throw`/`close` and frame origins → Chapter 5. Comprehensions
versus generator expressions → Chapter 3. Native `async`/`await` and `asyncio` → Chapters 10-11. The
import machinery → Deep G. `itertools` → Deep Q. Benchmarking → Deep K. The streaming seam to Book III
→ Deep U.
