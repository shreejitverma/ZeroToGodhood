"""Benchmark 154.1 - a try block is free on the happy path; raising is costly.

Two measurements. First, a loop with a try/except that never raises, versus the same
loop without the try: they run at the same speed (zero-cost exceptions since 3.11).
Second, the cost of actually raising and catching an exception per iteration: real work.
Together they justify EAFP (try freely) while warning against exceptions as hot-loop
control flow (raising is expensive).

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

LOOP = 1000
N = 50_000


def with_try():
    total = 0
    for i in range(LOOP):
        try:
            total += i
        except ValueError:
            pass
    return total


def without_try():
    total = 0
    for i in range(LOOP):
        total += i
    return total


def raising():
    caught = 0
    for _ in range(LOOP):
        try:
            raise ValueError
        except ValueError:
            caught += 1
    return caught


def main():
    print("=== 154.1  try-with-no-raise vs no-try, and the cost of raising ===")
    print(provenance())
    print()

    t_try = min(timeit.repeat(with_try, number=N, repeat=5)) / N
    t_no = min(timeit.repeat(without_try, number=N, repeat=5)) / N
    t_raise = min(timeit.repeat(raising, number=N // 10, repeat=5)) / (N // 10) / LOOP

    print(f"  loop WITH try (never raises) : {t_try * 1e6:5.1f} us")
    print(f"  loop WITHOUT try             : {t_no * 1e6:5.1f} us   (try overhead: {t_try / t_no:.2f}x, ~free)")
    print(f"  cost of raising+catching     : {t_raise * 1e9:5.0f} ns per raise")

    print()
    print("Reading this. The try block adds essentially no overhead when nothing is")
    print("raised (~1.0x), because since Python 3.11 the exception-handling info is")
    print("out-of-line (co_exceptiontable): the happy path runs the try body's")
    print("bytecode with no setup/teardown, and the table is consulted only when an")
    print("exception actually propagates. So the old advice 'avoid try/except for")
    print("speed' is obsolete: wrap the normal case in try/except freely (EAFP), it is")
    print("free on the path that does not raise. BUT raising an exception costs real")
    print("time (tens of nanoseconds: unwind the stack, build and match the exception),")
    print("so do NOT use exceptions as ordinary control flow in a hot loop (a raise")
    print("per element). Exceptions are for the EXCEPTIONAL: cheap to guard against,")
    print("costly to trigger. Guard freely; raise rarely.")


if __name__ == "__main__":
    main()
