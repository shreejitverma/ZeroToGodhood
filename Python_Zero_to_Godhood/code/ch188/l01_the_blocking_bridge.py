"""Listing 188.1 - blocking code, the loop, and the bridges between the worlds.

Chapter 101's clause - nothing on the loop may block - meets the real world:
most of Python's libraries are synchronous. This listing proves the failure
and the fix with EVENT-BASED order proofs (no timing, so the output is
deterministic): a blocking call on the loop freezes even already-queued
callbacks until it returns; the same call through asyncio.to_thread leaves
the loop live. Then the return bridges: to_thread propagates results,
exceptions, and contextvars; and threads re-enter the loop's world only
through run_coroutine_threadsafe / call_soon_threadsafe.
"""

import asyncio
import contextvars
import threading


def main() -> None:
    print("--- a blocking call freezes the loop, provably ---")
    log: list[str] = []

    def blocking_work(gate: threading.Event):
        # Waits for a signal that only a LIVE loop can send.
        released = gate.wait(timeout=0.5)
        log.append("work-done" if released else "work-TIMED-OUT-unreleased")

    async def on_loop():
        gate = threading.Event()
        loop = asyncio.get_running_loop()
        loop.call_soon(lambda: (log.append("callback-ran"), gate.set()))
        log.append("calling-blocking-work-ON-THE-LOOP")
        blocking_work(gate)          # the loop is stalled right here

    asyncio.run(on_loop())
    print(f"  {', '.join(log)}")
    print("  the callback was ALREADY QUEUED, and it still could not run: the")
    print("  blocking call owns the loop's only thread, so the gate it waits")
    print("  for can never open. every deadlock of this family is this shape")

    log.clear()

    async def off_loop():
        gate = threading.Event()
        loop = asyncio.get_running_loop()
        loop.call_soon(lambda: (log.append("callback-ran"), gate.set()))
        log.append("sending-blocking-work-to-a-thread")
        await asyncio.to_thread(blocking_work, gate)

    asyncio.run(off_loop())
    print(f"  {', '.join(log)}")
    print("  same code, one to_thread: the loop stayed live, ran the callback,")
    print("  opened the gate, and the worker finished. to_thread is the")
    print("  default bridge for any synchronous call you do not control")

    print("--- the bridge carries results, exceptions, and context ---")

    request_id = contextvars.ContextVar("request_id", default="unset")

    def sync_library_call(x):
        if x < 0:
            raise ValueError("negative")
        return x * 2, request_id.get()

    async def carries():
        request_id.set("req-7")
        value, seen_ctx = await asyncio.to_thread(sync_library_call, 21)
        try:
            await asyncio.to_thread(sync_library_call, -1)
        except ValueError as exc:
            caught = str(exc)
        return value, seen_ctx, caught

    value, seen_ctx, caught = asyncio.run(carries())
    print(f"  return value        : {value}")
    print(f"  contextvar in thread: {seen_ctx!r}")
    print(f"  exception surfaced  : ValueError({caught!r})")
    print("  to_thread copies the current context (Chapter 103's rule applies)")
    print("  and re-raises in the awaiting task: the seam is airtight in both")
    print("  directions, which run_in_executor alone does not give you")

    print("--- threads re-enter the loop through exactly two doors ---")
    log.clear()

    async def two_doors():
        loop = asyncio.get_running_loop()
        started = threading.Event()

        async def loop_side_work(tag):
            log.append(f"coro-ran-{tag}")
            return tag.upper()

        def worker():
            started.wait()
            loop.call_soon_threadsafe(log.append, "door1-callback")
            future = asyncio.run_coroutine_threadsafe(
                loop_side_work("door2"), loop)
            log.append(f"door2-returned-{future.result(timeout=1)}")

        t = threading.Thread(target=worker)
        t.start()
        started.set()
        await asyncio.to_thread(t.join)

    asyncio.run(two_doors())
    print(f"  {', '.join(log)}")
    print("  call_soon_threadsafe posts a callback and wakes the selector;")
    print("  run_coroutine_threadsafe submits a whole coroutine and hands the")
    print("  thread a concurrent.futures.Future to block on. everything else")
    print("  in asyncio is single-threaded machinery (Chapter 105) - these")
    print("  two doors are the entire legal interface")


if __name__ == "__main__":
    main()
