"""Benchmark 177.1 - the container's lock, priced, and where read scaling hides.

177.1a  four sharing shapes, four threads each, one million operations per
        thread, against a one-thread run of the same worker:

    private lists, append        each thread its own container: the lock is
                                 never contended
    one shared list, append      all threads mutate one container: its lock
                                 is the new serialisation point
    one shared dict, read        lookups take no lock (optimistic reads)
    one shared dict, write       all threads mutate one dict

177.1b  the sharpest result in the volume so far: the same shared-dict read
        loop twice, once with the dict hoisted into a local variable before
        the loop, once reading the shared name on every pass. Identical work,
        identical dict, identical lock (none is taken). One scales, one
        collapses to worse than serial, because the per-pass load touches the
        shared dict's REFERENCE COUNT from four threads at once (Chapter 94's
        contended-atomic row), while the hoisted version takes one reference
        and rides it. Chapter 75's old advice, hoist hot globals into locals,
        was worth ~10% under the GIL; here it is the difference between 3.0x
        and 0.3x.

Methodology (Chapters 85 and 95): self-timed with perf_counter, fresh
containers per run, stated order, NOT timeit - these scalings are sensitive
to heap history and harness side effects, and an earlier timeit-based draft
of this benchmark produced different (and misleading) read numbers.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import statistics
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import Result, provenance, table  # noqa: E402

N = 1_000_000
THREADS = 4
REPEAT = 5

SHARED_DICT = {i: i for i in range(1024)}


def run_threads(worker, count):
    ts = [threading.Thread(target=worker) for _ in range(count)]
    t0 = time.perf_counter()
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return (time.perf_counter() - t0) * 1e9


def timed(label, make_worker, count):
    """Fresh state per run; min/median/RSD over REPEAT runs."""
    runs = []
    for _ in range(REPEAT):
        runs.append(run_threads(make_worker(), count))
    median = statistics.median(runs)
    rsd = (statistics.stdev(runs) / median * 100.0) if median else 0.0
    return Result(label, median, min(runs), rsd, REPEAT, 1)


def private_append():
    lst = []
    append = lst.append
    for i in range(N):
        append(i)


def make_shared_append():
    shared = []

    def worker():
        append = shared.append
        for i in range(N):
            append(i)
    return worker


def read_hoisted():
    d = SHARED_DICT            # one load; the loop reads a local
    s = 0
    for i in range(N):
        s += d[i & 1023]


def read_global_each_pass():
    s = 0
    for i in range(N):
        s += SHARED_DICT[i & 1023]   # the shared name, every pass


def make_writer():
    d = {i: i for i in range(1024)}

    def worker():
        for i in range(N):
            d[i & 1023] = i
    return worker


def main():
    private_append()   # warm
    read_hoisted()

    rows = [
        timed("1 thread, private list, append", lambda: private_append, 1),
        timed("4 threads, private lists, append", lambda: private_append, THREADS),
        timed("4 threads, ONE shared list, append", make_shared_append, THREADS),
        timed("1 thread, shared dict, read", lambda: read_hoisted, 1),
        timed("4 threads, shared dict, read", lambda: read_hoisted, THREADS),
        timed("4 threads, shared dict, write", make_writer, THREADS),
    ]
    print("=== 177.1a  container operations by sharing shape ===")
    print(provenance())
    print(f"method      : perf_counter around whole runs, {REPEAT} runs per row,")
    print("              fresh mutable state per run; NOT timeit (see docstring)")
    print()
    print(table(rows, baseline="4 threads, private lists, append"))

    print()
    pair = [
        timed("read, dict hoisted to a local", lambda: read_hoisted, THREADS),
        timed("read, shared name every pass", lambda: read_global_each_pass, THREADS),
    ]
    print("=== 177.1b  the same read, with and without the hoist ===")
    print(table(pair, baseline="read, dict hoisted to a local"))

    print()
    print("Reading 177.1a. On the GIL build the rows are one flat story. On the")
    print("free-threaded build: private mutation scales, the per-object lock")
    print("being uncontended and nearly free; shared MUTATION is worse than one")
    print("thread doing all the work, because four threads queueing on one")
    print("container's lock, with its cache line bouncing, cost more than")
    print("serialisation ever did; and reads of a shared dict scale, because")
    print("lookups take no lock at all - provided the loop holds its reference")
    print("correctly, which is 177.1b's subject.")
    print()
    print("Reading 177.1b. Identical work, identical dict, no lock taken in")
    print("either row. Reading the shared NAME on every pass makes each")
    print("iteration touch the dict's reference count from four threads at")
    print("once - Chapter 94's contended-atomic row, applied to the container")
    print("itself rather than its values - and the read collapses below")
    print("serial. Hoisting the dict into a local takes that reference once.")
    print("Chapter 75 taught the hoist as a ~10% constant-factor trick; on the")
    print("free-threaded build it decides whether shared-read code scales at")
    print("all. The general rule: on this build, how often your loop touches")
    print("a shared object's refcount is a first-class cost, and it is set by")
    print("name-resolution details that Chapter 75 already taught you to see.")


if __name__ == "__main__":
    main()
