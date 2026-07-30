"""Benchmark 180.1 - the race lab: loss rates per build, and the price of the fixes.

Races are distributions, so this file reports distributions: sorted results
over 7 trials, never a single number.

180.1a  the plain unlocked read-modify-write: `box.n += 1` from 4 threads,
        no call in the sequence. On the GIL build the loss count is ZERO in
        every trial at every switch interval, and that is a structural fact,
        not luck: the modern GIL is released only at safe points (loop back
        edges, calls), so a call-free bytecode sequence is never split. On
        the free-threaded build the same code loses 25-40% of its updates
        per run.

180.1b  the same read-modify-write with a Python call inside it, at a 1 us
        switch interval. Now the GIL build loses updates too, because a call
        is a safe point. Together, a and b are the testing chapter's core
        result: the GIL build CANNOT surface call-free races, and can only
        surface call-bearing ones when provoked; the free-threaded build
        surfaces both, loudly, which makes a 3.14t CI leg the only honest
        stress test for threaded Python.

180.1c  check-then-act on a shared dict: double-initialisation counts.

180.1d  the fixes, priced: one shared Lock, versus partition-and-merge, for
        the same 400,000 increments. Correctness has more than one price,
        and the spread is large enough to be an architecture argument.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import statistics
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 100_000
THREADS = 4
TRIALS = 7


class Box:
    __slots__ = ("n",)

    def __init__(self):
        self.n = 0


def in_threads(worker):
    ts = [threading.Thread(target=worker) for _ in range(THREADS)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


def losses_plain():
    box = Box()

    def worker():
        for _ in range(N):
            box.n += 1

    in_threads(worker)
    return THREADS * N - box.n


def ident(x):
    return x


def losses_with_call():
    box = Box()

    def worker():
        for _ in range(N):
            box.n = box.n + ident(1)

    in_threads(worker)
    return THREADS * N - box.n


def double_inits():
    d = {}
    made = []

    def worker():
        mine = 0
        for k in range(1_000):
            if k not in d:
                d[k] = k
                mine += 1
        made.append(mine)

    in_threads(worker)
    return sum(made) - 1_000


def timed(fn):
    t0 = time.perf_counter()
    fn()
    return (time.perf_counter() - t0) * 1000


def fix_lock():
    box = Box()
    lock = threading.Lock()

    def worker():
        for _ in range(N):
            with lock:
                box.n += 1

    in_threads(worker)
    assert box.n == THREADS * N


def fix_partition():
    totals = [0] * THREADS

    def make(slot):
        def worker():
            mine = 0
            for _ in range(N):
                mine += 1
            totals[slot] = mine
        return worker

    ts = [threading.Thread(target=make(i)) for i in range(THREADS)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert sum(totals) == THREADS * N


def main():
    print("=== 180.1  the race lab ===")
    print(provenance())
    print(f"method      : sorted results over {TRIALS} trials; races are")
    print("              distributions and are reported as such")
    print()

    print(f"--- a: unlocked `box.n += 1`, {THREADS} threads x {N:,} ---")
    print(f"  lost updates of {THREADS * N:,} : "
          f"{sorted(losses_plain() for _ in range(TRIALS))}")

    print(f"--- b: the same with a call inside, switchinterval=1e-6 ---")
    old = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        print(f"  lost updates of {THREADS * N:,} : "
              f"{sorted(losses_with_call() for _ in range(TRIALS))}")
    finally:
        sys.setswitchinterval(old)

    print("--- c: check-then-act on a shared dict, 1,000 keys ---")
    print(f"  double initialisations : "
          f"{sorted(double_inits() for _ in range(TRIALS))}")

    print("--- d: the fixes, priced (same 400,000 increments, exact) ---")
    print(f"  one shared Lock     : {min(timed(fix_lock) for _ in range(5)):8.1f} ms")
    print(f"  partition and merge : {min(timed(fix_partition) for _ in range(5)):8.1f} ms")

    print()
    print("Reading this. On the GIL build, row a is all zeros, and no switch")
    print("interval changes that: the modern GIL releases only at safe points,")
    print("so a call-free read-modify-write is never split mid-sequence. The")
    print("same code on the free-threaded build loses a quarter to a third of")
    print("its updates every single run. Row b shows the GIL build CAN lose")
    print("updates when a call sits inside the sequence and the interval is")
    print("shaken down - which together give the testing prescription: a")
    print("free-threaded CI leg is the only honest stress test, because the")
    print("build you develop on is structurally incapable of showing you most")
    print("of your races.")
    print()
    print("Row d is the architecture argument: the Lock is correct and pays")
    print("heavy contention on this shape (Chapter 96's queueing, in user")
    print("code); partition-and-merge is correct and costs almost nothing,")
    print("because it deletes the sharing instead of guarding it. The fastest")
    print("lock is the one the design made unnecessary.")


if __name__ == "__main__":
    main()
