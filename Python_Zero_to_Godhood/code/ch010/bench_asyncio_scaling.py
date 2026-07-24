"""Benchmark 10.1 - what asyncio actually buys, and what it does not.

The event loop overlaps I/O waits on one thread. This measures three things and,
in the process, corrects a common oversimplification ("asyncio is faster than
threads").

  1. asyncio vs sequential: the overlap win is huge (many waits collapse to one).
  2. asyncio vs threads: at moderate task counts they are comparable in TIME;
     both overlap the waits.
  3. asyncio vs threads at SCALE: an asyncio Task costs a few hundred bytes; a
     thread reserves a full stack. This, not raw speed, is why asyncio scales to
     task counts threads cannot.

Coarse-grained timing done directly (an event loop is not a microbenchmark);
provenance header reused from the harness.
"""

import asyncio
import sys
import threading
import time
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 500
DELAY = 0.05


async def sleeper(d):
    await asyncio.sleep(d)


async def gather_n(n, d):
    await asyncio.gather(*[sleeper(d) for _ in range(n)])


def best(fn, repeat=3):
    return min(_timed(fn) for _ in range(repeat))


def _timed(fn):
    t0 = time.perf_counter()
    fn()
    return time.perf_counter() - t0


def run_threads(n, d):
    ts = [threading.Thread(target=time.sleep, args=(d,)) for _ in range(n)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


async def task_bytes(n):
    tracemalloc.start()
    tasks = [asyncio.ensure_future(sleeper(10)) for _ in range(n)]
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    for t in tasks:
        t.cancel()
    return peak / n


def main():
    print("=== 10.1  what asyncio buys ===")
    print(provenance())
    print(f"method      : {N} concurrent {DELAY}s I/O waits, min of 3 runs")
    print()

    seq = best(lambda: [time.sleep(DELAY) for _ in range(N)], repeat=1)
    aio = best(lambda: asyncio.run(gather_n(N, DELAY)))
    thr = best(lambda: run_threads(N, DELAY))
    print(f"  sequential      : {seq:7.3f} s   {seq / aio:6.0f}x asyncio")
    print(f"  asyncio gather  : {aio:7.3f} s   1.00x")
    print(f"  {N} threads      : {thr:7.3f} s   {thr / aio:6.2f}x asyncio")

    print()
    print("scaling (asyncio, one thread):")
    for n in (100, 2000):
        el = _timed(lambda n=n: asyncio.run(gather_n(n, DELAY)))
        print(f"  gather {n:5d} x {DELAY}s: {el:.3f} s")

    per = asyncio.run(task_bytes(5000))
    print()
    print(f"per-unit memory: asyncio Task ~{per:.0f} bytes; a thread reserves a")
    print("full stack (OS default, ~8 MB of virtual address space each).")
    print()
    print("The honest reading. Against SEQUENTIAL code, asyncio's overlap is a")
    print("huge win, but threads overlap I/O too, so at moderate counts asyncio")
    print("and threads finish in comparable time. asyncio's real advantage is")
    print("SCALE: a task is a few hundred bytes and the loop is one thread, so it")
    print("serves tens of thousands of concurrent connections where a thread-per-")
    print("connection model runs out of memory or hits the OS thread limit. Use")
    print("asyncio for high-count I/O concurrency, not for raw speed over threads.")


if __name__ == "__main__":
    main()
