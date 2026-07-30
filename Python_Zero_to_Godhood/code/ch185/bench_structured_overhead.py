"""Benchmark 185.1 - what the structure costs: timeout wrappers, group raises.

185.1a  asyncio.timeout around an await that never times out: the price of
        wearing a deadline. A timeout is a timer handle scheduled and
        cancelled per block, and services wrap nearly every operation in
        one, so the per-block price is a real budget line.

185.1b  the error path: raising and catching one plain ValueError through
        try/except, against one ValueError arriving as an ExceptionGroup
        through TaskGroup + except*. The group's error path carries task
        bookkeeping, sibling cancellation, and group construction; it is an
        ERROR path, and the number says to keep it off the hot path.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 50_000


async def nothing():
    return 1


def best(coro_factory, n, repeat=5):
    runs = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        asyncio.run(coro_factory())
        runs.append(time.perf_counter() - t0)
    return min(runs) * 1e9 / n


def main():
    print("=== 185.1a  the price of a deadline that never fires ===")
    print(provenance())
    print(f"method      : {N:,} operations per run, min of 5 runs")
    print()

    async def bare():
        for _ in range(N):
            await nothing()

    async def with_timeout():
        for _ in range(N):
            async with asyncio.timeout(60):
                await nothing()

    bare_ns = best(bare, N)
    timed_ns = best(with_timeout, N)
    print(f"  bare await                 : {bare_ns:6,.0f} ns")
    print(f"  wrapped in asyncio.timeout : {timed_ns:6,.0f} ns"
          f"   (+{timed_ns - bare_ns:,.0f} per block)")
    print("  a timeout block schedules a timer handle and cancels it on the")
    print("  way out; wear one per REQUEST, not one per await")

    print()
    print("=== 185.1b  the error path, plain vs structured ===")
    ERRORS = 5_000

    async def plain_raises():
        for _ in range(ERRORS):
            try:
                raise ValueError("x")
            except ValueError:
                pass

    async def fail_task():
        raise ValueError("x")

    async def group_raises():
        for _ in range(ERRORS):
            try:
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(fail_task())
            except* ValueError:
                pass

    plain_ns = best(plain_raises, ERRORS)
    group_ns = best(group_raises, ERRORS)
    print(f"  raise/except ValueError            : {plain_ns:7,.0f} ns")
    print(f"  TaskGroup + failing task + except* : {group_ns:7,.0f} ns"
          f"   ({group_ns / plain_ns:,.0f}x)")

    print()
    print("Reading this. The timeout wrapper's cost is a timer handle's")
    print("lifecycle - fine per request, wasteful per micro-await; deadlines")
    print("compose downward for free (an outer timeout bounds everything")
    print("inside), so one per boundary is the design. The structured error")
    print("path costs orders of magnitude more than a plain exception because")
    print("it IS more: a task, a group, sibling bookkeeping, and an")
    print("ExceptionGroup. Chapter 73 taught that the try is free and the")
    print("raise is the price; groups raise that price again - which is fine,")
    print("because failures are supposed to be rare, and structure is for")
    print("making rare failures IMPOSSIBLE TO LOSE, not cheap to throw.")


if __name__ == "__main__":
    main()
