"""Benchmark 183.1 - what a layer of `await` costs, and what a suspension costs.

Listing 183.1 showed that awaiting through k coroutine layers presents one
suspension to the loop. This benchmark prices the two separately:

  183.1a  depth without suspension: awaiting a value through 0, 1, 5, and 10
          intermediate `async def` layers, none of which suspend. Each layer
          is a coroutine object plus a frame entered and exited via the
          delegation machinery - Chapter 55's call overhead, in its async
          costume - and the cost is linear in depth.

  183.1b  the suspension itself: awaiting an already-completed Future (no
          loop trip) against awaiting a Future completed by call_soon (one
          full suspension: park the whole chain, run the loop, resume).
          The gap is what Chapter 101's ready-queue trip costs when entered
          from inside a coroutine stack rather than from sleep(0).

The design consequence is stated by the numbers: layers are cheap (tens of
ns) and suspensions are the expensive unit, so factoring async code into many
small `async def`s costs what factoring sync code into functions costs - and
the thing to minimise in hot paths is trips through the loop, not depth.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

CALLS = 100_000


async def leaf():
    return 42


def make_chain(depth):
    coro_fn = leaf
    for _ in range(depth):
        async def layer(next_fn=coro_fn):
            return await next_fn()
        coro_fn = layer
    return coro_fn


async def run_chain(coro_fn, n):
    for _ in range(n):
        await coro_fn()


async def await_done_future(n):
    loop = asyncio.get_running_loop()
    for _ in range(n):
        fut = loop.create_future()
        fut.set_result(42)
        await fut


async def await_pending_future(n):
    loop = asyncio.get_running_loop()
    for _ in range(n):
        fut = loop.create_future()
        loop.call_soon(fut.set_result, 42)
        await fut                      # a real suspension: full loop trip


def best(coro_factory, repeat=5):
    runs = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        asyncio.run(coro_factory())
        runs.append(time.perf_counter() - t0)
    return min(runs) * 1e9 / CALLS


def main():
    print("=== 183.1a  await depth, no suspension ===")
    print(provenance())
    print(f"method      : {CALLS:,} awaited calls per row, min of 5 runs")
    print()
    baseline = None
    for depth in (0, 1, 5, 10):
        chain = make_chain(depth)
        ns = best(lambda c=chain: run_chain(c, CALLS))
        if depth == 0:
            baseline = ns
        extra = f"   +{(ns - baseline) / depth:5.0f} ns per layer" if depth else ""
        print(f"  {depth:>2} extra layers : {ns:7,.0f} ns per await{extra}")

    print()
    print("=== 183.1b  the suspension, priced ===")
    done = best(lambda: await_done_future(CALLS))
    pending = best(lambda: await_pending_future(CALLS))
    print(f"  await an already-done Future : {done:7,.0f} ns  (no loop trip)")
    print(f"  await a pending Future       : {pending:7,.0f} ns  (one loop trip)")
    print(f"  one suspension costs         : {pending - done:7,.0f} ns over the")
    print("  done-future path - the ready-queue trip from Chapter 101, entered")
    print("  and exited through the whole delegation stack")

    print()
    print("Reading this. A layer is a frame: entering and leaving an async")
    print("def through the delegation machinery costs tens of nanoseconds,")
    print("Chapter 55's arithmetic in a new costume, and ten layers cost ten")
    print("times tens. A suspension is a trip through the loop, an order of")
    print("magnitude above a layer. So structure async code the way you")
    print("structure sync code - small functions, clear names - and spend")
    print("optimisation effort where the loop trips are: batching awaits,")
    print("completing futures early, and Chapter 106's buffer-sized reads.")


if __name__ == "__main__":
    main()
