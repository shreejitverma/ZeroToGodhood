"""Listing 11.1 - async def produces a distinct coroutine type, not a generator.

Through 3.4 a coroutine WAS a generator, so you could accidentally for-loop over
it or step it with next() outside the event loop, and yield from meant two
different things. PEP 492 (3.5) split them: async def produces a PyCoroObject
that has __await__ but NOT the iterator protocol, so misusing it is now a clean
error instead of confusing behavior.
"""

import asyncio


async def get_val():
    return 42


c = get_val()                                  # does NOT run the body; returns a coroutine
print("--- a coroutine is a distinct, non-iterable type ---")
print("  type(get_val())     :", type(c).__name__)
print("  has __await__       :", hasattr(c, "__await__"))
print("  has __next__        :", hasattr(c, "__next__"))
try:
    for _ in c:                                # the 3.4 danger, now a clean error
        pass
except TypeError as exc:
    print("  for-loop over it    ->", type(exc).__name__ + ":", exc)
c.close()

print()
print("--- calling it runs nothing until a loop drives it ---")
print("  asyncio.run(get_val()):", asyncio.run(get_val()))

print()
print("--- await accepts any awaitable: implement __await__ yourself ---")


class Delayed:
    def __init__(self, value):
        self.value = value

    def __await__(self):
        yield                 # suspend once, handing control to the event loop
        return self.value


async def use_awaitable():
    return await Delayed("custom-result")


print("  await Delayed(...)  :", asyncio.run(use_awaitable()))
print()
print("await compiles to GET_AWAITABLE + a SEND/YIELD_VALUE loop, the 3.11+")
print("successor to yield from. The suspension is still the heap frame from")
print("Chapter 5: await saves the frame, yields to the loop, resumes on")
print("completion.")
