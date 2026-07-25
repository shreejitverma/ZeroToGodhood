# Chapter 34: `functools`

Naive recursive Fibonacci is the textbook example of accidental exponential complexity: `fib(n)` calls
`fib(n-1)` and `fib(n-2)`, each of which recomputes the same subproblems, so `fib(28)` makes over a
million calls to compute 29 distinct values. One decorator fixes it. Add `@functools.cache` above the
function, and `fib(28)` goes from **25 milliseconds** to **20 nanoseconds** per call, a factor of over a
million, because the decorator memoizes each result so every `fib(k)` is computed exactly once. That is
not a speedup in the usual sense; it is a *change of complexity class*, from O(2^n) to O(n), achieved
without touching the algorithm.

That is the headline of `functools`, the module of higher-order helpers that operate *on* functions:
memoization (`cache`, `lru_cache`), partial application (`partial`), reduction (`reduce`), type-based
dispatch (`singledispatch`), and comparison completion (`total_ordering`). Chapter 5 covered
`functools.wraps` and `lru_cache` in the decorator context, and Chapter 13 covered `cached_property`;
this chapter, part of **Deep Q**, is the working reference for the rest and for the memoization that
turns algorithms inside out.

## Section index

- **34.1** The higher-order helpers
- **34.2** Memoization: `cache` and `lru_cache`
- **34.3** Measurement: caching as a complexity change
- **34.4** Edges and failure modes
- **34.5** Connections
- **34.6** Exercises
- **34.7** Summary and cross-references

Listings live under `code/ch034/` and are re-executed by `make verify` on both interpreters.

---

## 34.1 The higher-order helpers

`functools` transforms and combines functions:

```python
# code/ch034/l01_functools.py
```

Verified output (CPython 3.13.5):

```text
--- partial: bind some arguments, get a new callable ---
  partial(add3, 10, 20)(5): 35
  captured args           : (10, 20)
--- reduce: fold a binary function over an iterable ---
  reduce(a*b, 1..5) = 5! : 120
--- singledispatch: one function, type-based implementations ---
  describe(5)      : int: 5
  describe([1,2,3]): list of 3
  describe('hi')   : generic: 'hi' (falls back to generic)
--- total_ordering: define __eq__ and __lt__, get the other four ---
  Version(3) >= Version(2): True
  Version(1) >  Version(2): False
  (>=, >, <=, != were all synthesized from __eq__ and __lt__)
```

**`partial`** binds some of a function's arguments, returning a new callable with a smaller signature,
the cleanest way to specialize a general function (a callback that needs fixed configuration, a `sort`
key with a bound parameter). **`reduce`** folds a binary function over an iterable to a single value
(here `1*2*3*4*5`); it is the general form of `sum`/`math.prod`, used when no builtin fits. **`singledispatch`**
turns one function into a generic that picks an implementation by the *type* of its first argument, the
Pythonic answer to type-based dispatch without a chain of `isinstance` checks, and it falls back to the
base implementation for unregistered types. **`total_ordering`** synthesizes the four remaining
comparison methods from `__eq__` and `__lt__`, so a class defines two and gets all six, removing
boilerplate and the risk of an inconsistent comparison.

---

## 34.2 Memoization: `cache` and `lru_cache`

`functools.cache` (3.9) and `lru_cache` (the bounded version) wrap a function so a repeated call with the
same arguments returns a stored result instead of recomputing. `cache` is unbounded; `lru_cache(maxsize=N)`
keeps the N most-recently-used results and evicts the rest. Both require the arguments to be hashable
(they key the cache on them), and both expose `cache_info()` for hits, misses, and size.

Memoization's value depends entirely on the function. For a function called repeatedly with a *bounded,
repeated* set of arguments, it converts recomputation into a lookup. For the recursive Fibonacci of the
chapter opening, it does something stronger: because the recursion *itself* hits the cache, each distinct
subproblem is computed once, collapsing the exponential recomputation into linear work. That is the
distinction §34.3 measures, memoization is sometimes a constant-factor speedup and sometimes an
algorithmic transformation, and the recursive case is the latter.

---

## 34.3 Measurement: caching as a complexity change

**Methodology.** `code/ch034/bench_cache.py`. Recursive `fib(28)` computed with `@functools.cache` (warmed
once) versus naive recursion. `min` per call; note the per-call time is what is compared, so the two
cases use different batch counts but the reported nanoseconds are per call. CPython 3.13.5, Apple M3 Pro,
macOS 27.0, arm64.

| `fib(28)` | per call |
|---|---|
| cached (warm) | **20 ns** |
| uncached (naive recursion) | **25,000,000 ns** (25 ms) |

The cached call is a single dictionary lookup, O(1); the uncached call makes over a million recursive
calls, O(2^n). The ratio is over a *million*, and it is not a constant factor, it grows with `n`, because
the two functions have different complexity classes. `@cache` turned an exponential algorithm into a
linear one by ensuring each `fib(k)` is computed once and thereafter looked up. This is the memoized
dynamic-programming solution, expressed as the naive recursive function plus a one-line decorator.

The honest scope, because the number is seductive: this transformation happens only when the *repeated
subproblems* are the cost, as in recursion over overlapping subproblems. For a function called once per
distinct argument, `@cache` adds overhead (the cache bookkeeping) for no benefit and can leak memory,
because an unbounded `cache` grows with every distinct argument. Use `cache`/`lru_cache` for pure
functions with a bounded, repeated argument space; bound it with `lru_cache(maxsize=...)` when the
argument space is large; and never cache a function with side effects (the side effect happens only on a
miss) or one whose result can change (the cache serves stale values).

---

## 34.4 Edges and failure modes

**Caching an unbounded argument space.** §34.3. An unbounded `@cache` grows with every distinct argument,
a memory leak. Use `lru_cache(maxsize=N)` to bound it.

**Caching a side-effecting or time-varying function.** §34.3. The side effect runs only on a cache miss,
and a time-varying result is frozen at first computation. Cache only pure, stable functions.

**Unhashable arguments.** `cache`/`lru_cache` key on the arguments, which must be hashable; a `list` or
`dict` argument raises `TypeError`. Convert to a hashable form (a tuple) or do not cache.

**`reduce` where a builtin fits.** `reduce(operator.add, xs)` is `sum(xs)`, and slower and less readable.
Use `reduce` only when no builtin (`sum`, `math.prod`, `min`, `max`, `any`, `all`) expresses the fold.

**`singledispatch` on the wrong argument.** It dispatches on the *first* argument's type only. For
methods (dispatch on `self` is useless) use `singledispatchmethod` and dispatch on the second argument.

**`total_ordering` inconsistency.** It assumes `__eq__` and `__lt__` are consistent; if they disagree, the
synthesized methods are wrong. It also adds a small per-comparison cost versus hand-writing all six.

---

## 34.5 Connections

**Backward.** `functools.wraps` (preserving a wrapped function's identity) and `lru_cache` in the
decorator context are Chapter 5, whose measurement showed a warm `lru_cache` hit is not free.
`cached_property`, the per-instance memoization, is Chapter 13 (measured at 462x there). The descriptor
protocol behind `cached_property` and `partial` is Chapter 4.

**Forward.** `itertools`, the iterator half of the functional toolkit, is Chapter 33. The hashing that
keys the cache is **Deep P**. Dynamic programming and algorithmic complexity in depth are **Deep K**.

**Across books.** `@lru_cache` is how Book II caches expensive deterministic computations at the seams: a
**Book III** retrieval pipeline caches embedding lookups for repeated queries with `lru_cache(maxsize=...)`,
bounding memory while eliminating recomputation, and `singledispatch` cleanly handles the several message
types that cross the **Book III** boundary without an `isinstance` chain. The bounded, pure-function
discipline of §34.3 is what makes those caches safe at a service boundary. **Deep U** owns the seam.

---

## 34.6 Exercises

**1. Reproduce the complexity change.** Measure cached and uncached recursive `fib` at several `n` to the
standard of §34.3, and plot how the *ratio* grows with `n`. Explain why it grows (rather than being a
constant factor), in terms of the two complexity classes.

**2. Leak with `@cache`.** Write a function cached with unbounded `@cache` and call it with a growing set
of distinct arguments; observe the cache (via `cache_info()`) and memory grow without bound. Fix it with
`lru_cache(maxsize=...)` and explain the eviction.

**3. Dispatch by type.** Build a `singledispatch` function that formats several types differently, and add
a registration for a type after the fact. Explain why this is cleaner than an `isinstance` chain and what
it dispatches on.

**4. Complete an ordering.** Write a class with `__eq__` and `__lt__` and `@total_ordering`, and confirm
all six comparisons work. Then make `__eq__` and `__lt__` inconsistent and show a synthesized comparison
gives a wrong answer. Explain the assumption `total_ordering` relies on.

**5. The design question.** `@cache` can change an algorithm's complexity class with one line, which is
powerful and dangerous. Argue when memoization is the right tool versus rewriting the algorithm
iteratively. Your answer must address the memory cost of the cache, the purity requirement, and why the
recursive-plus-cache form is sometimes clearer than the hand-written dynamic-programming table and
sometimes worse.

---

## 34.7 Summary and cross-references

- **`functools`** provides higher-order helpers: **`partial`** (bind arguments), **`reduce`** (fold),
  **`singledispatch`** (type-based dispatch), **`total_ordering`** (synthesize comparisons from `__eq__`
  and `__lt__`), and memoization.
- **`cache`/`lru_cache`** memoize a function; for recursion over overlapping subproblems this is an
  **algorithmic transformation**, not a constant-factor speedup.
- **Measured:** cached recursive `fib(28)` is **20 ns** per call versus **25 ms** uncached, over a
  **million-fold** difference, because `@cache` turns O(2^n) into O(n). The ratio grows with `n`, the
  signature of a complexity-class change.
- **Edges:** cache only pure, stable functions with hashable, bounded, repeated arguments; use
  `lru_cache(maxsize)` to bound memory; never cache side effects.

**Cross-references.** `wraps` and `lru_cache` in decorators → Chapter 5. `cached_property` → Chapter 13.
Descriptors behind `partial`/`cached_property` → Chapter 4. `itertools` → Chapter 33. Hashing → Deep P.
Complexity and dynamic programming → Deep K. The caching seam → Deep U.
