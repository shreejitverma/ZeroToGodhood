"""Benchmark 171.1 - what a cache costs, what it pays, and when it loses.

Four measurements, one argument.

  171.1a  a cache hit against the recomputation it replaces, for a genuinely
          expensive pure function. This is the headline everyone quotes.

  171.1b  the same comparison for a TRIVIAL function, where the cache loses:
          a hit still pays a call, key construction, a hash, and a dict probe,
          for cheap work that machinery costs more than the work.

  171.1c  a fixed workload at controlled hit rates, including 0%. A cache is
          not an optimisation of a function, it is an optimisation of an access
          pattern, and at a 0% hit rate it is pure overhead - measured, not
          argued.

  171.1d  the memory side of the trade, with tracemalloc: bytes per cached
          entry, which is the price §171.1a's speedup is paid in.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import functools
import sys
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, provenance, report  # noqa: E402

CALLS = 10_000


def main():
    EXPENSIVE_SETUP = """
import functools

def curve(n):
    return sum(i * i for i in range(n))

cached_curve = functools.cache(curve)
cached_curve(1_000)   # warm: the measured calls are all hits
"""
    expensive = [
        measure("recompute curve(1000)", "curve(1_000)",
                EXPENSIVE_SETUP, repeat=7, number=2_000),
        measure("cache hit", "cached_curve(1_000)",
                EXPENSIVE_SETUP, repeat=7, number=2_000),
    ]
    report("171.1a  an expensive pure function: recompute vs cache hit",
           expensive, baseline="recompute curve(1000)")

    print()
    TRIVIAL_SETUP = """
import functools

def double(x):
    return x + x

cached_double = functools.cache(double)
cached_double(21)     # warm
"""
    trivial = [
        measure("double(21) direct", "double(21)", TRIVIAL_SETUP),
        measure("double(21) via cache hit", "cached_double(21)", TRIVIAL_SETUP),
    ]
    report("171.1b  a trivial function: the cache machinery against the work",
           trivial, baseline="double(21) direct")

    print()
    SWEEP_SETUP = f"""
import functools

CALLS = {CALLS}

def curve(n):
    return sum(i * i for i in range(200)) + n - n

cached_curve = functools.cache(curve)

# One key list per hit rate: repeating each key k times gives a (k-1)/k hit
# rate on a cleared cache, deterministically.
KEYS = {{
    "0%":  [i for i in range(CALLS)],
    "50%": [i // 2 for i in range(CALLS)],
    "90%": [i // 10 for i in range(CALLS)],
    "99%": [i // 100 for i in range(CALLS)],
}}

def run_cached(keys):
    cached_curve.cache_clear()
    for key in keys:
        cached_curve(key)

def run_direct(keys):
    for key in keys:
        curve(key)
"""
    sweep = [measure("no cache", "run_direct(KEYS['0%'])",
                     SWEEP_SETUP, repeat=5, number=3)]
    for rate in ("0%", "50%", "90%", "99%"):
        sweep.append(measure(f"cached, {rate} hits", f"run_cached(KEYS['{rate}'])",
                             SWEEP_SETUP, repeat=5, number=3))
    report(f"171.1c  the same {CALLS:,}-call workload at controlled hit rates",
           sweep, baseline="no cache")

    print()
    print("=== 171.1d  the memory side of the trade, measured by tracemalloc ===")

    def curve(n):
        return sum(i * i for i in range(200)) + n - n

    cached_curve = functools.cache(curve)
    entries = 100_000
    tracemalloc.start()
    tracemalloc.reset_peak()
    for key in range(entries):
        cached_curve(key)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"  {entries:,} cached entries : {peak:,} bytes at peak")
    print(f"  per entry           : {peak / entries:.0f} bytes"
          f"  (dict entry + key + result; a bounded cache adds per-entry links)")

    print()
    print("Reading this. The headline table is real: when the work is expensive and")
    print("repeated, a hit replaces microseconds of compute with tens of nanoseconds")
    print("of dict probe, and the ratio is whatever the work costs divided by that")
    print("floor. The trivial table is the same machinery with nothing to amortise")
    print("it: a hit costs a call, key construction, a hash, and a probe, which is more")
    print("than doubling an integer costs, so the cache makes that function slower.")
    print()
    print("The sweep is the chapter's argument. The function never changes; only the")
    print("access pattern does. At a 0% hit rate the cache is measurably worse than")
    print("no cache - every call pays the probe AND the compute AND the store - and")
    print("the win only appears as the hit rate climbs. A cache is a bet on the")
    print("access pattern, and 171.1d is the stake: real bytes per entry, held for")
    print("as long as the cache lives, win or lose.")


if __name__ == "__main__":
    main()
