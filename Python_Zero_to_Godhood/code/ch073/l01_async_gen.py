"""Listing 73.1 - async generators: stream async data with async for.

An async generator is `async def` + `yield`: it can `await` between items (waiting
on I/O) and is consumed with `async for` (or an async comprehension). Its value is
that multiple async streams INTERLEAVE: while one awaits, others make progress, so
several sources are consumed concurrently on one thread (the asyncio model,
Chapters 10-11). This listing shows an async generator, an async comprehension,
and two streams interleaving. It is deterministic: each item awaits sleep(0),
yielding control fairly, so the two streams alternate.
"""

import asyncio


async def stream(tag, n):
    for i in range(n):
        await asyncio.sleep(0)        # yield control (stands in for awaiting I/O)
        yield f"{tag}{i}"


async def run() -> None:
    print("--- async comprehension collects an async generator ---")
    items = [x async for x in stream("page", 3)]
    print(f"  [x async for x in stream(...)] : {items}")

    print("--- async for streams items one at a time ---")
    async for x in stream("row", 2):
        print(f"  streamed : {x}")

    print("--- two async streams interleave (concurrent on one thread) ---")
    order = []

    async def drain(tag, n):
        async for v in stream(tag, n):
            order.append(v)

    await asyncio.gather(drain("A", 3), drain("B", 3))
    print(f"  interleaved order : {order}")
    print(f"  (A and B alternate: each yields control at every await)")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
