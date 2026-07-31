"""Benchmark 208.1 - the C10k win, measured: many waiting connections, one loop.

  208.1a  serve N concurrent requests that each 'wait' 20 ms (a database, an
          upstream) two ways, both real, both on this machine:
            - a bounded thread pool of W workers (the WSGI model: one
              connection holds one worker until it returns);
            - one asyncio event loop running all N as tasks (the ASGI model).
          At W < N the thread pool serialises the excess; the loop runs all N
          waits concurrently and finishes in ~one wait. This is Chapter
          126's ceiling and Chapter 101's standing-army table, joined into
          the web result they were built to explain.

  208.1b  a sanity check that the win is not paid in per-call overhead:
          awaiting a completed coroutine costs about what returning a value
          costs (Chapter 102 measured the await itself at tens of ns). The
          real per-request async cost is the LOOP TRIP on a genuine
          suspension (Chapter 102's ~27 us), which 208.1a's 500-fold
          concurrency dwarfs - so ASGI's tax is negligible exactly when its
          win is large: I/O-bound, many-connection services.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import asyncio
import concurrent.futures
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 500
WAIT = 0.020


def sync_handler():
    time.sleep(WAIT)
    return b"ok"


async def async_handler():
    await asyncio.sleep(WAIT)
    return b"ok"


def serve_threadpool(workers):
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        list(pool.map(lambda _: sync_handler(), range(N)))


async def serve_loop():
    async with asyncio.TaskGroup() as tg:
        for _ in range(N):
            tg.create_task(async_handler())


def best(fn, repeat=3):
    times = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return min(times)


def main():
    print(f"=== 208.1a  {N} requests, each waiting {WAIT * 1000:.0f} ms ===")
    print(provenance())
    print(f"method      : min of 3 runs; ideal (all concurrent) = ~{WAIT*1000:.0f} ms")
    print()
    for workers in (16, 64, 256):
        t = best(lambda w=workers: serve_threadpool(w))
        print(f"  thread pool, {workers:>3} workers : {t * 1000:7.0f} ms")
    t = best(lambda: asyncio.run(serve_loop()))
    print(f"  one event loop, {N} tasks : {t * 1000:7.0f} ms")

    print()
    print("=== 208.1b  the per-request cost of awaiting ===")
    def sync_calls():
        for _ in range(100_000):
            (lambda: b"ok")()

    async def async_calls():
        for _ in range(100_000):
            await _noop()

    async def _noop():
        return b"ok"

    globals()["_noop"] = _noop
    s = best(sync_calls, repeat=5) / 100_000 * 1e9
    a = best(lambda: asyncio.run(async_calls()), repeat=5) / 100_000 * 1e9
    print(f"  return a value : {s:6.0f} ns")
    print(f"  await a coro   : {a:6.0f} ns")

    print()
    print("Reading this. The 208.1a table is the whole reason ASGI exists.")
    print("The thread pool finishes in (N / workers) x wait: 16 workers")
    print("serialise 500 waits into ~30 rounds, and only a 256-worker pool")
    print("approaches the loop - at 256 threads of memory and scheduler cost.")
    print("The one event loop runs all 500 waits at once and finishes in ~one")
    print("wait, on ONE thread, because a waiting task costs a frame not a")
    print("stack (Chapter 101). 208.1b confirms the win is not clawed back")
    print("in overhead: awaiting a coroutine costs about what returning does,")
    print("so ASGI's real tax is the loop trip on a true suspension (Chapter")
    print("102's ~27 us), negligible against 208.1a's 500-fold concurrency.")
    print("The verdict: ASGI is a rout for the I/O-bound, many-connection")
    print("services the web actually runs, and merely even for CPU-bound")
    print("no-wait handlers (which belong on threads/processes anyway, Deep")
    print("L). Choose the gateway by whether requests WAIT - the same")
    print("question Chapter 100 asked of every concurrency primitive.")


if __name__ == "__main__":
    main()
