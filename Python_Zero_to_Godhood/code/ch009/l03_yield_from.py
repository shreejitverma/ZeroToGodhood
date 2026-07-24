"""Listing 9.3 - yield from delegates transparently and captures the return.

Before 3.3, a generator that wanted to yield everything from a sub-generator AND
forward send/throw/close and capture the sub-generator's return value had to
hand-write a fragile loop. PEP 380's yield from makes the delegating generator a
transparent channel: yielded values pass out, sent values pass in, thrown
exceptions raise inside the sub-generator, and the sub-generator's return value
becomes the value of the yield-from expression (via StopIteration.value).
"""


def subgen():
    received = yield "a"
    yield f"got {received}"
    return "subgen-result"


def delegator():
    result = yield from subgen()       # transparent channel; captures the return
    print("  delegator captured return:", result)
    yield "after"


print("--- yield from routes send() into the sub-generator and captures return ---")
d = delegator()
print("  next(d)   :", next(d))         # "a" from subgen
print("  d.send('X'):", d.send("X"))    # "X" routed into subgen -> "got X"
print("  next(d)   :", next(d))         # subgen returns; result captured; -> "after"


def flatten(nested):
    for item in nested:
        if isinstance(item, list):
            yield from flatten(item)
        else:
            yield item


print()
print("--- the everyday use: composition without manual loops ---")
print("  flatten([1,[2,[3,4],5],6]):", list(flatten([1, [2, [3, 4], 5], 6])))
print()
print("When you read `await expr` in Chapter 11, picture yield from with a")
print("typed, awaitable-only channel: the suspension mechanism is identical.")
