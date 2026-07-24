"""Listing 10.1 - the event loop overlaps waits: concurrency on one thread.

asyncio (PEP 3156, Python 3.4) is one thread, one event loop, cooperative
multitasking. Tasks voluntarily suspend at await points; while one waits on I/O,
the loop runs others. The loop registers each descriptor with the selectors
module (epoll on Linux, kqueue on macOS, select elsewhere), blocks the single
thread in the kernel until one is ready, then resumes the suspended task.

This listing shows the payoff structurally (three waits overlap so the total is
one delay, not three) rather than printing a timing number, which would vary per
run. The timing itself is measured in bench_asyncio_scaling.py.
"""

import asyncio
import time

print("--- the 3.4-era @asyncio.coroutine decorator was removed in 3.11 ---")
print("  hasattr(asyncio, 'coroutine'):", hasattr(asyncio, "coroutine"))


async def worker(name, delay):
    await asyncio.sleep(delay)
    return f"{name} done"


async def main():
    t0 = time.perf_counter()
    results = await asyncio.gather(
        worker("A", 0.05), worker("B", 0.05), worker("C", 0.05)
    )
    return results, time.perf_counter() - t0


results, elapsed = asyncio.run(main())
print()
print("--- three 0.05s waits run concurrently on one thread ---")
print("  results:", results)
print("  overlapped (elapsed well under the 0.15s serial sum):", elapsed < 0.12)
print()
print("This is cooperative scheduling, like Go's goroutines or Node's loop, but")
print("explicit: a task runs uninterrupted until it awaits, so no lock is needed")
print("for data touched only between awaits. The flip side: a blocking call")
print("(a synchronous requests.get, a CPU loop) freezes the entire loop.")
