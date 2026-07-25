"""Benchmark 70.1 - a generator coroutine costs about the same as a class.

Unlike pure iteration (Chapter 69, where a generator beats a class 2x because the
class pays a __next__ call per item), a coroutine that RECEIVES data pays a call
per item either way: .send() on the generator, or .update() on the class. So they
are about equal. The coroutine's advantage is not speed but EXPRESSIVENESS: state
lives in local variables across suspensions, and cleanup comes free via close().
This measures a running-average accumulator both ways.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
def running_average():
    total = 0.0
    count = 0
    average = None
    while True:
        value = yield average
        total += value
        count += 1
        average = total / count

class Averager:
    def __init__(self):
        self.total = 0.0
        self.count = 0
    def update(self, value):
        self.total += value
        self.count += 1
        return self.total / self.count

def feed_gen():
    avg = running_average()
    next(avg)
    r = None
    for i in range(1000):
        r = avg.send(i)
    return r

def feed_class():
    a = Averager()
    r = None
    for i in range(1000):
        r = a.update(i)
    return r
"""


def main() -> None:
    results = [
        measure("class (update method)", "feed_class()", SETUP, number=20000),
        measure("generator coroutine (send)", "feed_gen()", SETUP, number=20000),
    ]
    report("70.1  running-average accumulator: coroutine vs class",
           results, baseline="class (update method)")

    print()
    print("Reading this. Sending 1000 values into a generator coroutine costs about")
    print("the same as calling a class's update method 1000 times, because both pay")
    print("one call per value. So the choice is not about speed. The coroutine's")
    print("value is expressiveness: its state (total, count) lives in plain local")
    print("variables preserved across each yield, and its try/finally gives")
    print("automatic cleanup on close, no explicit state object or teardown method")
    print("needed. Use a coroutine for a naturally sequential state machine; use a")
    print("class when the state must be an object with a broader interface.")


if __name__ == "__main__":
    main()
