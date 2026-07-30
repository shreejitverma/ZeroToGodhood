"""Benchmark 184.1 - what a Task costs: creation, the eager dividend, fan-out.

184.1a  one task, created and awaited, for a coroutine that completes
        without suspending: the default factory against the eager factory
        (3.12+). The default pays a loop trip to start the body (Chapter
        102's suspension price); the eager factory runs the body at
        create_task and pays it only if the body actually suspends.

184.1b  fan-out overhead: run 10,000 trivial coroutines sequentially (the
        no-concurrency floor), with gather, and with TaskGroup. The
        difference over the floor, divided by 10,000, is the bookkeeping a
        task adds when you fan out - the number to weigh per Chapter 108's
        patterns.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 10_000


async def trivial():
    return 1


def best(coro_factory, repeat=5):
    runs = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        asyncio.run(coro_factory())
        runs.append(time.perf_counter() - t0)
    return min(runs)


def main():
    print("=== 184.1a  create_task + await, non-suspending body ===")
    print(provenance())
    print(f"method      : {N:,} tasks per run, min of 5 runs")
    print()

    async def default_factory():
        for _ in range(N):
            await asyncio.create_task(trivial())

    async def eager_factory():
        asyncio.get_running_loop().set_task_factory(asyncio.eager_task_factory)
        for _ in range(N):
            await asyncio.create_task(trivial())

    d = best(default_factory) * 1e9 / N
    e = best(eager_factory) * 1e9 / N
    print(f"  default factory : {d:7,.0f} ns per task")
    print(f"  eager factory   : {e:7,.0f} ns per task   ({d / e:.1f}x cheaper)")
    print("  the default queues the first send: one loop trip before the body")
    print("  runs at all. eager runs it at create_task and, for bodies that")
    print("  complete synchronously, never touches the ready queue")

    print()
    print("=== 184.1b  fan-out bookkeeping over 10,000 trivial coroutines ===")

    async def sequential():
        for _ in range(N):
            await trivial()

    async def with_gather():
        await asyncio.gather(*(trivial() for _ in range(N)))

    async def with_taskgroup():
        async with asyncio.TaskGroup() as tg:
            for _ in range(N):
                tg.create_task(trivial())

    s = best(sequential) * 1e9 / N
    g = best(with_gather) * 1e9 / N
    t = best(with_taskgroup) * 1e9 / N
    print(f"  sequential awaits (floor) : {s:7,.0f} ns per coroutine")
    print(f"  gather                    : {g:7,.0f} ns  (+{g - s:,.0f} bookkeeping)")
    print(f"  TaskGroup                 : {t:7,.0f} ns  (+{t - s:,.0f} bookkeeping)")

    print()
    print("Reading this. A Task is a Future, a driver, a context copy, and an")
    print("entry in the loop's bookkeeping, and the tables price that at a")
    print("few microseconds each under the default factory. The eager factory")
    print("collapses the start-up loop trip for bodies that complete at once,")
    print("which is common in cache-hit-shaped services (Chapter 102's done-")
    print("future dividend, applied to whole tasks). For fan-out, gather and")
    print("TaskGroup add comparable per-task bookkeeping over the sequential")
    print("floor; the choice between them is Chapter 104's semantics - error")
    print("handling and cancellation - not this table's nanoseconds.")


if __name__ == "__main__":
    main()
