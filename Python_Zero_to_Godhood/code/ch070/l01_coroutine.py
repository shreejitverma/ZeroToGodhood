"""Listing 70.1 - generators as coroutines: send, throw, close.

A generator is not only a producer; yield is two-way. `value = yield result`
sends `result` OUT and receives the next `value` IN via .send(). So a generator
becomes a resumable coroutine that keeps its state in local variables across
suspensions, a natural state machine. Two more controls: .close() raises
GeneratorExit at the suspension point (so a try/finally runs cleanup), and
.throw(exc) injects an exception there (so the coroutine can handle it and
continue). This was the foundation asyncio was built on before native async/await.
"""


def running_average():
    """A coroutine: receives numbers via send, yields the running average."""
    total = 0.0
    count = 0
    average = None
    while True:
        value = yield average        # yield current avg OUT, receive next value IN
        total += value
        count += 1
        average = total / count


def worker(events):
    """Records what it processes; its finally runs cleanup when closed."""
    try:
        while True:
            x = yield
            events.append(f"processed {x}")
    finally:
        events.append("cleanup ran on close")


def resilient(events):
    """Handles an injected exception and keeps going."""
    while True:
        try:
            x = yield
            events.append(f"got {x}")
        except ValueError:
            events.append("handled ValueError, continued")


def main() -> None:
    print("--- send: two-way communication, state kept across suspensions ---")
    avg = running_average()
    next(avg)                        # prime: run to the first yield
    print(f"  send 10 -> avg {avg.send(10)}")
    print(f"  send 20 -> avg {avg.send(20)}")
    print(f"  send 30 -> avg {avg.send(30)}")

    print("--- close: GeneratorExit runs the finally (cleanup) ---")
    events = []
    w = worker(events)
    next(w)
    w.send(1)
    w.close()
    print(f"  events: {events}")

    print("--- throw: inject an exception at the suspension point ---")
    events = []
    r = resilient(events)
    next(r)
    r.send(1)
    r.throw(ValueError)
    r.send(2)
    print(f"  events: {events}")


if __name__ == "__main__":
    main()
