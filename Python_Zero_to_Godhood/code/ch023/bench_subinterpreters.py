# requires: 3.14+
"""Benchmark 23.1 - subinterpreters parallelize CPU work; threads do not.

Chapter 8 measured that four threads give no speedup on CPU-bound work, because
one interpreter has one GIL. A subinterpreter has its OWN GIL (PEP 684), so four
subinterpreters, each driven by a thread, run four streams of Python bytecode in
genuine parallel, in a single process. This measures the three options:
serial, four threads, four subinterpreters.

Coarse-grained timing done directly; provenance header reused from the harness.
"""

import sys
import threading
import time
from pathlib import Path
from concurrent import interpreters

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

WORKERS = 4
CODE = "total = 0\nfor i in range(5_000_000):\n    total += i * i"


def run_code():
    exec(CODE, {})


def serial():
    for _ in range(WORKERS):
        run_code()


def with_threads():
    ts = [threading.Thread(target=run_code) for _ in range(WORKERS)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


def with_subinterpreters():
    interps = [interpreters.create() for _ in range(WORKERS)]
    ts = [threading.Thread(target=i.exec, args=(CODE,)) for i in interps]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    for i in interps:
        i.close()


def best(fn, repeat=3):
    return min(_timed(fn) for _ in range(repeat))


def _timed(fn):
    t0 = time.perf_counter()
    fn()
    return time.perf_counter() - t0


def main():
    print("=== 23.1  CPU-bound parallelism: threads vs subinterpreters ===")
    print(provenance())
    print(f"method      : {WORKERS} CPU tasks, min of 3 runs")
    print()

    with_subinterpreters()  # warm interpreter creation out of the timed region
    s = best(serial)
    t = best(with_threads)
    u = best(with_subinterpreters)

    print(f"  serial            : {s * 1e3:7.0f} ms   1.00x")
    print(f"  {WORKERS} threads         : {t * 1e3:7.0f} ms   {s / t:.2f}x   <- GIL: no speedup")
    print(f"  {WORKERS} subinterpreters : {u * 1e3:7.0f} ms   {s / u:.2f}x   <- own GILs: real parallelism")

    print()
    print("Reading this. Four threads give no speedup, exactly as Chapter 8")
    print("measured: one interpreter, one GIL. Four subinterpreters give real")
    print("parallelism, because each has its own GIL, in a single process with no")
    print("subprocess spawn or pickle tax. This is the third concurrency model:")
    print("between threads (shared everything, one GIL, I/O only) and processes")
    print("(nothing shared, real parallelism, heavy IPC). Subinterpreters share a")
    print("process but not objects, and pass data through queues.")


if __name__ == "__main__":
    main()
