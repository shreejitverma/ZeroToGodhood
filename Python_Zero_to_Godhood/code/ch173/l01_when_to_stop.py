"""Listing 173.1 - when to stop: Amdahl's ceiling, the interpreter's floor, the procedure.

Deep K closes on the only question left: when is the next optimisation not worth
making, and when is the right one leaving pure Python? Both halves are arithmetic
on numbers this volume has already measured, so this listing computes rather than
asserts them. The timings behind the escape itself are in bench_the_escape.py.

Four facts, deterministic on any interpreter:

  Amdahl: the hot path's SHARE of runtime caps what optimising it can ever buy
  the floor: Chapter 78's per-instruction constant prices a loop before it does anything
  the escape changes the executor, not the answer - checked, not promised
  the volume, restated as the decision procedure it has been building
"""

import math


def amdahl(share, speedup):
    """Whole-program speedup when `share` of runtime is made `speedup`x faster."""
    return 1.0 / ((1.0 - share) + share / speedup)


def main() -> None:
    print("--- Amdahl: what optimising the hot path can ever buy ---")
    print(f"  {'hot-path share':>15} {'made 10x faster':>17} {'made infinite':>15}")
    for share in (0.50, 0.90, 0.99):
        print(f"  {share:>15.0%} {amdahl(share, 10):>16.1f}x"
              f" {1 / (1 - share):>14.0f}x")
    print("  the profile's share (Chapter 86) caps the win: past a point the hot")
    print("  path is no longer the program, and the next factor must come from")
    print("  somewhere else - or from stopping")

    print("--- the interpreter's floor, priced with Chapter 78's constant ---")
    NS_PER_INSTRUCTION = 3.4     # Chapter 78, this machine; re-derive on yours
    K = 8                        # instructions per element, a real loop body (Ch 77)
    print(f"  model: {NS_PER_INSTRUCTION} ns per instruction x {K} instructions per element")
    print(f"  {'n':>12} {'floor per pass':>15} {'passes per second':>18}")
    for n in (1_000, 100_000, 10_000_000):
        floor_ns = NS_PER_INSTRUCTION * K * n
        ms = floor_ns / 1e6
        floor = (f"{floor_ns / 1e3:.0f} us" if ms < 1
                 else f"{ms:.1f} ms" if ms < 10 else f"{ms:.0f} ms")
        print(f"  {n:>12,} {floor:>15} {1e9 / floor_ns:>18,.0f}")
    print("  the floor is paid before the loop does anything you asked for; when")
    print("  the budget and the floor collide, no rewrite INSIDE the formulation")
    print("  removes it - the formulation itself has to change (Chapters 78, 84)")

    print("--- the escape changes the executor, not the answer ---")
    data = list(range(1_000))
    by_loop = 0
    for x in data:
        by_loop += x * x
    by_genexp = sum(x * x for x in data)
    by_sumprod = math.sumprod(data, data)      # C loop, zero bytecode per element
    print(f"  sum of squares: loop == genexp == math.sumprod : "
          f"{by_loop == by_genexp == by_sumprod}")
    buffer = bytes(200) + b"abc" + bytes(100)
    counted = 0
    for b in buffer:
        if b == 0:
            counted += 1
    print(f"  zero bytes    : manual loop == bytes.count     : "
          f"{counted == buffer.count(0)}")
    print("  same answers, different executors: the C rows run ZERO Python")
    print("  instructions per element, so their constant differs in kind, and")
    print("  bench 173.1 prices the difference")

    print("--- Deep K, as the decision procedure it has been building ---")
    steps = (
        ("measure honestly, or do nothing", "Chapter 85"),
        ("find the hot path, and note its share", "Chapter 86"),
        ("fix the exponent before the constant", "Chapter 87"),
        ("pick the container for the access pattern", "Chapter 88"),
        ("price the memory; pack or slot what is big", "Chapter 89"),
        ("cache what repeats, bounded", "Chapter 90"),
        ("stream what should never be held; fuse hot stages", "Chapter 91"),
        ("requirement met? stop. floor hit? escape", "Chapters 92 and 84"),
    )
    for i, (step, where) in enumerate(steps, 1):
        print(f"  {i}  {step:<50} ({where})")

    print("--- the rule ---")
    print("  optimise until the requirement is met, never until the code is fast;")
    print("  every rung costs clarity, and the budget - not taste - picks the rung")


if __name__ == "__main__":
    main()
