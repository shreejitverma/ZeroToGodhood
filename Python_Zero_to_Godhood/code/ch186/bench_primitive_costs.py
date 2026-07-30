"""Benchmark 186.1 - the async primitives, priced against their thread cousins.

Chapter 101's handoff table already showed asyncio.Event losing to
threading.Event at concurrency two. This benchmark completes the price list
for the objects Chapter 105 teaches, in the shape they are actually used:

  186.1a  uncontended pass-through: acquire/release an asyncio.Lock and a
          Semaphore with nobody waiting, against threading.Lock, and against
          no lock at all. The async objects are pure Python; the thread lock
          is C. Uncontended, none of them suspends.

  186.1b  queue hand-off within one loop: asyncio.Queue put+get against a
          plain collections.deque (the no-machinery floor) and against
          queue.Queue used same-thread (its lock uncontended).

The point is calibration, not disqualification: these costs buy wakeup
bookkeeping that plain objects lack, and they are paid per OPERATION, so the
arithmetic of Chapter 88 applies - fine around real awaits, wasteful as
inner-loop decoration.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import asyncio
import collections
import queue as thread_queue
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 100_000


def best_async(coro_factory, repeat=5):
    runs = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        asyncio.run(coro_factory())
        runs.append(time.perf_counter() - t0)
    return min(runs) * 1e9 / N


def best_sync(fn, repeat=5):
    runs = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        runs.append(time.perf_counter() - t0)
    return min(runs) * 1e9 / N


def main():
    print("=== 186.1a  uncontended acquire/release ===")
    print(provenance())
    print(f"method      : {N:,} operations per run, min of 5 runs")
    print()

    async def no_lock():
        x = 0
        for _ in range(N):
            x += 1

    async def async_lock():
        lock = asyncio.Lock()
        for _ in range(N):
            async with lock:
                pass

    async def async_sem():
        sem = asyncio.Semaphore(1)
        for _ in range(N):
            async with sem:
                pass

    def thread_lock():
        lock = threading.Lock()
        for _ in range(N):
            with lock:
                pass

    print(f"  no lock (floor)     : {best_async(no_lock):6,.0f} ns")
    print(f"  threading.Lock      : {best_sync(thread_lock):6,.0f} ns")
    print(f"  asyncio.Lock        : {best_async(async_lock):6,.0f} ns")
    print(f"  asyncio.Semaphore   : {best_async(async_sem):6,.0f} ns")
    print("  uncontended, none of these suspends; the async objects pay their")
    print("  Python-level bookkeeping per pass, the thread lock is one C call")

    print()
    print("=== 186.1b  same-thread queue hand-off, put + get ===")

    async def async_queue():
        q: asyncio.Queue = asyncio.Queue()
        for i in range(N):
            q.put_nowait(i)
            q.get_nowait()

    def plain_deque():
        d: collections.deque = collections.deque()
        for i in range(N):
            d.append(i)
            d.popleft()

    def threadsafe_queue():
        q: thread_queue.Queue = thread_queue.Queue()
        for i in range(N):
            q.put(i)
            q.get()

    print(f"  collections.deque (floor) : {best_sync(plain_deque):6,.0f} ns")
    print(f"  asyncio.Queue (nowait)    : {best_async(async_queue):6,.0f} ns")
    print(f"  queue.Queue               : {best_sync(threadsafe_queue):6,.0f} ns")

    print()
    print("Reading this. The async primitives are Python objects doing")
    print("Python-level bookkeeping: an uncontended async lock costs a few")
    print("hundred nanoseconds where the C thread lock costs tens, and the")
    print("async queue sits between the raw deque and the fully locked")
    print("queue.Queue. None of this matters next to a 27,000 ns suspension")
    print("(Chapter 102) or real I/O - and all of it matters if a primitive")
    print("decorates an inner loop. Use them where invariants cross awaits")
    print("(Listing 186.1's rule) and where flow needs bounding, and let the")
    print("model's own atomicity cover everything between awaits for free.")


if __name__ == "__main__":
    main()
