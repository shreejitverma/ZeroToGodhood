"""Listing 71.1 - yield from: transparent delegation to a sub-generator.

`yield from subgen` delegates to subgen: it forwards every yielded value to the
caller, AND it establishes a transparent two-way channel, send() and throw() from
the caller go straight to subgen, close() closes it, and subgen's RETURN value
becomes the value of the yield-from expression. A manual `for x in subgen: yield x`
loop forwards VALUES but breaks everything else: it does not forward send() to
subgen (the sent value hits the wrapper's own yield and is lost), and it discards
subgen's return value. For plain producers the two look alike; for coroutines and
return values, only yield from is correct. This listing shows the differences.
"""


def leaf_returns():
    yield 1
    yield 2
    return "the sub-generator's result"


def echo(events):
    while True:
        x = yield
        events.append(f"echo received {x}")


def main() -> None:
    print("--- yield from captures the sub-generator's return value ---")
    def parent():
        result = yield from leaf_returns()   # result = what leaf_returns returns
        yield f"result was: {result}"
    print(f"  {list(parent())}")

    print("--- yield from forwards send() to the sub-generator ---")
    events = []
    def yf_wrapper():
        yield from echo(events)
    w = yf_wrapper()
    next(w)                 # prime (runs into echo's first yield)
    w.send("A")
    w.send("B")
    print(f"  yield from : {events}")

    print("--- a manual re-yield loop does NOT forward send (values are lost) ---")
    events2 = []
    def manual_wrapper():
        for x in echo(events2):   # the sub-generator's yields come here...
            yield x               # ...and we re-yield; send() hits THIS yield, not echo
    m = manual_wrapper()
    next(m)
    m.send("A")
    m.send("B")
    print(f"  manual loop: {events2}  (echo never received the sent values)")

    print("--- yield from flattens a nested structure cleanly ---")
    def flatten(items):
        for item in items:
            if isinstance(item, list):
                yield from flatten(item)     # delegate to the recursive call
            else:
                yield item
    print(f"  flatten([1,[2,[3,4]],5]) : {list(flatten([1, [2, [3, 4]], 5]))}")


if __name__ == "__main__":
    main()
