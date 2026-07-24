"""Benchmark 11.1 - await is not free, even when nothing suspends.

The anti-pattern in section 11.5 is making everything async when it does not need
to await I/O. This sizes the cost: a loop that awaits a trivial coroutine (one
that returns immediately, never actually suspending) versus the same loop calling
a plain function. The gap is the pure overhead of the coroutine-and-await
machinery, paid whether or not there is any I/O to overlap.

Coarse-grained timing done directly (an event loop is not a microbenchmark);
provenance header reused from the harness.
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 100_000


async def leaf_async():
    return 1


def leaf_sync():
    return 1


async def chain_async(n):
    total = 0
    for _ in range(n):
        total += await leaf_async()
    return total


def chain_sync(n):
    total = 0
    for _ in range(n):
        total += leaf_sync()
    return total


def best(fn, repeat=5):
    return min(_timed(fn) for _ in range(repeat))


def _timed(fn):
    t0 = time.perf_counter()
    fn()
    return time.perf_counter() - t0


def main():
    print("=== 11.1  the cost of await when nothing suspends ===")
    print(provenance())
    print(f"method      : {N:,} iterations, min of 5 runs, perf_counter")
    print()

    a = best(lambda: asyncio.run(chain_async(N)))
    s = best(lambda: chain_sync(N))
    print(f"  {N:,} plain calls : {s * 1e6:9.0f} us   1.00x")
    print(f"  {N:,} awaits      : {a * 1e6:9.0f} us   {a / s:.1f}x")

    print()
    print("Reading this. Awaiting a coroutine that completes immediately still")
    print("costs several times a plain call: the interpreter builds a coroutine")
    print("object, drives it with SEND, and unwinds it, for every await. That")
    print("overhead is worth paying when the await overlaps real I/O (Chapter 10")
    print("showed the payoff). It is pure waste when a function is marked async")
    print("but never actually awaits anything that blocks. Do not make code async")
    print("for style; make it async where it awaits I/O.")


if __name__ == "__main__":
    main()
