"""Benchmark 182.1 - the loop's cost model: iterations, handoffs, standing armies.

182.1a  the switch, as a function of how busy the loop is: 100,000 total
        `await asyncio.sleep(0)` yields, spread across 1 to 1,000 ready
        tasks. One loop iteration is one selector poll (a syscall) plus a
        FIFO drain of everything ready (Listing 182.1's four steps), so the
        per-switch cost is (iteration overhead / ready tasks) + a resume
        floor. The curve IS the cost model, measured.

182.1b  the directed handoff at concurrency two: A wakes B, B wakes A,
        100,000 times, via asyncio.Event against threading.Event. The
        surprise is honest and instructive: THREADS WIN this shape, because
        a nearly-empty loop pays its full iteration overhead per handoff and
        asyncio's coordination objects are Python-level, while a thread
        Event is C plus a futex.

182.1c  the standing army: 10,000 concurrent task sleepers, against 1,000
        thread sleepers (10,000 OS threads is not something to do to a
        laptop, which is itself a result). Time to run, and bytes per unit.

Together: asyncio does not make switching cheap in the small; it makes
concurrency cheap in the LARGE. The loop amortises its iteration across
everything ready, and its unit of concurrency is a frame, not a stack.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import asyncio
import sys
import threading
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

TOTAL = 100_000


async def yielder(n):
    for _ in range(n):
        await asyncio.sleep(0)


async def spread(tasks, total):
    async with asyncio.TaskGroup() as tg:
        for _ in range(tasks):
            tg.create_task(yielder(total // tasks))


def best(fn, repeat=5):
    runs = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        runs.append(time.perf_counter() - t0)
    return min(runs)


async def async_ping_pong(n):
    a_turn = asyncio.Event()
    b_turn = asyncio.Event()
    a_turn.set()

    async def side(mine, theirs, rounds):
        for _ in range(rounds):
            await mine.wait()
            mine.clear()
            theirs.set()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(side(a_turn, b_turn, n // 2))
        tg.create_task(side(b_turn, a_turn, n // 2))


def thread_ping_pong(n):
    a_turn = threading.Event()
    b_turn = threading.Event()
    a_turn.set()

    def side(mine, theirs, rounds):
        for _ in range(rounds):
            mine.wait()
            mine.clear()
            theirs.set()

    ts = [threading.Thread(target=side, args=(a_turn, b_turn, n // 2)),
          threading.Thread(target=side, args=(b_turn, a_turn, n // 2))]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


def main():
    print("=== 182.1a  per-switch cost against loop busyness ===")
    print(provenance())
    print(f"method      : {TOTAL:,} total sleep(0) yields, min of 5 runs per row")
    print()
    print("  ready tasks    ns per switch")
    print("  -----------------------------")
    for tasks in (1, 2, 10, 100, 1_000):
        dt = best(lambda t=tasks: asyncio.run(spread(t, TOTAL)))
        print(f"  {tasks:>11,} {dt * 1e9 / TOTAL:>15,.0f}")
    print("  one iteration = one selector poll + drain everything ready, so")
    print("  per-switch cost = iteration overhead / ready + a resume floor")

    print()
    print("=== 182.1b  directed handoff at concurrency two ===")
    a = best(lambda: asyncio.run(async_ping_pong(TOTAL)))
    t = best(lambda: thread_ping_pong(TOTAL))
    print(f"  asyncio.Event ping-pong   : {a * 1e9 / TOTAL:8,.0f} ns per handoff")
    print(f"  threading.Event ping-pong : {t * 1e9 / TOTAL:8,.0f} ns per handoff")
    print(f"  threads are {a / t:.1f}x faster at THIS shape: a near-empty loop")
    print("  pays full iteration overhead per wake, and asyncio's Event is")
    print("  Python all the way down while threading's is C over a futex")

    print()
    print("=== 182.1c  the standing army ===")

    async def sleepers(count):
        async with asyncio.TaskGroup() as tg:
            for _ in range(count):
                tg.create_task(asyncio.sleep(0.2))

    tracemalloc.start()
    tracemalloc.reset_peak()
    t0 = time.perf_counter()
    asyncio.run(sleepers(10_000))
    task_time = time.perf_counter() - t0
    _, task_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    def thread_sleepers(count):
        ts = [threading.Thread(target=time.sleep, args=(0.2,))
              for _ in range(count)]
        for th in ts:
            th.start()
        for th in ts:
            th.join()

    tracemalloc.start()
    tracemalloc.reset_peak()
    t0 = time.perf_counter()
    thread_sleepers(1_000)
    thread_time = time.perf_counter() - t0
    _, thread_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"  10,000 tasks sleeping 200 ms : {task_time * 1000:6.0f} ms wall,"
          f" {task_peak / 10_000:6.0f} bytes/task (tracemalloc peak)")
    print(f"  1,000 threads sleeping 200 ms: {thread_time * 1000:6.0f} ms wall,"
          f" {thread_peak / 1_000:6.0f} bytes/thread + ~512 KB C stack each,")
    print("                                 which tracemalloc cannot see")

    print()
    print("Reading this. The three tables are one argument. At concurrency")
    print("two, threads win: the loop's iteration overhead has nothing to")
    print("amortise over and its coordination objects are Python-level. As")
    print("the ready set grows, the poll amortises and the switch falls to")
    print("its resume floor - an order of magnitude under a thread handoff.")
    print("And at ten thousand concurrent waiters, tasks cost a frame each")
    print("where threads cost a stack each, which is the scale asyncio was")
    print("built for. The loop is not a faster thread; it is a cheaper WAIT,")
    print("purchased with Chapter 101's clause that nothing may block it.")


if __name__ == "__main__":
    main()
