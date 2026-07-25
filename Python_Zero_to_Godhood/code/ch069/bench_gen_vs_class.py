"""Benchmark 69.1 - a generator is faster than a hand-written iterator class.

Both produce the same 0..n-1 sequence, but they cost differently to consume. The
class's __next__ is a Python METHOD called once per item, so each value pays
Python-level call dispatch. The generator resumes a suspended frame in C on each
next(), with no per-item Python method call. So the generator is the faster (and
shorter) way to implement the same iterator.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
class CountIter:
    def __init__(self, n):
        self.i = 0
        self.n = n
    def __iter__(self):
        return self
    def __next__(self):
        if self.i >= self.n:
            raise StopIteration
        v = self.i
        self.i += 1
        return v

def count_gen(n):
    i = 0
    while i < n:
        yield i
        i += 1

def consume(it):
    total = 0
    for x in it:
        total += x
    return total
"""


def main() -> None:
    results = [
        measure("generator function", "consume(count_gen(1000))", SETUP, number=20000),
        measure("hand-written iterator class", "consume(CountIter(1000))", SETUP, number=20000),
    ]
    report("69.1  consuming 1000 items: generator vs iterator class",
           results, baseline="generator function")

    print()
    print("Reading this. The iterator class pays a Python __next__ method call per")
    print("item; the generator resumes a suspended frame in C with no per-item")
    print("Python call, so it is faster (about 2x here) and far shorter to write.")
    print("Prefer a generator function (or generator expression) to a hand-written")
    print("__iter__/__next__ class for producing a sequence; reserve the class only")
    print("when the iterator needs rich state, methods, or to be an object with")
    print("more than iteration.")


if __name__ == "__main__":
    main()
