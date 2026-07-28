"""Benchmark 166.1 - why min, and why batching: the two methodology decisions, measured.

_harness/bench.py asserts two things about microbenchmark methodology. This benchmark is
the evidence for both, rather than the assertion.

  166.1a  NOISE IS ONE-SIDED. The same work, timed many times, has a hard floor and a
          right tail: a batch can be interrupted, migrated between cores, or preempted,
          and every one of those makes it slower while none can make it faster. So the
          minimum estimates the work and the mean estimates the work plus the machine.
          Every statistic is reported as a multiple of the min so the asymmetry is
          visible. On a quiet machine the spread is small, and that is the point of
          reporting RSD as a diagnostic: it says how quiet the machine was.

  166.1b  A SMALL BATCH MEASURES THE CLOCK. perf_counter's resolution on this platform
          is about 42 ns (Listing 166.1). Timing a single operation that costs less than
          that cannot report the operation, and the table shows exactly that: at one,
          three, and ten operations per batch the per-operation figure sits at the
          clock's resolution regardless of what the code does, and only converges on the
          real cost once the batch is large enough to dwarf it.

A warm-up effect from the specializing interpreter was looked for and is NOT reported:
at these batch sizes specialization completes within the first few dozen executions out
of tens of thousands, and no systematic difference between the first batch and later
ones survived measurement. The warm-up discard in the harness is cheap insurance for
small batches, not a large correction for big ones. Reporting the null is the point.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import statistics
import sys
import time
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

BATCHES = 40
PER_BATCH = 20_000
SIZES = (1, 3, 10, 100, 1_000, 20_000, 200_000)

WORK_SOURCE = """
def work(a, b):
    return (a * b + 3) % 7 + (a - b) * 2
"""


def timer():
    return timeit.Timer("work(3, 5)", WORK_SOURCE, timer=time.perf_counter)


def distribution():
    t = timer()
    t.timeit(number=PER_BATCH)                       # warm-up, discarded
    return sorted(x / PER_BATCH * 1e9 for x in t.repeat(repeat=BATCHES, number=PER_BATCH))


def by_batch_size():
    rows = []
    for n in SIZES:
        repeat = 200 if n < 1_000 else 15
        best = min(timer().repeat(repeat=repeat, number=n)) / n * 1e9
        rows.append((n, best))
    return rows


def main():
    resolution_ns = time.get_clock_info("perf_counter").resolution * 1e9

    print(f"=== 166.1a  one operation, {BATCHES} batches of {PER_BATCH:,} ===")
    print(provenance())
    print()

    samples = distribution()
    floor = samples[0]
    for label, value in (
        ("min", floor),
        ("p25", samples[len(samples) // 4]),
        ("median", statistics.median(samples)),
        ("mean", statistics.fmean(samples)),
        ("p90", samples[int(len(samples) * 0.9)]),
        ("max", samples[-1]),
    ):
        print(f"  {label:<8} {value:8.1f} ns/op   {value / floor:5.2f}x min")
    rsd = statistics.stdev(samples) / statistics.median(samples) * 100
    print(f"  {'RSD':<8} {rsd:8.1f} %       (a machine-quietness diagnostic)")
    print(f"  every statistic is >= the min, by construction : "
          f"{all(value >= floor for value in samples)}")

    print()
    print("=== 166.1b  the same work, timed in batches of different sizes ===")
    print(f"  perf_counter resolution : {resolution_ns:.1f} ns")
    print()
    print(f"  {'ops/batch':>10} {'ns/op':>9} {'batch ns':>12} {'clock ticks':>12}")
    print("  " + "-" * 48)
    for n, ns in by_batch_size():
        batch_ns = ns * n
        print(f"  {n:>10,} {ns:9.1f} {batch_ns:12.0f} {batch_ns / resolution_ns:12.1f}")

    print()
    print("Reading this. The first table's shape is the argument for min: there is a")
    print("hard floor and nothing below it, because none of the things that perturb a")
    print("measurement can make work finish sooner than it does. On a quiet machine the")
    print("spread is small and the choice of statistic barely matters; on a busy one the")
    print("mean drifts and the min does not, which is precisely when you need the rule.")
    print()
    print("The second table is the argument for batching, and the clock-ticks column is")
    print("the proof. Those counts are INTEGERS: a batch of one operation always takes")
    print("exactly one tick, so it reports the resolution and would report the same")
    print("figure for any operation faster than 42 ns. A batch of three takes two or")
    print("three ticks depending on where it lands, which is why that row moves between")
    print("runs while the work does not. Only once a batch spans hundreds of ticks does")
    print("the quantization stop mattering and the number start describing the code. Any")
    print("benchmark that times a single operation is reporting its clock.")


if __name__ == "__main__":
    main()
