"""Benchmark 136.1 - a function call is not free: it builds a frame.

Every Python call creates a frame (Chapter 54): allocate it, bind the arguments to its
locals, run, and tear it down on return. That is real per-call overhead. This measures
it two ways: the same work done via a per-iteration function call versus inlined, and
the pure overhead of calling an empty function versus an empty loop iteration.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 20_000
LOOP = 1000


def square(x):
    return x * x


def noop():
    pass


def with_calls():
    s = 0
    for i in range(LOOP):
        s += square(i)          # a call (a frame) per iteration
    return s


def inlined():
    s = 0
    for i in range(LOOP):
        s += i * i              # same work, no call, no frame
    return s


def call_loop():
    for _ in range(LOOP):
        noop()                  # pure call overhead


def empty_loop():
    for _ in range(LOOP):
        pass


def main():
    print("=== 136.1  function call overhead: per-call frame cost ===")
    print(provenance())
    print()

    t_call = min(timeit.repeat(with_calls, number=N, repeat=5)) / N
    t_inline = min(timeit.repeat(inlined, number=N, repeat=5)) / N
    t_c = min(timeit.repeat(call_loop, number=N, repeat=5)) / N
    t_e = min(timeit.repeat(empty_loop, number=N, repeat=5)) / N

    per_call = (t_c - t_e) / LOOP

    print(f"  same work, per-iteration call : {t_call * 1e6:5.1f} us")
    print(f"  same work, inlined            : {t_inline * 1e6:5.1f} us   ({t_call / t_inline:.2f}x)")
    print(f"  pure call overhead (noop vs pass) : ~{per_call * 1e9:.0f} ns per call")

    print()
    print("Reading this. A per-iteration function call is ~1.5x the inlined work, and")
    print("the pure overhead of calling an empty function is a few nanoseconds, the")
    print("cost of building a frame (Chapter 54): allocate it, bind arguments to its")
    print("locals, and tear it down on return. That is negligible for a normal call")
    print("but adds up when a trivial function is called millions of times in a hot")
    print("loop. The lesson is NOT 'inline everything', clarity and reuse matter far")
    print("more than a few nanoseconds. It is: in a measured hot path, reducing call")
    print("depth (or vectorizing so one call does the whole loop, Deep T) removes real")
    print("overhead, and it is one reason a Python element loop loses to NumPy, which")
    print("crosses into C once for the whole array instead of calling per element.")


if __name__ == "__main__":
    main()
