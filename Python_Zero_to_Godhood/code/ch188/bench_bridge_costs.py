"""Benchmark 188.1 - what the bridges cost, per crossing.

  188.1a  loop -> thread: asyncio.to_thread and loop.run_in_executor around
          a trivial function, against calling it directly. The bridge is a
          thread-pool submission, a concurrent Future, its asyncio wrapper,
          and a threadsafe wakeup: microseconds, paid per call.

  188.1b  thread -> loop: run_coroutine_threadsafe round trips from a worker
          thread, and call_soon_threadsafe fire-and-forget posts.

The unit to remember: a bridge crossing costs tens of microseconds, hundreds
of times a plain call. That is irrelevant around a 10 ms database query and
ruinous around a 10 us parser - Chapter 100's grain rule, applied to the
two-color boundary. Batch the small stuff; bridge the big stuff.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import asyncio
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 2_000


def trivial(x=1):
    return x + 1


def best_async(coro_factory, n, repeat=5):
    runs = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        asyncio.run(coro_factory())
        runs.append(time.perf_counter() - t0)
    return min(runs) * 1e9 / n


def main():
    print("=== 188.1a  loop -> thread, per crossing ===")
    print(provenance())
    print(f"method      : {N:,} crossings per run, min of 5 runs")
    print()

    async def direct():
        for _ in range(N):
            trivial()

    async def to_thread():
        for _ in range(N):
            await asyncio.to_thread(trivial)

    async def executor():
        loop = asyncio.get_running_loop()
        for _ in range(N):
            await loop.run_in_executor(None, trivial)

    d = best_async(direct, N)
    t = best_async(to_thread, N)
    e = best_async(executor, N)
    print(f"  direct call            : {d:8,.0f} ns")
    print(f"  loop.run_in_executor   : {e:8,.0f} ns")
    print(f"  asyncio.to_thread      : {t:8,.0f} ns")
    print("  to_thread = run_in_executor + a context copy; both are a pool")
    print("  submission, a Future pair, and a threadsafe wakeup per call")

    print()
    print("=== 188.1b  thread -> loop, per crossing ===")

    async def nothing():
        return 1

    results = {}

    async def host():
        loop = asyncio.get_running_loop()
        done = threading.Event()

        def worker():
            t0 = time.perf_counter()
            for _ in range(N):
                asyncio.run_coroutine_threadsafe(nothing(), loop).result()
            results["rct"] = (time.perf_counter() - t0) * 1e9 / N

            t0 = time.perf_counter()
            for _ in range(N):
                loop.call_soon_threadsafe(trivial)
            results["cst"] = (time.perf_counter() - t0) * 1e9 / N
            done.set()

        threading.Thread(target=worker).start()
        await asyncio.to_thread(done.wait)

    asyncio.run(host())
    print(f"  run_coroutine_threadsafe (round trip) : {results['rct']:8,.0f} ns")
    print(f"  call_soon_threadsafe (post only)      : {results['cst']:8,.0f} ns")

    print()
    print("Reading this. Every crossing is tens of microseconds: a pool")
    print("submission or a threadsafe post, a selector wakeup, and a Future")
    print("completing across worlds. Around real blocking work - a query, a")
    print("file, a legacy client - the bridge is free and mandatory. Around")
    print("tiny work it is a 1000x tax, and the fix is Chapter 100's grain")
    print("rule: batch the small calls into one bridged call (one to_thread")
    print("that runs the whole loop of parses), never a bridged call per")
    print("small item. The post-only door is an order cheaper than the round")
    print("trip - fire-and-forget notifications should use it.")


if __name__ == "__main__":
    main()
