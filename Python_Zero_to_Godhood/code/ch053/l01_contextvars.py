"""Listing 53.1 - contextvars: per-context state that survives async interleaving.

Concurrent async tasks share one thread and interleave at every await. A module
global written before an await is clobbered by other tasks that run during the
await, so per-request state kept in a global gets corrupted. A ContextVar gives
each logical context (each Task) its own value, set in one task is not visible in
another, so it is the correct home for request-scoped state (request id, user,
trace context) in async code. threading.local does not help here: async tasks
share a thread, so they share the same thread-local. This listing shows the
contrast, and it is deterministic (gather preserves order, equal sleeps).
"""

import asyncio
import contextvars

request_id = contextvars.ContextVar("request_id")
_global = {"rid": None}


async def handle_with_contextvar(rid):
    request_id.set(rid)               # this task's own context
    await asyncio.sleep(0.001)        # other tasks run during this await
    return request_id.get()           # still THIS task's rid


async def handle_with_global(rid):
    _global["rid"] = rid              # shared mutable global
    await asyncio.sleep(0.001)        # other tasks overwrite _global here
    return _global["rid"]             # whatever ran last


async def run_all(handler):
    return await asyncio.gather(*(handler(i) for i in range(5)))


def main() -> None:
    ctx_results = asyncio.run(run_all(handle_with_contextvar))
    glob_results = asyncio.run(run_all(handle_with_global))

    print("--- ContextVar: each task keeps its own value across the await ---")
    print(f"  results             : {ctx_results}")
    print(f"  each task saw its own rid : {ctx_results == [0, 1, 2, 3, 4]}")

    print("--- module global: clobbered by interleaving (all see the last write) ---")
    print(f"  results             : {glob_results}")
    print(f"  corrupted?          : {len(set(glob_results)) == 1} (all tasks saw the same rid)")

    print("--- the rule ---")
    print(f"  request-scoped state in async code -> ContextVar, not a global or")
    print(f"  threading.local (async tasks share a thread, so they share both)")


if __name__ == "__main__":
    main()
