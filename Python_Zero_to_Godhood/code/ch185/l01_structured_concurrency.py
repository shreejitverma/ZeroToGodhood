"""Listing 185.1 - structured concurrency: the group owns its children.

Chapter 103's Tasks are powerful and unowned: any code can spawn one, hold or
drop it, and its failure surfaces wherever (or never). Structured concurrency
is the discipline that closed that hole in 3.11: a TaskGroup owns every task
created within it, its `async with` does not exit until all children finish,
one child's failure cancels the siblings, and ALL failures arrive together as
an ExceptionGroup, matched with `except*`. Timeouts join the model through
asyncio.timeout, which converts the cancellation it injects into TimeoutError
at its own boundary, using Chapter 103's uncancel bookkeeping.

Every order shown is deterministic: the same scheduling rules as Chapter 101,
so the lifecycle claims are verified, not narrated.
"""

import asyncio


def main() -> None:
    log: list[str] = []

    print("--- the group waits for every child ---")

    async def child(name, beats):
        for _ in range(beats):
            await asyncio.sleep(0)
        log.append(f"{name}-done")
        return name

    async def happy():
        async with asyncio.TaskGroup() as tg:
            a = tg.create_task(child("a", 1))
            b = tg.create_task(child("b", 3))
        log.append("group-exited")
        return a.result(), b.result()

    results = asyncio.run(happy())
    print(f"  order   : {', '.join(log)}")
    print(f"  results : {results}")
    print("  the async with block refused to exit until the slower child")
    print("  finished: children cannot outlive their block, so there are no")
    print("  orphans to hold references to (Chapter 103's first edge, solved)")

    print("--- one failure cancels the siblings ---")
    log.clear()

    async def slow_sibling():
        try:
            log.append("sibling-waiting")
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            log.append("sibling-cancelled")
            raise

    async def failer():
        await asyncio.sleep(0)
        log.append("failer-raises")
        raise ValueError("boom")

    async def one_fails():
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(slow_sibling())
                tg.create_task(failer())
        except* ValueError as group:
            log.append(f"caught-group-of-{len(group.exceptions)}")

    asyncio.run(one_fails())
    print(f"  order : {', '.join(log)}")
    print("  the failure did not leak past the block, and it did not leave the")
    print("  sibling running: cancellation of the group is the ERROR PATH, and")
    print("  it uses Chapter 103's contract (the sibling re-raised, honestly)")

    print("--- multiple failures arrive TOGETHER ---")
    log.clear()

    async def fail_with(exc_type, msg):
        await asyncio.sleep(0)
        raise exc_type(msg)

    async def two_fail():
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(fail_with(ValueError, "bad-value"))
                tg.create_task(fail_with(KeyError, "bad-key"))
        except* ValueError as g:
            log.append(f"values: {[str(e) for e in g.exceptions]}")
        except* KeyError as g:
            log.append(f"keys: {[str(e) for e in g.exceptions]}")

    asyncio.run(two_fail())
    print(f"  {log[0]}")
    print(f"  {log[1]}")
    print("  gather(return_exceptions=False) reports only the FIRST failure;")
    print("  a TaskGroup collects every failure into one ExceptionGroup, and")
    print("  except* runs each matching handler against its selection")

    print("--- timeout: cancellation converted at its own boundary ---")
    log.clear()

    async def patient():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            log.append("worker-sees-CancelledError")
            raise

    async def bounded():
        try:
            async with asyncio.timeout(0.01):
                await patient()
        except TimeoutError:
            log.append("caller-sees-TimeoutError")

    asyncio.run(bounded())
    print(f"  order : {', '.join(log)}")
    print("  inside the boundary the mechanism is ordinary cancellation")
    print("  (Chapter 103); at the boundary, asyncio.timeout recognises ITS")
    print("  OWN cancellation via the uncancel counter and converts it to")
    print("  TimeoutError. an outside cancel arriving at the same moment")
    print("  still propagates as CancelledError - the counter is what makes")
    print("  the two distinguishable")


if __name__ == "__main__":
    main()
