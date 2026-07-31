# Chapter 245: Lru_cache

## The constraint

Memoization - remembering a pure function's results so you never recompute them - is one of the oldest optimizations there is.
If `f(5)` returned `120` last time and `f` is pure, `f(5)` will return `120` again, so storing the answer turns a repeated computation into a lookup.
And for twenty years, every Python programmer who needed it wrote the same small machine by hand:

```python
_cache = {}
def f(n):
    if n in _cache:
        return _cache[n]
    result = ... expensive ...
    _cache[n] = result
    return result
```

It works, and it is easy to get subtly wrong.
The hand-rolled cache grows without bound, so a long-running process leaks memory.
It has no thread safety.
It clutters the function with caching logic that has nothing to do with what the function computes.
And every codebase reimplements it slightly differently.

The constraint Python 3.2 (2011) answered: **make memoization a decorator - one line above a pure function - with a bounded eviction policy so it is safe to leave running, and observable statistics so you can tell whether it helps.**

This is a two-track chapter.
The cost model - *when* caching is worth it, how to measure the hit rate, when the memory trade is justified - belongs to Deep Volume K (performance engineering).
The hashability rule the cache depends on belongs to Deep Volume A.
What this chapter owns is the release: the day applying a bounded, instrumented cache became a single decorator.

## What shipped

`functools.lru_cache` wraps a function so its results are cached, keyed on the arguments, with a Least-Recently-Used eviction policy bounded by `maxsize` (or unbounded with `maxsize=None`).
It exposes `cache_info()` for statistics.
Listing 245.1 shows it turning exponential recursion linear, caching plain calls, evicting under a bound, and enforcing its requirements, on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- @lru_cache turns exponential recursion into linear ---
  fib(30) = 832040
  actual fib() bodies executed : 31  (once per distinct n)
  naive recursive fib(30) makes over 2.7 MILLION calls (each value
  recomputed exponentially). with @lru_cache each fib(n) runs ONCE
  and is reused, so 31 distinct computations cover the whole tree
--- the cache is observable via cache_info() ---
  fib.cache_info() : hits=28, misses=31, currsize=31
  misses are the real computations (one per distinct n); hits are
  the reuses. the decorator exposes the cache stats so you can SEE
  whether it is helping - measurement, not faith (Deep K)
--- a plain call is cached too, not just recursion ---
  called slow_square(7) five times
  actual computations : 1  (only the first)
  repeated calls with the same arguments return the stored result.
  the function runs once; the other four are cache hits
--- maxsize bounds memory: LRU eviction ---
  maxsize=2 after ident(1),(2),(3) : currsize=2
  ident(1) again -> misses rose to 4 (1 was evicted)
  with maxsize=2 the cache holds only the 2 most-recently-used keys;
  the least-recently-used is evicted. that bound is what makes it
  safe on a hot path - memory cannot grow without limit (the L-R-U)
--- the requirement: arguments must be hashable, function pure ---
  fib([1,2]) -> TypeError: unhashable type: 'list'
  the cache keys on the arguments, so they must be HASHABLE (Deep A)
  - a list fails. and the function must be PURE (same args -> same
  result, no side effects), or the cache returns stale answers
--- the constraint answered ---
  memoization was a hand-rolled dict-plus-guard, easy to get wrong
  and repeated everywhere. @lru_cache (3.2) made it one decorator
  with bounded LRU eviction and observable stats. Deep K tells you
  WHEN a cache helps; this release made SAYING so a single line
```

## Why each part answers the constraint

**One decorator collapses an exponential.**
The first block is the dramatic case.
Naive recursive `fib(30)` makes over 2.7 million calls, because each value is recomputed exponentially through the two-way recursion.
With `@lru_cache`, each `fib(n)` executes exactly once and is reused thereafter - the instrumented counter confirms only 31 actual function bodies ran, one per distinct `n`.
The exponential tree collapses to linear work, and the change is a single line above the function.

**The cache is observable.**
The second block reads `cache_info()`: `hits=28`, `misses=31`, `currsize=31`.
Misses are the real computations (one per distinct argument); hits are the reuses.
This matters because caching is a performance claim, and performance claims should be measured, not assumed (the recurring theme of Deep Volume K).
The decorator hands you the numbers to confirm the cache is actually earning its memory - a good hit rate means it helps, a poor one means the arguments rarely repeat and the cache is dead weight.

**Plain calls cache too.**
The third block shows memoization is not special to recursion: calling `slow_square(7)` five times runs the body once and returns the stored result the other four times.
Any pure function called repeatedly with repeating arguments benefits - parsing the same configuration, resolving the same lookup, computing the same expensive transform.

**The bound is what makes it safe.**
The fourth block shows the LRU eviction that the hand-rolled dict lacked.
With `maxsize=2`, after caching three distinct keys the cache holds only two - the least-recently-used was evicted - and calling the evicted key again registers as a fresh miss.
This bound is the crucial safety property: on a hot path with many distinct arguments, an unbounded cache is a memory leak, while a bounded LRU cache keeps only the most-recently-useful entries and can run forever.
The "LRU" in the name is this policy.

**The requirements are real.**
The fifth block shows the two conditions.
The cache keys on the arguments, so they must be *hashable* - `fib([1, 2])` raises `TypeError` because a list is unhashable (Deep Volume A's rule).
And the function must be *pure*: same arguments must always produce the same result with no side effects, or the cache will happily return stale, wrong answers.
`lru_cache` is a sharp tool precisely because it trusts you on purity - it cannot check it.

## The two-track note

The performance reasoning - how to decide a function is worth caching, how to read a hit rate, when the memory cost outweighs the recomputation saved, how caching interacts with the broader cost model - is Deep Volume K's to develop.
The hashability requirement is Deep Volume A's.
What the timeline records is the release act: in 3.2, `functools.lru_cache` turned the hand-rolled, leak-prone, uninstrumented memoization pattern into a single decorator with a bounded eviction policy and observable statistics.
The modern consequence, verified above, is that memoization is now a one-line annotation - later joined by the simpler `@functools.cache` (3.9) for the unbounded case - and the cache's behavior is inspectable rather than a matter of faith.

## Where this lands

`lru_cache` is a model of what good standard-library consolidation looks like: it took a pattern everyone reimplemented, fixed the parts everyone got wrong (unbounded growth, no observability), and reduced it to a decorator.
Reach for it on any pure function that is called repeatedly with repeating, hashable arguments - and confirm with `cache_info()` that the hit rate justifies the memory.
Do not reach for it on impure functions, or on functions whose arguments rarely repeat, where it only adds overhead.
Deep Volume K tells you when a cache is worth it; this chapter is the record of the release that made applying one a single line.
