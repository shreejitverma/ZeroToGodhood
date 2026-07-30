"""Listing 184.1 - Tasks, Futures, and the anatomy of cancellation.

A Task is a Future with a driver attached: it wraps a coroutine, feeds it
`send` from the ready queue, and routes every future the chain yields to the
loop's watching machinery (Chapter 102 built the chain; Chapter 101 the queue).
This listing pins down the Task's contract with deterministic order proofs:
when the body starts (next iteration - unless the eager factory is installed),
what being a Future buys (many awaiters, one result), and exactly how
cancellation travels (a CancelledError THROWN INTO the coroutine at its
suspension point, catchable, shieldable, and suppressible - with the
suppression being the trap).
"""

import asyncio


def main() -> None:
    log: list[str] = []

    print("--- a task starts on the NEXT iteration, not at create_task ---")

    async def child():
        log.append("child-runs")
        return "payload"

    async def default_start():
        task = asyncio.create_task(child())
        log.append("after-create")
        await asyncio.sleep(0)
        log.append("after-yield")
        await task

    asyncio.run(default_start())
    print(f"  default factory : {', '.join(log)}")

    log.clear()

    async def eager_start():
        asyncio.get_running_loop().set_task_factory(asyncio.eager_task_factory)
        task = asyncio.create_task(child())
        log.append("after-create")
        await task

    asyncio.run(eager_start())
    print(f"  eager factory   : {', '.join(log)}")
    print("  by default create_task only QUEUES the first send; the eager")
    print("  factory (3.12+) runs the body synchronously to its first await,")
    print("  which skips a loop trip for tasks that complete immediately")

    print("--- a Task is a Future: many awaiters, one result ---")

    async def shared_result():
        task = asyncio.create_task(child())
        first, second = await task, await task
        watchers = await asyncio.gather(task, task)
        return first == second == "payload" and watchers == ["payload"] * 2

    print(f"  awaited the same task four times, one execution : "
          f"{asyncio.run(shared_result())}")
    print("  the coroutine ran once (the log would show it); the Task caches")
    print("  the outcome as Future state, which raw coroutines cannot (Ch 102)")

    print("--- the anatomy of cancel() ---")
    log.clear()

    async def worker():
        try:
            log.append("working")
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            log.append("CancelledError-at-await")
            raise                     # the contract: clean up, then re-raise
        finally:
            log.append("finally-ran")

    async def cancel_it():
        task = asyncio.create_task(worker())
        await asyncio.sleep(0)        # let it reach its await
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            log.append("awaiter-sees-it")
        log.append(f"cancelled()={task.cancelled()}")

    asyncio.run(cancel_it())
    print(f"  {', '.join(log)}")
    print("  cancel() arranges a CancelledError to be THROWN at the task's")
    print("  current await; try/finally and context managers run normally on")
    print("  the way out; re-raising marks the task cancelled")

    print("--- the suppression trap ---")
    log.clear()

    async def swallower():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            log.append("caught-and-swallowed")
        return "i-pretend-nothing-happened"

    async def cancel_swallower():
        task = asyncio.create_task(swallower())
        await asyncio.sleep(0)
        task.cancel()
        result = await task           # no CancelledError reaches us!
        log.append(f"result={result}")
        log.append(f"cancelled()={task.cancelled()}")

    asyncio.run(cancel_swallower())
    print(f"  {', '.join(log)}")
    print("  swallowing CancelledError makes cancellation LIE: the canceller")
    print("  believes it worked, cancelled() says False, and Chapter 104's")
    print("  TaskGroup timeouts depend on the error completing its journey")

    print("--- shield: cancelling the wait, not the work ---")

    async def precious():
        await asyncio.sleep(0.01)
        return "committed"

    async def shielded():
        inner = asyncio.create_task(precious())
        try:
            await asyncio.wait_for(asyncio.shield(inner), timeout=0.001)
        except TimeoutError:
            pass                      # OUR wait timed out...
        return await inner            # ...but the work survived

    print(f"  wait_for timed out, shielded task still : "
          f"{asyncio.run(shielded())!r}")
    print("  shield(x) cancels the shield, not x: for work that must not be")
    print("  half-done (a commit, a payment), the timeout abandons the WAIT")
    print("  and the caller decides what awaiting the survivor means")


if __name__ == "__main__":
    main()
