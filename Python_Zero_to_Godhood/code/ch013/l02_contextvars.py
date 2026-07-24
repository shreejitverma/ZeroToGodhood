"""Listing 13.2 - the bug thread-locals cause in async, and the contextvar fix.

threading.local isolates state per OS thread. That is exactly wrong for asyncio,
where many tasks share one thread: task A sets a thread-local, awaits, task B
runs on the same thread and clobbers it. Context variables isolate state per
logical context (per task) and survive await suspensions correctly.

The output below is the whole point: with threading.local, three concurrent
"requests" all report the SAME id (the last one to set it), because they share
one thread-local on one thread. With a ContextVar, each keeps its own.
"""

import asyncio
import contextvars
import threading

# --- the bug: threading.local shared across tasks on one loop thread ---
_tl = threading.local()


async def with_threadlocal(rid):
    _tl.value = rid
    await asyncio.sleep(0.01)             # yield; another task runs and overwrites _tl.value
    return _tl.value


async def run_threadlocal():
    return await asyncio.gather(
        with_threadlocal("req-A"),
        with_threadlocal("req-B"),
        with_threadlocal("req-C"),
    )


# --- the fix: a ContextVar, isolated per task ---
request_id = contextvars.ContextVar("request_id", default="none")


async def with_contextvar(rid):
    request_id.set(rid)
    await asyncio.sleep(0.01)
    return request_id.get()               # still this task's own value


async def run_contextvar():
    return await asyncio.gather(
        with_contextvar("req-A"),
        with_contextvar("req-B"),
        with_contextvar("req-C"),
    )


print("--- threading.local in async: state LEAKS between tasks ---")
print("  three concurrent requests report:", asyncio.run(run_threadlocal()))
print("  every one sees the last id set; A and B were clobbered.")
print()
print("--- contextvars: each task keeps its own value across await ---")
print("  three concurrent requests report:", asyncio.run(run_contextvar()))
print()
print("A ContextVar holds its variables in an immutable HAMT (a persistent map).")
print("set() produces a new trie root sharing all unchanged branches, so saving")
print("and restoring a task's whole context at an await is an O(1) pointer swap.")
print("This is how structured logging correlates a request id through an async")
print("call tree without threading it through every signature.")
