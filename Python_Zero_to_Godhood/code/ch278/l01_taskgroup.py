"""Listing 278.1 - Python 3.11 (2022): asyncio.TaskGroup, structured concurrency.

Running several coroutines concurrently with asyncio.gather() had a nasty gap: if
one task failed, the OTHERS kept running (orphaned), and error handling was
awkward. 'Structured concurrency' fixes this: concurrent tasks live inside a
scope, and the scope does not exit until every task finishes - and if any task
fails, the rest are cancelled and the errors are reported together. Python 3.11's
asyncio.TaskGroup is that scope: an `async with` block you create tasks in; it
awaits them all at block end, and on failure cancels the siblings and raises an
ExceptionGroup (Chapter 21). Deep H owns the asyncio model; this is the release
that gave concurrent tasks a scope with no orphans. This listing awaits fixed
work with no real delays, so its output is deterministic. Verified on current
interpreters.
"""

import asyncio


async def fetch(name, value):
    await asyncio.sleep(0)                        # yield control; no real delay
    return f"{name}={value}"


async def flaky(name):
    await asyncio.sleep(0)
    raise ValueError(f"{name} failed")


async def happy_path():
    results = {}
    async with asyncio.TaskGroup() as tg:         # the concurrency SCOPE
        t1 = tg.create_task(fetch("a", 1))
        t2 = tg.create_task(fetch("b", 2))
        t3 = tg.create_task(fetch("c", 3))
    # the block only exits once ALL tasks are done - results are ready here
    return [t1.result(), t2.result(), t3.result()]


async def failure_path():
    cancelled = {"count": 0}

    async def cancellable(name):
        try:
            await asyncio.sleep(3600)             # would run forever...
        except asyncio.CancelledError:
            cancelled["count"] += 1               # ...but gets cancelled
            raise

    outcome = "no error"
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(cancellable("sibling-1"))
            tg.create_task(cancellable("sibling-2"))
            tg.create_task(flaky("worker"))       # this one fails
    except* ValueError as eg:                     # ExceptionGroup, caught with except*
        outcome = (f"caught {len(eg.exceptions)} ValueError(s); "
                   f"siblings cancelled = {cancelled['count']}")
    return outcome


def main() -> None:
    print("--- a TaskGroup runs tasks concurrently and awaits them all ---")
    results = asyncio.run(happy_path())
    print(f"  results after the `async with` block : {results}")
    print("  create_task() schedules each coroutine in the group; the `async")
    print("  with` block does not exit until EVERY task has finished. so after")
    print("  the block, all results are guaranteed ready - no manual gather/await")

    print("--- the scope guarantees completion: no orphaned tasks ---")
    print("  unlike firing tasks and forgetting them, a TaskGroup task cannot")
    print("  outlive its block. the scope is the lifetime: enter, spawn, and on")
    print("  exit every task is done (or cancelled). that is 'structured")
    print("  concurrency' - tasks nest in scopes like blocks nest in code")

    print("--- on failure, siblings are cancelled and errors grouped ---")
    outcome = asyncio.run(failure_path())
    print(f"  {outcome}")
    print("  when 'worker' raised, the TaskGroup CANCELLED the two siblings")
    print("  (which would have run for an hour) and raised an ExceptionGroup.")
    print("  no task is left running after a failure - the orphan problem gather")
    print("  had is gone")

    print("--- errors come as an ExceptionGroup, handled with except* ---")
    print("  a TaskGroup can fail with SEVERAL errors at once (multiple tasks),")
    print("  so it raises an ExceptionGroup and you catch by type with `except*`")
    print("  (Chapter 21). one worker failing gave one ValueError in the group;")
    print("  many failing would give many, each catchable by its type")

    print("--- the constraint answered ---")
    print("  gather() let a failed task orphan its siblings and made errors")
    print("  awkward. asyncio.TaskGroup (3.11) makes concurrent tasks a SCOPE:")
    print("  the `async with` block awaits them all, cancels siblings if one")
    print("  fails, and reports errors as an ExceptionGroup. concurrent tasks got")
    print("  the same lifetime discipline as a code block - structured concurrency")


if __name__ == "__main__":
    main()
