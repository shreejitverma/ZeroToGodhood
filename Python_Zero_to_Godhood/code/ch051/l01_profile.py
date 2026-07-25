"""Listing 51.1 - cProfile finds WHERE time goes; it does not measure HOW FAST.

cProfile is a DETERMINISTIC profiler: it hooks every function call and return and
records counts and times per function. That makes it excellent at attributing
time to functions (finding the hotspot) but poor at absolute timing, the per-call
hook adds overhead (the benchmark measures ~4x) and over-weights call-heavy code.
So the workflow is: cProfile to find the hot function, then a focused benchmark
(timeit / the bench harness) to measure and improve it.

This listing prints the DETERMINISTIC facts cProfile gives (call counts and the
call structure), not the timing numbers, which vary run to run.
"""

import cProfile
import pstats


def leaf(n):
    return sum(i * i for i in range(n))


def middle(n):
    return leaf(n) + leaf(n)         # calls leaf twice


def work():
    total = 0
    for _ in range(1000):
        total += middle(50)          # -> 1000 middle, 2000 leaf
    return total


def main() -> None:
    pr = cProfile.Profile()
    pr.enable()
    work()
    pr.disable()

    stats = pstats.Stats(pr)
    # ncalls per function is deterministic (unlike the times); build a name->calls map
    calls = {}
    for (filename, lineno, funcname), (cc, nc, tt, ct, callers) in stats.stats.items():
        if funcname in {"work", "middle", "leaf"}:
            calls[funcname] = nc

    print("--- cProfile attributes calls to functions (counts are deterministic) ---")
    print(f"  work called   : {calls['work']:>5} time(s)")
    print(f"  middle called : {calls['middle']:>5} time(s)  (1 per loop iteration)")
    print(f"  leaf called   : {calls['leaf']:>5} time(s)  (2 per middle call)")

    print("--- the hotspot is the most-called leaf function ---")
    hottest = max(calls, key=calls.get)
    print(f"  most-called function : {hottest} ({calls[hottest]} calls)")
    print(f"  this is where to focus a benchmark, not to trust cProfile's ms")


if __name__ == "__main__":
    main()
