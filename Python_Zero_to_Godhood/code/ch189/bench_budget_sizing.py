"""Benchmark 189.1 - the capstone: sizing a concurrency budget, measured.

One thousand fake requests through Listing 189.1's skeleton (TaskGroup +
Semaphore), each request 10 ms of pure waiting, at budgets from 10 to 1,000.
Little's law says throughput = budget / latency until something else binds,
and the table shows the law holding and then breaking:

  in the WAITING regime, doubling the budget doubles throughput, because
  waiters are nearly free (Chapter 101: 1.4 KB and a frame each);

  adding 1 ms of CPU per request exposes the OTHER bound: one thread can
  execute at most 1,000 x 1 ms of bytecode per second, so past the point
  where the loop saturates, budget buys queueing, not throughput - Chapter
  100's composition rule, measured from the asyncio side.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

REQUESTS = 1_000
WAIT = 0.010


def spin(ms):
    deadline = time.perf_counter() + ms / 1000
    while time.perf_counter() < deadline:
        pass


async def run_batch(budget, cpu_ms):
    sem = asyncio.Semaphore(budget)

    async def request():
        async with sem:
            await asyncio.sleep(WAIT)
            if cpu_ms:
                spin(cpu_ms)

    async with asyncio.TaskGroup() as tg:
        for _ in range(REQUESTS):
            tg.create_task(request())


def best(budget, cpu_ms, repeat=3):
    runs = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        asyncio.run(run_batch(budget, cpu_ms))
        runs.append(time.perf_counter() - t0)
    return min(runs)


def main():
    print("=== 189.1  1,000 requests of 10 ms wait, by budget ===")
    print(provenance())
    print("method      : min of 3 runs per cell")
    print()
    print("  budget    pure wait         wait + 1 ms CPU")
    print("  ------------------------------------------------")
    for budget in (10, 50, 100, 500, 1_000):
        w = best(budget, 0)
        c = best(budget, 1)
        print(f"  {budget:>6} {w * 1000:8.0f} ms ({REQUESTS / w:6,.0f}/s)"
              f" {c * 1000:10.0f} ms ({REQUESTS / c:6,.0f}/s)")

    print()
    print("Reading this. The pure-wait column is Little's law with nothing in")
    print("the way: 1,000 requests x 10 ms / budget, so budget 1,000 runs the")
    print("whole batch in one wait. Waiters are what Chapter 101 priced them:")
    print("nearly free. The CPU column hits the other wall: 1,000 requests x")
    print("1 ms of bytecode is one full second on the loop's single thread,")
    print("and no budget can go below it - past saturation, budget buys")
    print("longer queues and worse tail latency, not throughput. Sizing an")
    print("async service is therefore two measurements, not one: the wait")
    print("your budget divides, and the CPU floor your single thread imposes;")
    print("when the second binds, Chapter 107's bridges and Chapter 100's")
    print("table are the next chapter of your capacity plan.")


if __name__ == "__main__":
    main()
