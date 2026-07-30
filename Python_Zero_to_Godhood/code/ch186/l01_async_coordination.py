"""Listing 186.1 - async coordination: when the loop is the lock, and when not.

Chapter 101's determinism has a consequence Deep E readers find heretical:
most async code needs NO locks, because nothing preempts between awaits - the
first block increments a shared counter from four tasks, unlocked, exactly.
The second block shows the one case that still races: an invariant held
ACROSS an await - and because the schedule is deterministic, this listing
prints the race's corrupted value EXACTLY, every run, on every build. A
reproducible race is something Deep E could never print; it is this model's
signature party trick, and the reason async bugs are findable.

Then the tools for the across-await case: Lock, Queue with backpressure, and
Semaphore as a concurrency bound - all single-threaded, none thread-safe,
which is stated at the end because it is the migration trap.
"""

import asyncio


def main() -> None:
    print("--- between awaits, nothing preempts: unlocked and exact ---")
    counter = 0

    async def bump(n):
        nonlocal counter
        for _ in range(n):
            counter += 1        # no await inside: atomic by the model itself
        await asyncio.sleep(0)

    async def unlocked():
        async with asyncio.TaskGroup() as tg:
            for _ in range(4):
                tg.create_task(bump(100_000))

    asyncio.run(unlocked())
    print(f"  4 tasks x 100,000 unlocked increments : {counter:,}")
    print("  Chapter 99's benchmark lost a third of these on the free-threaded")
    print("  build; here the count is exact BY THE MODEL: a task owns the loop")
    print("  between its awaits, so call-free sequences cannot interleave")

    print("--- but an invariant held ACROSS an await races, deterministically ---")
    balance = {"value": 0}

    async def read_modify_write():
        seen = balance["value"]       # read
        await asyncio.sleep(0)        # ...suspend with the invariant open...
        balance["value"] = seen + 1   # write back a stale value

    async def racy():
        async with asyncio.TaskGroup() as tg:
            tg.create_task(read_modify_write())
            tg.create_task(read_modify_write())

    asyncio.run(racy())
    print(f"  two unlocked read-await-write increments : "
          f"balance = {balance['value']}  (one update LOST)")

    balance["value"] = 0
    lock = None

    async def locked_rmw():
        async with lock:
            seen = balance["value"]
            await asyncio.sleep(0)
            balance["value"] = seen + 1

    async def fixed():
        nonlocal lock
        lock = asyncio.Lock()
        async with asyncio.TaskGroup() as tg:
            tg.create_task(locked_rmw())
            tg.create_task(locked_rmw())

    asyncio.run(fixed())
    print(f"  the same two increments under asyncio.Lock : "
          f"balance = {balance['value']}")
    print("  the async race is DETERMINISTIC - it printed the same lost update")
    print("  it will print on your machine - which is why it is findable in a")
    print("  test where a thread race is a distribution (Chapter 99). the rule:")
    print("  lock exactly the invariants that stay open across an await")

    print("--- Queue(maxsize): backpressure is built in ---")
    log: list[str] = []

    async def producer(q):
        for i in range(4):
            await q.put(i)
            log.append(f"put-{i}")

    async def consumer(q):
        for _ in range(4):
            await asyncio.sleep(0)
            item = await q.get()
            log.append(f"got-{item}")

    async def pipeline():
        q: asyncio.Queue = asyncio.Queue(maxsize=2)
        async with asyncio.TaskGroup() as tg:
            tg.create_task(producer(q))
            tg.create_task(consumer(q))

    asyncio.run(pipeline())
    print(f"  maxsize=2 : {', '.join(log)}")
    print("  the producer stalled at put-2 until the consumer drained one: a")
    print("  bounded queue makes the fast side wait for the slow side, which")
    print("  is flow control nobody has to remember to write")

    print("--- Semaphore: concurrency as a budget ---")
    in_flight = 0
    high_water = 0

    async def limited(sem):
        nonlocal in_flight, high_water
        async with sem:
            in_flight += 1
            high_water = max(high_water, in_flight)
            await asyncio.sleep(0)
            in_flight -= 1

    async def bounded_fanout():
        sem = asyncio.Semaphore(2)
        async with asyncio.TaskGroup() as tg:
            for _ in range(6):
                tg.create_task(limited(sem))

    asyncio.run(bounded_fanout())
    print(f"  6 tasks through Semaphore(2), max in flight : {high_water}")
    print("  the fan-out pattern of Chapter 108 in one object: admit two,")
    print("  the rest wait their turn on the loop, no threads, no spinning")

    print("--- the migration trap, stated plainly ---")
    print("  every object above is single-threaded machinery: awaiting wakes")
    print("  via the loop, and NONE of it is thread-safe. threads talk to a")
    print("  loop through call_soon_threadsafe and run_coroutine_threadsafe")
    print("  (Chapter 107), never by touching asyncio primitives directly")


if __name__ == "__main__":
    main()
