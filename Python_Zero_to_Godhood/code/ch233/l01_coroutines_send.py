"""Listing 233.1 - Python 2.5 (2006): yield becomes an expression - generators gain send().

Chapter 226's generators (2.2) were one-directional: values flowed OUT via
yield, and the caller could only pull with next(). Python 2.5's PEP 342 made
`yield` an EXPRESSION that also returns a value - the object passed to the
generator's new .send() method. That single change turned a generator into a
two-way channel: it can yield a value out AND receive one back in at the same
suspension point. A generator you drive by sending values into is a coroutine,
and this is the exact primitive that, followed to its conclusion, becomes
`yield from` (3.3) and then async/await (3.5). Deep F owns the coroutine model;
this is the release where a generator first became something you talk BACK to.
Verified on current interpreters.
"""


def running_average():
    """A coroutine: each value SENT in updates the average yielded back out."""
    total = 0.0
    count = 0
    average = None
    while True:
        value = yield average                    # yield OUT average, receive IN a value
        total += value
        count += 1
        average = total / count


def main() -> None:
    print("--- yield as an expression: value flows OUT and IN at one point ---")
    avg = running_average()
    next(avg)                                    # prime: run up to the first yield
    print(f"  send(10) -> running average : {avg.send(10)}")
    print(f"  send(20) -> running average : {avg.send(20)}")
    print(f"  send(30) -> running average : {avg.send(30)}")
    print("  `value = yield average` yields average OUT and binds the SENT value")
    print("  to `value` IN. that two-way flow at one suspension point is the")
    print("  whole of PEP 342 - a generator you push into, not just pull from")

    print("--- pull (next) vs push (send): the same yield, two directions ---")
    print("  next(g)     == g.send(None)  : pull a value out, send nothing in")
    print("  g.send(x)   : resume with `yield` evaluating to x - push in AND pull")
    print("  a plain generator (Chapter 226) only ever pulled; send() added the")
    print("  push, and 'a generator you push into' is the definition of a")
    print("  coroutine (Deep F)")

    print("--- priming: a coroutine must be advanced to its first yield ---")
    a2 = running_average()
    try:
        a2.send(5)                               # illegal before priming
    except TypeError as exc:
        print(f"  send() before priming raises : TypeError({exc})")
    next(a2)                                      # now primed
    print(f"  after next() primes it, send(5) works : {a2.send(5)}")
    print("  you cannot send into a generator that has not yet reached a yield -")
    print("  there is nowhere for the value to land. hence the priming next(),")
    print("  the wart that @coroutine decorators and later async/await hid away")

    print("--- throw() and close(): the caller also controls the coroutine ---")
    a3 = running_average()
    next(a3)
    a3.send(100)
    a3.close()                                   # inject GeneratorExit, stop it
    try:
        a3.send(1)
    except StopIteration:
        print("  after close(), send() raises StopIteration (coroutine is done)")
    print("  send() is the headline, but PEP 342 also gave throw() (raise INTO")
    print("  the generator) and close() (stop it). the caller now fully drives")
    print("  the coroutine's lifecycle - resume, inject, terminate")

    print("--- the constraint answered ---")
    print("  2.2 generators were a one-way pull: values only came OUT. PEP 342")
    print("  made yield an expression with send(), so values also go IN - a")
    print("  generator became a two-way coroutine you drive. that primitive is")
    print("  the seed of yield from (3.3) and async/await (3.5): async began")
    print("  the day yield learned to receive")


if __name__ == "__main__":
    main()
