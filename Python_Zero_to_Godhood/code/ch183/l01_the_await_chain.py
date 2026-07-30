"""Listing 183.1 - coroutines and awaitables: what `await` actually traverses.

Chapter 101 said the loop sees only callbacks and futures. This chapter is the
machinery between your `async def` and that loop, driven BY HAND: a coroutine
is an inert object until sent; its return value travels inside StopIteration;
`await` is delegation that FLATTENS, so ten layers of coroutines still present
exactly one suspension to the loop; and anything with __await__ can join the
chain. Deep F owns the generator engine underneath; this chapter owns the
awaitable protocol built on it.
"""

import asyncio
import warnings


async def answer():
    return 42


class ManualAwaitable:
    """The protocol, bare: __await__ returns an iterator; each yield suspends;
    the iterator's StopIteration.value is the result of `await`."""

    def __await__(self):
        handed_back = yield "SUSPEND-TOKEN"
        return ("resumed with", handed_back)


async def outer():
    return await middle()


async def middle():
    return await inner()


async def inner():
    return await ManualAwaitable()


def main() -> None:
    print("--- a coroutine is inert until driven ---")
    coro = answer()
    print(f"  calling an async def returns : {type(coro).__name__}")
    try:
        coro.send(None)
    except StopIteration as stop:
        print(f"  send(None) ran the body; the RETURN VALUE rides in "
              f"StopIteration.value : {stop.value}")
    print("  no loop was involved: the loop is a consumer of this protocol,")
    print("  not its owner. Deep F's generators, wearing a contract")

    print("--- the awaitable protocol, driven by hand ---")
    it = ManualAwaitable().__await__()
    token = it.send(None)
    print(f"  first send(None) suspended, yielding : {token!r}")
    try:
        it.send("a-result-from-outside")
    except StopIteration as stop:
        print(f"  resuming with a value finished it    : {stop.value!r}")
    print("  that is the whole contract: yield to suspend, StopIteration.value")
    print("  to return. Futures, Tasks, and sleep() are all spellings of it")

    print("--- await flattens: three layers, ONE suspension ---")
    chain = outer()
    token = chain.send(None)
    print(f"  outer -> middle -> inner -> ManualAwaitable, one send reached")
    print(f"  the bottom and surfaced its token        : {token!r}")
    try:
        chain.send("loop-says-go")
    except StopIteration as stop:
        print(f"  one resume finished ALL THREE layers     : {stop.value!r}")
    print("  await compiles to delegation (Deep F's yield from): the stack of")
    print("  coroutines suspends AS A UNIT and resumes as a unit. depth adds")
    print("  frames, never extra trips through the loop (the benchmark prices")
    print("  the frames)")

    print("--- the failure mode the machinery watches for ---")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        answer()                     # created, never awaited, dropped
        import gc
        gc.collect()
    kinds = {type(w.message).__name__ for w in caught}
    print(f"  create-and-drop a coroutine warns : "
          f"{'RuntimeWarning' in kinds}")
    print("  'coroutine was never awaited': the inert object died undriven,")
    print("  which almost always means a missing await - the async bug that")
    print("  fails silently at the call site and loudly nowhere")

    print("--- what asyncio.run adds ---")
    print(f"  the same coroutine, driven by the loop : "
          f"{asyncio.run(answer())}")
    print("  run() wraps the protocol in a Task (Chapter 103), drives sends")
    print("  from the ready queue, and routes yielded futures to the selector.")
    print("  everything above still happened; it was just automated")


if __name__ == "__main__":
    main()
