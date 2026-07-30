"""Benchmark 178.1 - where the free-threaded build's single-threaded cost lives.

178.1a  six single-threaded micro-workloads, run identically on the GIL and
        free-threaded builds of CPython 3.14.6. Within each build the table is
        ordinary; the point is the PAIR of tables read side by side, which
        this book allows itself here under a stated caveat (Chapter 93): the
        two builds match on every dispatch-critical flag except
        Py_GIL_DISABLED itself, so the per-row gap is attributable to the
        free-threading machinery, biased refcount checks, per-object locking
        on mutation, mimalloc, deferred references, and not to compiler or
        dispatch differences.

        The rows are chosen to separate the suspects: pure arithmetic touches
        almost none of the machinery; attribute reads touch refcounts;
        appends and dict writes take the container's lock; calls exercise
        frames and stack references.

178.1b  the thread-local-bytecode check: the same worker-thread loop, with
        the function warmed only in the worker against warmed in main first.
        Equal times prove the worker's private copy specialized (Listing
        178.1's dis result shows main's copy cold), closing the loop on the
        chapter's mechanism claim.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
class Point:
    def __init__(self):
        self.x = 3

p = Point()
data = list(range(1000))

def call_me(a, b):
    return a

def arithmetic():
    total = 0
    for i in range(1000):
        total = total + i * i
    return total

def attr_reads():
    total = 0
    for i in range(1000):
        total = total + p.x
    return total

def appends():
    lst = []
    append = lst.append
    for i in range(1000):
        append(i)

def dict_writes():
    d = {}
    for i in range(1000):
        d[i] = i

def calls():
    for i in range(1000):
        call_me(i, i)

def genexp():
    return sum(i * i for i in data)

for _ in range(100):
    arithmetic(); attr_reads(); appends(); dict_writes(); calls(); genexp()
"""


def main():
    rows = [
        measure("arithmetic loop", "arithmetic()", SETUP, repeat=9, number=2_000),
        measure("attribute reads", "attr_reads()", SETUP, repeat=9, number=2_000),
        measure("list appends", "appends()", SETUP, repeat=9, number=2_000),
        measure("dict writes", "dict_writes()", SETUP, repeat=9, number=2_000),
        measure("function calls", "calls()", SETUP, repeat=9, number=2_000),
        measure("genexp sum", "genexp()", SETUP, repeat=9, number=2_000),
    ]
    report("178.1a  1,000-iteration micro-workloads, single-threaded",
           rows, baseline="arithmetic loop")

    print()
    print("=== 178.1b  thread-local bytecode: worker-warmed vs main-warmed ===")

    src = """
def work(p, n):
    total = 0
    for i in range(n):
        total = total + p.x
    return total
"""

    class Point:
        def __init__(self):
            self.x = 3

    def fresh_work():
        ns = {}
        exec(src, ns)
        return ns["work"]

    def time_in_worker(fn, warm_in_main):
        point = Point()
        if warm_in_main:
            for _ in range(200):
                fn(point, 100)
        result = []

        def runner():
            for _ in range(50):
                fn(point, 1000)
            t0 = time.perf_counter()
            for _ in range(200):
                fn(point, 10_000)
            result.append((time.perf_counter() - t0) * 1e6)

        t = threading.Thread(target=runner)
        t.start()
        t.join()
        return result[0]

    worker_only = min(time_in_worker(fresh_work(), False) for _ in range(5))
    main_warmed = min(time_in_worker(fresh_work(), True) for _ in range(5))
    print(f"  worker-only code : {worker_only:9.0f} us")
    print(f"  main-warmed code : {main_warmed:9.0f} us")
    print(f"  ratio            : {worker_only / main_warmed:9.2f}x")
    print("  equal times on the free-threaded build: the worker specialized its")
    print("  own thread-local copy, even though main's copy shows cold in dis")

    print()
    print("Reading 178.1a. Compare this build's table with the other build's,")
    print("row by row. Pure arithmetic barely moves: dispatch is dispatch, and")
    print("3.14t's re-enabled specializer keeps it so. The rows that touch the")
    print("new machinery move by their exposure to it: attribute reads pay the")
    print("biased-refcount checks, appends and dict writes pay an uncontended")
    print("per-object lock per operation, and calls pay the deferred-reference")
    print("frame machinery. None of these is the ~40% of 3.13t, which was the")
    print("DISABLED specializer, not the locks; PEP 779's ~10% suite average")
    print("for 3.14t is these rows, mixed in workload proportions.")


if __name__ == "__main__":
    main()
