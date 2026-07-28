"""Benchmark 167.1 - the profiler does not just slow the program, it re-ranks it.

Chapter 51 measured how much cProfile slows a call-heavy workload. This measures the
consequence that actually costs you an afternoon: because the per-call hook is charged to
whichever function made the calls, a deterministic profiler systematically OVER-WEIGHTS
call-heavy code relative to compute-heavy code, and can therefore point at the wrong
function.

The experiment is a workload with two halves, deliberately tuned to cost about the same
when nothing is watching:

  call-heavy     200,000 calls to a trivial function
  compute-heavy  one call running an equivalent amount of arithmetic in a loop

First each half is timed on its own, with no profiler, to establish the true split.
Then both run under cProfile and the split is recomputed from tottime. If the profiler
were a neutral observer the two splits would agree. They do not.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import cProfile
import pstats
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 200_000
REPEAT = 9


def tiny(x):
    return x + 1


def call_heavy(n):
    total = 0
    for _ in range(n):
        total = tiny(total)
    return total


def compute_heavy(n):
    total = 0
    for i in range(n):
        total += i * i
    return total


def best(fn, n, repeat=REPEAT):
    lowest = float("inf")
    for _ in range(repeat):
        start = time.perf_counter()
        fn(n)
        lowest = min(lowest, time.perf_counter() - start)
    return lowest


def profiled_tottime():
    """tottime per function, with the callee's own time attributed to the callee."""
    profiler = cProfile.Profile()
    profiler.enable()
    call_heavy(N)
    compute_heavy(N)
    profiler.disable()
    stats = pstats.Stats(profiler).stats
    tot = {name: entry[2] for (_, _, name), entry in stats.items()}
    # tiny's time belongs to the call-heavy half: it is only reached from there.
    return tot.get("call_heavy", 0.0) + tot.get("tiny", 0.0), tot.get("compute_heavy", 0.0)


def main():
    print(f"=== 167.1  the same workload, weighed twice ({N:,} units each half) ===")
    print(provenance())
    print(f"method      : min of {REPEAT} runs unprofiled; one cProfile run for tottime")
    print()

    true_calls = best(call_heavy, N)
    true_compute = best(compute_heavy, N)
    true_total = true_calls + true_compute

    prof_calls, prof_compute = profiled_tottime()
    prof_total = prof_calls + prof_compute

    print(f"  {'half':<16} {'unprofiled ms':>14} {'share':>8} {'profiled ms':>12} {'share':>8}")
    print("  " + "-" * 62)
    print(f"  {'call-heavy':<16} {true_calls * 1e3:14.1f} {true_calls / true_total:7.0%}"
          f" {prof_calls * 1e3:12.1f} {prof_calls / prof_total:7.0%}")
    print(f"  {'compute-heavy':<16} {true_compute * 1e3:14.1f} {true_compute / true_total:7.0%}"
          f" {prof_compute * 1e3:12.1f} {prof_compute / prof_total:7.0%}")

    shift = (prof_calls / prof_total) - (true_calls / true_total)
    print()
    print(f"  the profiler moved the call-heavy half's apparent share by "
          f"{shift:+.0%}")
    print(f"  and it is the larger half under the profiler : "
          f"{prof_calls > prof_compute}")
    print(f"  while the two are close without one          : "
          f"{abs(true_calls - true_compute) / true_total < 0.15}")
    if (prof_calls > prof_compute) != (true_calls > true_compute):
        print("  the profiler named the half that is actually the SMALLER one")

    print()
    print("Reading this. cProfile hooks every call and every return, so the cost of")
    print("observing is proportional to how many calls a piece of code makes. That cost")
    print("is charged to the code being observed, which means a deterministic profile")
    print("does not merely run slower - it runs slower UNEVENLY, in proportion to call")
    print("frequency. Two halves that cost the same when nothing is watching come out")
    print("lopsided under the profiler, and if the true split had been the other way")
    print("round by a small margin, the profile would have named the wrong function.")
    print()
    print("The working rule that follows: use a deterministic profiler to find the")
    print("SUBTREE, never to compare two candidates that are close. Once you have a")
    print("candidate, measure it with a focused benchmark that has no per-call hook, or")
    print("with a sampling profiler whose cost does not scale with call count.")


if __name__ == "__main__":
    main()
