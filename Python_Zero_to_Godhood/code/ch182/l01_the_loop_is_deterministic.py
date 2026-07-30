"""Listing 182.1 - the event loop: cooperative, single-threaded, and deterministic.

Deep J opens with the property that separates asyncio from every concurrency
primitive in Deep E and Deep L: the interleaving is DETERMINISTIC. A thread
scheduler may switch anywhere; the event loop switches only where the code
says `await`, so the execution order of this listing is exactly reproducible,
on every run, on every interpreter in the matrix - which is why this file can
be verified byte-for-byte at all.

Four facts: tasks interleave only at await points; a coroutine that does not
await starves everyone (cooperative means it); ready callbacks run FIFO; and
`await asyncio.sleep(0)` is the explicit "let others run" edge.
"""

import asyncio


def main() -> None:
    log: list[str] = []

    print("--- interleaving happens exactly at await points ---")

    async def ping_pong(name, beats):
        for i in range(beats):
            log.append(f"{name}{i}")
            await asyncio.sleep(0)          # yield to the loop

    async def scenario():
        async with asyncio.TaskGroup() as tg:
            tg.create_task(ping_pong("a", 3))
            tg.create_task(ping_pong("b", 3))

    asyncio.run(scenario())
    print(f"  two tasks, three beats each : {', '.join(log)}")
    print("  perfect alternation, every run: the loop resumes ready tasks in")
    print("  order, and each one runs EXACTLY until its next await. schedule is")
    print("  code, not chance - the property threads can never offer (Ch 99)")

    print("--- a task that does not await starves the loop ---")
    log.clear()

    async def hog():
        for i in range(3):
            log.append(f"hog{i}")            # no await: nobody else runs

    async def polite():
        log.append("polite")

    async def starvation():
        async with asyncio.TaskGroup() as tg:
            tg.create_task(hog())
            tg.create_task(polite())

    asyncio.run(starvation())
    print(f"  hog first, no awaits inside : {', '.join(log)}")
    print("  the hog finished before polite ran at all: 'async' grants no")
    print("  preemption, and one loop iteration runs one task until IT yields.")
    print("  blocking the loop blocks every task on it (Chapter 107)")

    print("--- the ready queue is FIFO, and call_soon shows it raw ---")
    log.clear()

    async def callbacks():
        loop = asyncio.get_running_loop()
        for name in ("first", "second", "third"):
            loop.call_soon(log.append, name)
        await asyncio.sleep(0)               # let the queued callbacks drain
        log.append("after-sleep(0)")

    asyncio.run(callbacks())
    print(f"  call_soon x3, then sleep(0) : {', '.join(log)}")
    print("  callbacks queued while a task runs execute in queue order at the")
    print("  next iteration; sleep(0) parked the task BEHIND them. one queue,")
    print("  strictly FIFO per iteration: that is the whole scheduler")

    print("--- what one loop iteration is ---")
    print("  1  compute the poll timeout from the nearest timer")
    print("  2  poll the selector: which fds are ready (Chapter 106)")
    print("  3  queue the callbacks those fds unblocked, and any due timers")
    print("  4  drain the ready queue, FIFO, each entry running to its yield")
    print("  everything in this volume - tasks, futures, streams, timeouts -")
    print("  compiles down to entries in step 4's queue")


if __name__ == "__main__":
    main()
