# Chapter 11: Native Async/Await and New Operators (Python 3.5)

In Python 3.4, a coroutine was a generator. That was clever, and it was a trap: because a coroutine
implemented the iterator protocol, you could accidentally `for`-loop over one, or call `next()` on it,
or pass it somewhere that expected a sequence, and instead of an error you got confusing, subtly-wrong
behavior. And `yield from` meant two unrelated things depending on context: delegate to a sub-generator,
or await I/O. The pattern worked, but it was built on a type that was pretending to be two things at
once.

Python 3.5 fixed this by making a coroutine its own type. `async def` now produces a `PyCoroObject`
that has `__await__` but *not* `__next__`, so the misuses above become clean errors instead of quiet
bugs:

```python
async def fetch():
    return 42
for x in fetch():      # TypeError: 'coroutine' object is not iterable
    ...
```

This chapter completes the async through-line this book has been building since Chapter 5: the
suspendable frame (Chapter 5), delegated with `yield from` (Chapter 9), driven by an event loop
(Chapter 10), now gets first-class syntax with `async def`, `await`, `async for`, and `async with`
(PEP 492). Two more operators arrived the same release: PEP 465's `@` matrix-multiplication operator
and PEP 448's generalized unpacking. This chapter is the canonical home for the async/await *syntax and
object model*; the event loop it drives is Chapter 10 and **Deep H**.

## Section index

- **11.1** Native coroutines: `async def`, `await`, and `PyCoroObject` (PEP 492)
- **11.2** `async for` and `async with`
- **11.3** The matrix-multiplication operator `@` (PEP 465)
- **11.4** Extended unpacking generalizations (PEP 448)
- **11.5** Measurement: the cost of `await`
- **11.6** Edges and failure modes
- **11.7** Connections
- **11.8** Exercises
- **11.9** Summary and cross-references

Listings live under `code/ch011/` and are re-executed by `make verify` on both interpreters.

---

## 11.1 Native coroutines: `async def`, `await`, and `PyCoroObject` (PEP 492)

**Why this exists.** The chapter opening is the why: through 3.4 a coroutine *was* a generator, which
conflated two protocols and let a coroutine be misused as an iterator. **PEP 492** split them.

```python
# code/ch011/l01_native_coroutine.py
async def get_val():
    return 42
c = get_val()                                  # does NOT run the body; returns a coroutine
```

Verified output (CPython 3.13.5):

```text
--- a coroutine is a distinct, non-iterable type ---
  type(get_val())     : coroutine
  has __await__       : True
  has __next__        : False
  for-loop over it    -> TypeError: 'coroutine' object is not iterable
--- calling it runs nothing until a loop drives it ---
  asyncio.run(get_val()): 42
--- await accepts any awaitable: implement __await__ yourself ---
  await Delayed(...)  : custom-result
```

Calling an `async def` builds a `PyCoroObject` and runs *nothing* until it is driven by `await` or an
event loop; the body of `get_val` does not execute when you call it, only when `asyncio.run` drives it.
The coroutine has `__await__` but no `__next__`, so the `for`-loop is a clean `TypeError`, which is
exactly the safety PEP 492 bought. And `await` accepts any **awaitable**: a coroutine, or any object
whose type implements `__await__` (the C `am_await` slot in the `tp_as_async` table) and returns an
iterator, which the `Delayed` class demonstrates by yielding once to suspend and then returning a value.

**What the interpreter actually does.** `await` compiles to `GET_AWAITABLE` followed by a
`SEND`/`YIELD_VALUE` resume loop, the modern descendant of Chapter 9's `yield from` machinery, now
driving an awaitable. A coroutine's code object opens with `RETURN_GENERATOR` (a coroutine *is* a kind
of generator frame under the hood), and the `SEND`/`END_SEND` pair replaced the pre-3.11 `YIELD_FROM`;
material showing `YIELD_FROM` for `await` predates 3.11. The suspension is still the heap frame you have
been tracking since Chapter 5: `await` saves the frame, hands control to the loop, and resumes when the
awaitable completes. (The exact opcodes shift again on 3.14, which is why the listing states the shape
in prose rather than pinning a disassembly.)

---

## 11.2 `async for` and `async with`

PEP 492 also added asynchronous versions of the two iteration and context constructs, for the common
case where *advancing an iterator* or *acquiring a resource* is itself I/O. `async for` drives the
asynchronous iterator protocol (`__aiter__` returns an async iterator; `__anext__` is a coroutine
returning the next item or raising `StopAsyncIteration`); `async with` drives `__aenter__`/`__aexit__`,
both coroutines, so acquiring or releasing a connection can `await`. Async comprehensions followed in
3.6 (PEP 530).

```python
# code/ch011/l02_async_for_with.py
async def demo():
    collected = [x async for x in AsyncRange(3)]      # async comprehension (PEP 530)
    async with AsyncCtx():
        print("  inside async with")
    return collected
```

Verified output (CPython 3.13.5):

```text
--- async iteration and an async context manager ---
  __aenter__ (awaitable acquire)
  inside async with
  __aexit__ (awaitable release)
  collected: [0, 1, 2]
```

The order confirms the protocol: `__aenter__` awaits and returns, the body runs, `__aexit__` awaits and
releases, and the async comprehension collected all three values. These are the building blocks for
async database cursors, streaming HTTP bodies, and async connection pools, anywhere "get the next item"
or "open the resource" must await I/O.

---

## 11.3 The matrix-multiplication operator `@` (PEP 465)

**Why this exists.** The numeric community needed a clean infix operator for matrix multiplication:
before 3.5, `A.dot(B).dot(C)` nested awkwardly and `*` was already element-wise. **PEP 465** added `@`
(and in-place `@=`), mapping to `__matmul__`/`__rmatmul__`/`__imatmul__` and the C slot
`nb_matrix_multiply`. Like every operator, it carries *no* built-in meaning and dispatches to the
operands' type:

```python
# code/ch011/l03_operators.py (excerpt)
class Vec:
    def __matmul__(self, other):
        return sum(a * b for a, b in zip(self.data, other.data))
```

Verified output (CPython 3.13.5):

```text
--- @ dispatches to __matmul__; here, a dot product ---
  Vec([1,2,3]) @ Vec([4,5,6]): 32
  operator.matmul exists: True
```

Dispatch follows the standard binary-operator rules from Chapter 4: try `type(A).__matmul__(A, B)`; on
`NotImplemented`, try `type(B).__rmatmul__(B, A)`; a subclass's reflected method takes precedence. The
payoff is readability where it matters most, `result = (A @ B @ C) + (D @ E)` instead of chained
`.dot()` calls. NumPy implements `nb_matrix_multiply` on `ndarray` to call optimized BLAS/LAPACK
routines that *release the GIL* during the heavy C computation (Chapter 8's escape hatch, **Deep T**),
so `@` on large arrays is both readable and parallelizable. (This chapter's benchmark does not measure
NumPy, which is a third-party dependency and not installed on both verification interpreters; the BLAS
speedup is real but out of scope for a stdlib-only harness.)

---

## 11.4 Extended unpacking generalizations (PEP 448)

**Why this exists.** Before 3.5, `*` and `**` unpacking were limited to a single use in restricted
positions. **PEP 448** generalized them to multiple unpackings in collection literals and calls:

```text
--- PEP 448: multiple * and ** unpackings in literals and calls ---
  [*a, *b, 5]        : [1, 2, 3, 4, 5]
  {**d1, **d2, 'z':3}: {'x': 1, 'y': 2, 'z': 3}
  f(*a, *b)          : (1, 2, 3, 4)
--- collision rules differ by context ---
  dict literal, rightmost wins: {**o1, **o2}['k'] = 2
  call kwargs collision raises -> TypeError: __main__.<lambda>() got multiple values for keyword
```

The last two lines are the subtlety worth carrying: **collision rules differ by context.** In a `dict`
literal, a duplicate key is *silently overwritten* by the rightmost value, so `{**d1, **d2}` lets `d2`
win. In a function *call*, `f(**d1, **d2)` with overlapping keys raises `TypeError: got multiple values
for keyword argument`, because keyword arguments must be unambiguous. Do not assume the "right wins"
semantics of dict literals carry over to calls; they deliberately do not. The 3.5 implementation used
`BUILD_LIST_UNPACK`/`BUILD_MAP_UNPACK`; Python 3.9 replaced those with leaner incremental opcodes
(`LIST_EXTEND`, `DICT_UPDATE`, `DICT_MERGE`) that build the result in place. Dict merging via `|`/`|=`
(PEP 584) is Chapter 15.

---

## 11.5 Measurement: the cost of `await`

async/await earns its keep when a coroutine awaits real I/O and the loop overlaps the waits (Chapter 10
measured that payoff). But the syntax is easy to over-apply, marking functions `async` that never
actually await anything blocking, and that has a cost worth knowing.

**Methodology.** `code/ch011/bench_await_overhead.py`. A loop that awaits a trivial coroutine (one that
returns immediately, never suspending) versus the same loop calling a plain function, 100,000
iterations, `min` of five runs. The gap is the pure overhead of the coroutine-and-await machinery, with
no I/O to overlap. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64. Reproduced across runs.

| loop body | ratio |
|---|---|
| 100,000 plain calls | 1.00x |
| 100,000 awaits (nothing suspends) | **~2.2x** |

**Awaiting a coroutine that completes immediately costs about 2.2x a plain call.** For every `await`,
the interpreter builds a coroutine object, drives it with `SEND`, and unwinds it, whether or not there
was anything to wait for. That overhead is entirely worth paying when the `await` overlaps real I/O, as
Chapter 10 showed at 479x over sequential code. It is pure waste when a function is marked `async` for
consistency or style but never awaits anything that blocks: you have added coroutine machinery around
synchronous work.

The rule: **make code async where it awaits I/O, not for style.** An `async def` that never `await`s a
blocking operation is a plain function wearing a 2.2x tax. The async keyword is a claim that this
function yields to the loop; if it never does, it should not make the claim.

---

## 11.6 Edges and failure modes

**The un-awaited coroutine.** Calling `async def` without awaiting or scheduling it runs nothing and
emits `RuntimeWarning: coroutine ... was never awaited`. Always `await` it, pass it to
`asyncio.create_task`/`gather`, or `close()` it. This is the most common async bug and it is silent
except for the warning.

**Blocking the loop.** §11.5 and Chapter 10. A synchronous call inside a coroutine stalls every task.
`await` only non-blocking operations; offload blocking work with `asyncio.to_thread`.

**Async for style.** §11.5. Marking a function `async` that never awaits I/O adds ~2.2x overhead for
nothing. async is for I/O concurrency, not decoration.

**`@` has no inherent meaning.** §11.3. It does whatever the operands' `__matmul__` defines, and raises
`TypeError` for types that do not implement it. It shines with NumPy, not with lists.

**Unpacking copies.** `[*a, *b]` builds a new list (O(total length)); `{**d1, **d2}` a new dict.
Convenient, but not for a hot loop where you could `extend` in place.

**`**` keyword collisions in calls raise.** §11.4. Unlike dict literals, overlapping keys in a call are
a `TypeError`. Do not carry "right wins" intuition from literals into calls.

---

## 11.7 Connections

**Backward.** `await` generalizes the `yield from` delegation of Chapter 9 into a typed, awaitable-only
channel over the same suspendable frame from Chapter 5. The event loop, Futures, and Tasks that drive a
coroutine are Chapter 10. The `@` operator's dispatch rules are Chapter 4's binary-operator protocol,
and the GIL-releasing C computation NumPy runs under `@` is Chapter 8.

**Forward.** Event-loop internals, `TaskGroup`, cancellation, and structured concurrency are **Deep H**;
the free-threaded build is **Deep L**. NumPy, BLAS, and GIL-releasing numerics are **Deep T**. Dict
merge operators `|`/`|=` (PEP 584) are Chapter 15. f-strings and further 3.6 ergonomics are Chapter 12.

**Across books.** Native `async`/`await` is the syntax that makes Book II a good asynchronous client of
both siblings. A retrieval service in **Book III** awaits thousands of concurrent model calls as
coroutines on one loop; when one needs the C++ inference kernel in **Book I**, it `await`s a
`run_in_executor` call that releases the GIL and runs the kernel without blocking the loop. The
`__await__` protocol shown here is exactly what a custom awaitable wrapping a native future implements.
**Deep M** owns that boundary; `await` is how Book II schedules around it.

---

## 11.8 Exercises

**1. Trigger the safety net.** Take a coroutine and try each of: `for`-looping it, calling `next()` on
it, and calling it without awaiting. Record the exact error or warning for each, and explain, using
§11.1, which protocol each misuse assumed the coroutine had. Then show the 3.4-style equivalent would
have done something instead of erroring.

**2. Build an awaitable.** Implement a class whose `__await__` suspends twice (yields twice) before
returning a value, drive it with `asyncio.run`, and explain what each `yield` hands to the loop. Then
explain why `__await__` must return an *iterator* and what would break if it returned the value directly.

**3. Measure your own async tax.** Reproduce §11.5's benchmark, then add a version where the awaited
coroutine actually sleeps for a microsecond via `asyncio.sleep(0)`. Predict whether the ratio grows or
shrinks and why, then measure it to the standard of §11.5.

**4. Collide the keys.** Demonstrate both collision behaviors from §11.4: a dict literal where the right
key silently wins, and a function call where overlapping `**` keys raise. Then construct a realistic bug
where someone expected the call to behave like the literal, and describe how it would surface.

**5. The design question.** PEP 492 made a coroutine a distinct type rather than reusing the generator,
at the cost of a second, parallel protocol (`__await__`/`__aiter__`/`__aenter__` alongside
`__iter__`/`__enter__`). Argue whether the safety was worth the duplication. Your answer must address
the class of bug §11.1 eliminated, the cost of maintaining two protocols, and whether a language
starting today should unify them or keep them separate.

---

## 11.9 Summary and cross-references

- **PEP 492** makes `async def` produce a **distinct coroutine type** (`PyCoroObject`) with `__await__`
  and *no* iterator protocol, so misusing a coroutine as an iterator is a clean error. `await` compiles
  to `GET_AWAITABLE` plus a `SEND`/`YIELD_VALUE` loop, the 3.11+ successor to `YIELD_FROM`.
- **`async for`/`async with`** drive `__aiter__`/`__anext__`/`StopAsyncIteration` and
  `__aenter__`/`__aexit__`; async comprehensions arrived in 3.6 (PEP 530).
- **PEP 465** adds `@`/`@=` (`__matmul__`); the operator is meaning-free and dispatches to the type, the
  basis of NumPy's BLAS-backed, GIL-releasing matrix product.
- **PEP 448** generalizes `*`/`**` unpacking in literals and calls; dict literals let the right key win,
  call kwargs collisions raise.
- **Measured:** awaiting a coroutine that never suspends costs about **2.2x** a plain call. Make code
  async where it awaits I/O, not for style.

**Cross-references.** `yield from` and the suspendable frame → Chapter 9. The event loop, Futures, Tasks
→ Chapter 10. Structured concurrency → Deep H; the free-threaded build → Deep L. NumPy and GIL-releasing
numerics → Deep T. Dict merge `|`/`|=` → Chapter 15. f-strings → Chapter 12. The offload path to Book I
→ Deep M.
