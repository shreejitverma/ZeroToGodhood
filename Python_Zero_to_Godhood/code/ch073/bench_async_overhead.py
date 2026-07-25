"""Benchmark 73.1 - an async generator has real per-item overhead.

Iterating an async generator with async for drives __anext__, which returns a
coroutine the event loop must step; a sync generator resumes a C frame directly.
So for the SAME in-memory sequence (no real awaiting), the async generator costs
several times more per item. This measures both (no I/O), so the machinery cost is
visible. The lesson: async generators are for genuinely async sources, where the
overhead is dwarfed by the I/O wait, not for iterating in-memory data.

Does its own timing (it runs an event loop), guarded by __main__. See
_harness/bench.py.
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 100_000


async def agen(n):
    for i in range(n):
        yield i


def sgen(n):
    for i in range(n):
        yield i


def best_sync(reps=9):
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        total = 0
        for x in sgen(N):
            total += x
        times.append(time.perf_counter() - t0)
    return min(times)


def best_async(reps=9):
    async def once():
        total = 0
        async for x in agen(N):
            total += x
        return total

    async def run():
        times = []
        for _ in range(reps):
            t0 = time.perf_counter()
            await once()
            times.append(time.perf_counter() - t0)
        return min(times)

    return asyncio.run(run())


def main():
    print("=== 73.1  async generator vs sync generator per item (no I/O) ===")
    print(provenance())
    print()

    sync = best_sync()
    asyncr = best_async()
    print(f"  sync generator  : {sync / N * 1e9:6.0f} ns/item")
    print(f"  async generator : {asyncr / N * 1e9:6.0f} ns/item")
    print(f"  overhead        : {asyncr / sync:6.1f}x")

    print()
    print("Reading this. With no real awaiting, the async generator is several")
    print("times slower per item, because each item is driven through __anext__ and")
    print("the coroutine/event-loop machinery, while the sync generator resumes a")
    print("frame directly. So do NOT use an async generator to iterate in-memory")
    print("data, use a plain generator. Use an async generator ONLY when the source")
    print("is genuinely async (awaiting network, disk, a queue) between items, where")
    print("the per-item overhead is dwarfed by the I/O wait and the interleaving of")
    print("many streams is the whole point.")


if __name__ == "__main__":
    main()
