"""Listing 21.2 - the reason exception groups exist: asyncio.TaskGroup.

TaskGroup (3.11, PEP 654's motivating use) runs several tasks concurrently and,
if more than one fails, raises an ExceptionGroup carrying ALL the failures rather
than discarding all but one. except* then routes them by category. This is
structured concurrency: the group is the unit, and its failures are collected,
not lost.
"""

import asyncio


async def failing(name, exc_type):
    await asyncio.sleep(0.01)
    raise exc_type(name)


async def main():
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(failing("db", ConnectionError))
            tg.create_task(failing("cache", TimeoutError))
            tg.create_task(failing("api", ValueError))
    except* ConnectionError as e:
        print("  infra failures :", sorted(str(x) for x in e.exceptions))
    except* (TimeoutError, ValueError) as e:
        print("  other failures :", sorted(str(x) for x in e.exceptions))


print("--- three tasks fail concurrently; all three are preserved ---")
asyncio.run(main())

print()
print("--- the pre-3.11 alternative: gather(return_exceptions=True) ---")


async def with_gather():
    results = await asyncio.gather(
        failing("a", ValueError), failing("b", TypeError), return_exceptions=True
    )
    print("  gather collects into a list:", sorted(type(r).__name__ for r in results))


asyncio.run(with_gather())
print()
print("gather(return_exceptions=True) also collects all failures, but as a flat")
print("list you must inspect by hand; it does not cancel siblings on the first")
print("failure and has no structured propagation. TaskGroup cancels the")
print("remaining tasks when one fails and raises a typed, routable group.")
