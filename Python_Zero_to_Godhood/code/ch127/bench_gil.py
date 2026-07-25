"""Benchmark 127.1 - the GIL: threads help IO-bound work, not CPU-bound work.

The defining consequence of the GIL: only one thread runs Python bytecode at a time.
So for CPU-BOUND work (pure Python computation), two threads are NOT faster than
doing the work serially, they take turns on the one GIL. But the GIL is RELEASED
during blocking IO (and time.sleep), so for IO-BOUND work two threads overlap their
waits and finish in roughly half the time. This measures both: the same 2 units of
work done serially vs on 2 threads, for CPU-bound and IO-bound tasks.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

CPU_N = 8_000_000
IO_SEC = 0.2


def cpu_bound(n):
    x = 0
    for i in range(n):
        x += i * i
    return x


def io_bound():
    time.sleep(IO_SEC)                       # blocking wait: the GIL is released


def run_serial(fn, args, times):
    t0 = time.perf_counter()
    for _ in range(times):
        fn(*args)
    return time.perf_counter() - t0


def run_threaded(fn, args, times):
    threads = [threading.Thread(target=fn, args=args) for _ in range(times)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return time.perf_counter() - t0


def main():
    print("=== 127.1  GIL: CPU-bound vs IO-bound, serial vs 2 threads ===")
    print(provenance())
    print()

    cpu_serial = run_serial(cpu_bound, (CPU_N,), 2)
    cpu_threaded = run_threaded(cpu_bound, (CPU_N,), 2)
    io_serial = run_serial(io_bound, (), 2)
    io_threaded = run_threaded(io_bound, (), 2)

    print(f"  CPU-bound  serial     : {cpu_serial * 1000:6.0f} ms")
    print(f"  CPU-bound  2 threads  : {cpu_threaded * 1000:6.0f} ms   speedup {cpu_serial / cpu_threaded:.2f}x  (~1: GIL serializes)")
    print(f"  IO-bound   serial     : {io_serial * 1000:6.0f} ms")
    print(f"  IO-bound   2 threads  : {io_threaded * 1000:6.0f} ms   speedup {io_serial / io_threaded:.2f}x  (~2: GIL released in IO)")

    print()
    print("Reading this. Two CPU-bound threads finish no faster than serial (~1x):")
    print("the GIL lets only one run Python bytecode at a time, so they take turns.")
    print("Two IO-bound threads finish in about half the time (~2x): time.sleep and")
    print("blocking IO RELEASE the GIL, so the waits overlap. This is the rule for")
    print("threads in CPython: use threading for IO-bound concurrency (network, disk,")
    print("waiting), where the GIL is released and threads overlap. For CPU-bound")
    print("parallelism, threads do not help, use multiprocessing (separate processes,")
    print("separate GILs) or the free-threaded build. The GIL is a concurrency-vs-")
    print("simplicity trade: it makes single-threaded code fast and C extensions easy,")
    print("at the cost of multi-core CPU parallelism within one process.")


if __name__ == "__main__":
    main()
