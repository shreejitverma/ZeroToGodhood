"""Benchmark 174.1 - the headline of the volume: CPU-bound threads, both builds.

One CPU-bound Python function, three shapes on each build:

    one call                   the unit of work
    4 calls, sequential        the honest baseline for speedup claims
    4 calls, on 4 threads      the same work, offered to 4 cores

On the GIL build the threaded row ties the sequential row (or loses to it):
Chapter 8 measured this and Chapter 80 measured it again at the C boundary.
On the free-threaded build the threaded row divides by the core count. That
difference is the reason PEP 703 exists, and with the t-build in the
verification matrix it is measured here rather than cited.

Run this under each interpreter separately:

    make bench CH=ch174                       # 3.13 (GIL)
    python3 ch174/bench_thread_scaling.py     # 3.14 (GIL)
    $PY314T ch174/bench_thread_scaling.py     # 3.14t (free-threaded)

Ratios are within-build only, as everywhere in this book. The single-threaded
gap BETWEEN builds is reported by comparing the two "one call" rows by hand,
with the caveat that Py_GIL_DISABLED itself is the differing build flag - that
cross-build gap is exactly the overhead PEP 779 tracks (~10% class on 3.14).

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import threading

N = 2_000_000

def work(n=N):
    total = 0
    for i in range(n):
        total += i * i
    return total

def sequential(times=4):
    for _ in range(times):
        work()

def threaded(times=4):
    workers = [threading.Thread(target=work) for _ in range(times)]
    for w in workers:
        w.start()
    for w in workers:
        w.join()

work(1000)   # warm the specializer before timing
"""


def main():
    rows = [
        measure("one call", "work()", SETUP, repeat=5, number=1),
        measure("4 calls, sequential", "sequential()", SETUP, repeat=5, number=1),
        measure("4 calls, on 4 threads", "threaded()", SETUP, repeat=5, number=1),
    ]
    report("174.1  the same CPU-bound work, sequential and threaded",
           rows, baseline="4 calls, sequential")

    seq = next(r for r in rows if r.label == "4 calls, sequential")
    par = next(r for r in rows if r.label == "4 calls, on 4 threads")
    print()
    print(f"  threads bought a factor of {seq.min_ns / par.min_ns:.2f} on this build")
    print()
    print("Reading this. The work is pure Python and CPU-bound - no I/O, no C")
    print("boundary to release at (Chapter 80's escape does not apply). On the")
    print("GIL build the interpreter runs one thread at a time, so four threads")
    print("re-serialise into roughly the sequential time plus switching costs.")
    print("On the free-threaded build the same three lines of threading code")
    print("divide the wall time by close to the thread count, because PEP 703")
    print("replaced the one lock with per-object coordination the rest of this")
    print("volume examines: biased reference counting (Chapter 94), a thread-")
    print("aware allocator and collector (Chapter 95), and per-container locks")
    print("(Chapter 96). The price of that machinery is the single-threaded gap")
    print("between the builds' 'one call' rows, which PEP 779 bounds as a")
    print("condition of the whole project.")


if __name__ == "__main__":
    main()
