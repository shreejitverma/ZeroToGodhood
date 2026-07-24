"""Listing 11.2 - async for and async with, for when advancing an iterator or
acquiring a resource is itself I/O.

async for drives the async iterator protocol: __aiter__ returns an async
iterator, __anext__ is a coroutine returning the next item or raising
StopAsyncIteration. async with drives __aenter__/__aexit__, both coroutines, so
acquiring or releasing a connection can await. Async comprehensions followed in
3.6 (PEP 530).
"""

import asyncio


class AsyncRange:
    def __init__(self, n):
        self.n, self.i = n, 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.i >= self.n:
            raise StopAsyncIteration
        self.i += 1
        return self.i - 1


class AsyncCtx:
    async def __aenter__(self):
        print("  __aenter__ (awaitable acquire)")
        return self

    async def __aexit__(self, *exc):
        print("  __aexit__ (awaitable release)")


async def demo():
    collected = [x async for x in AsyncRange(3)]      # async comprehension (PEP 530)
    async with AsyncCtx():
        print("  inside async with")
    return collected


print("--- async iteration and an async context manager ---")
print("  collected:", asyncio.run(demo()))
print()
print("These are the building blocks for async database cursors, streaming HTTP")
print("bodies, and async connection pools: anywhere 'get the next item' or 'open")
print("the resource' must await I/O.")
