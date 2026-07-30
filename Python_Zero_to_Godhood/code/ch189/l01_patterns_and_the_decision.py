"""Listing 189.1 - the patterns, composed, and the volume closed.

Deep J closes the way this book closes volumes: the pieces assembled into the
shapes production code actually takes, each proven with a deterministic order
log, then the decision procedure handed over. Three patterns cover most async
services: BOUNDED FAN-OUT (TaskGroup + Semaphore + timeout - the service
skeleton), HEDGED RACE (first response wins, losers cancelled), and GRACEFUL
SHUTDOWN (stop intake, drain, then cancel). Every piece is a chapter of this
volume; the composition is this listing.
"""

import asyncio


def main() -> None:
    print("--- pattern 1: bounded fan-out, the service skeleton ---")
    peak = 0

    async def fetch(job, sem, results):
        nonlocal peak
        async with sem:
            peak = max(peak, sem_holders())
            await asyncio.sleep(0)
            results.append(job * 10)

    def sem_holders():
        return budget - sem._value          # introspection for the proof only

    budget = 3
    sem = asyncio.Semaphore(budget)

    async def skeleton():
        results: list[int] = []
        async with asyncio.timeout(5):
            async with asyncio.TaskGroup() as tg:
                for job in range(10):
                    tg.create_task(fetch(job, sem, results))
        return sorted(results)

    results = asyncio.run(skeleton())
    print(f"  10 jobs, budget {budget} : {len(results)} completed, "
          f"peak in flight {peak}")
    print("  TaskGroup owns the lifetimes (Ch 104), the Semaphore owns the")
    print("  budget (Ch 105), the timeout owns the deadline (Ch 104), and")
    print("  every fan-out in production is this skeleton with I/O inside")

    print("--- pattern 2: the hedged race: first wins, losers cancelled ---")
    log: list[str] = []

    async def backend(name, beats):
        try:
            for _ in range(beats):
                await asyncio.sleep(0)
            log.append(f"{name}-answered")
            return name
        except asyncio.CancelledError:
            log.append(f"{name}-cancelled")
            raise

    async def hedged():
        fast = asyncio.create_task(backend("fast", 1))
        slow = asyncio.create_task(backend("slow", 5))
        done, pending = await asyncio.wait(
            {fast, slow}, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        for task in pending:
            try:
                await task
            except asyncio.CancelledError:
                pass
        return done.pop().result()

    winner = asyncio.run(hedged())
    print(f"  winner : {winner}   order : {', '.join(log)}")
    print("  wait(FIRST_COMPLETED) is the race; cancelling the losers is the")
    print("  half everyone forgets, and Chapter 103's contract is why the")
    print("  slow backend's cleanup ran before we moved on")

    print("--- pattern 3: graceful shutdown: stop intake, drain, then cancel ---")
    log.clear()

    async def worker(q):
        while True:
            item = await q.get()
            if item is None:
                log.append("worker-drained")
                return
            await asyncio.sleep(0)
            log.append(f"served-{item}")

    async def server():
        q: asyncio.Queue = asyncio.Queue()
        async with asyncio.TaskGroup() as tg:
            tg.create_task(worker(q))
            for item in range(3):
                await q.put(item)
            log.append("shutdown-requested")
            await q.put(None)            # stop intake, then drain via sentinel
        log.append("group-closed")

    asyncio.run(server())
    print(f"  {', '.join(log)}")
    print("  the sentinel drains in-flight work before the group closes; the")
    print("  cancel-everything hammer (Ch 103) is the fallback for stragglers,")
    print("  behind a timeout - drain first, cancel second, always")

    print("--- the decision, closing Deep J and Chapter 100's table ---")
    print("  is the workload WAITING?   asyncio: 1.4 KB per waiter (Ch 101),")
    print("    determinism (Ch 101), structure (Ch 104), one thread")
    print("  is it COMPUTING?           Deep L's primitives via the bridges")
    print("    (Ch 107), sized by Chapter 100's grain table")
    print("  is it BOTH?                async front absorbs the waiting; the")
    print("    CPU ships over to_thread/executors in BATCHES (Ch 107)")
    print("  the loop is a cheap wait, never a fast thread; nothing on it may")
    print("  block; suspensions are the budget unit (Ch 102); and the")
    print("  interleaving being CODE, not chance, is what you gave up threads")
    print("  to get. Deep J closed: 101 loop, 102 chain, 103 tasks, 104")
    print("  structure, 105 coordination, 106 bytes, 107 bridges, 108 this")


if __name__ == "__main__":
    main()
