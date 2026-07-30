"""Listing 171.1 - what a cache changes, counted: the exponent, the ledger, the bound.

Caching is the one optimisation in this volume that changes a cost model rather than a
constant: a function whose call tree revisits the same arguments stops paying for the
revisits, which can move the exponent itself. It is also the one optimisation whose
failure modes are bookkeeping rather than speed, so everything here is COUNTED with
call counters and cache_info() rather than timed. The timings are in bench_caching.py.

Four facts, deterministic on any interpreter:

  the same recursive function, counted with and without a cache: exponential to linear
  cache_info() as the ledger every caching decision should be read from
  the break-even, as arithmetic: what a hit rate is worth at a given cost ratio
  eviction's worst case: one entry over the bound can take the hit rate to zero
"""

import functools


def counted(fn):
    """Count calls through the wrapper, recursion included."""
    def wrapper(*args):
        wrapper.calls += 1
        return fn(*args)
    wrapper.calls = 0
    wrapper.reset = lambda: setattr(wrapper, "calls", 0)
    return wrapper


@counted
def fib_naive(n):
    return n if n < 2 else fib_naive(n - 1) + fib_naive(n - 2)


computations = 0


@functools.cache
def fib_cached(n):
    global computations
    computations += 1
    return n if n < 2 else fib_cached(n - 1) + fib_cached(n - 2)


def main() -> None:
    global computations

    print("--- the same function, counted, with and without a cache ---")
    print(f"  {'n':>4} {'naive calls':>13} {'cached computations':>21}")
    previous = None
    for n in (18, 23, 28):
        fib_naive.reset()
        fib_naive(n)
        fib_cached.cache_clear()
        computations = 0
        fib_cached(n)
        growth = f"   x{fib_naive.calls / previous:.1f} for +5" if previous else ""
        previous = fib_naive.calls
        print(f"  {n:>4} {fib_naive.calls:>13,} {computations:>21,}{growth}")
    print("  each +5 multiplies the naive count by ~11; the cached count is n + 1.")
    print("  the cache did not shave the constant, it CHANGED THE EXPONENT")

    print("--- cache_info: the ledger a caching decision is read from ---")
    fib_cached.cache_clear()
    computations = 0
    fib_cached(28)
    print(f"  after fib(28)      : {fib_cached.cache_info()}")
    fib_cached(33)
    print(f"  after fib(33) next : {fib_cached.cache_info()}")
    print("  the second call cost 5 new computations, not 33: the cache is doing")
    print("  cross-call work, which no other optimisation in this volume does")

    print("--- the break-even, as arithmetic ---")
    t_miss, t_hit = 1000, 50   # ns; a 20x cost ratio, close to bench 171.1b's measured one
    print(f"  model: compute costs {t_miss} ns, a hit costs {t_hit} ns")
    print(f"  {'hit rate':>9} {'effective ns/call':>18} {'speedup':>9}")
    for h in (0.0, 0.5, 0.9, 0.99):
        effective = h * t_hit + (1 - h) * t_miss
        print(f"  {h:>9.0%} {effective:>18.0f} {t_miss / effective:>8.1f}x")
    print("  the speedup is capped by the hit rate, not by the cost ratio: at 50%")
    print("  hits no cache can beat 2x, however expensive the miss")

    print("--- eviction: one entry over the bound, counted ---")

    @functools.lru_cache(maxsize=8)
    def fits(key):
        return key

    @functools.lru_cache(maxsize=8)
    def cycles(key):
        return key

    for _ in range(10):                 # 10 rounds over 8 keys: fits in the bound
        for key in range(8):
            fits(key)
    for _ in range(10):                 # 10 rounds over 9 keys: one over the bound
        for key in range(9):
            cycles(key)
    print(f"  8 keys, maxsize=8 : {fits.cache_info()}")
    print(f"  9 keys, maxsize=8 : {cycles.cache_info()}")
    print("  one extra key took the hit rate from 90% to ZERO: a cyclic scan is LRU's")
    print("  worst case, because the entry evicted is always the next one needed")

    print("--- the rule ---")
    print("  a cache buys repeated work back at the price of memory and staleness;")
    print("  read the ledger before believing in one, and bound it or own the growth")


if __name__ == "__main__":
    main()
