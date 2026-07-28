"""Benchmark 161.1 - what releasing the GIL is worth, in threads that actually scale.

Three measurements, all of the same shape: do a fixed amount of work in one thread,
then split the same work across four threads, and report the speedup.

  161.1a  a C sleep through ctypes.CDLL (GIL released) and ctypes.PyDLL (GIL held).
          This is the clean case: the C function touches nothing, so releasing is free
          and the four threads overlap completely.
  161.1b  hashlib.sha256 over a large buffer. A real standard-library C extension that
          releases the GIL around its digest loop.
  161.1c  the same shape of work as a pure-Python loop. The control: no C boundary,
          nothing to release, and a speedup of 1.0 - four threads take four times as
          long as one, which is what complete serialisation looks like.

Wall-clock timing with threads is noisier than the microbenchmarks elsewhere in this
book, so each configuration is run several times and the MINIMUM total wall time is
reported, for the same one-sided-noise reason `_harness.bench` uses min.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import ctypes
import ctypes.util
import hashlib
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

THREADS = 4
REPEAT = 7
SLEEP_US = 100_000          # 100 ms of C sleep per unit of work
HASH_MB = 64                # per unit of work
PY_ITERS = 3_000_000        # per unit of work, tuned to a comparable duration


def run_parallel(work, n_threads, repeat=REPEAT):
    """Minimum wall time to run `work` once in each of n_threads threads."""
    best = float("inf")
    for _ in range(repeat):
        threads = [threading.Thread(target=work) for _ in range(n_threads)]
        start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        best = min(best, time.perf_counter() - start)
    return best


def sleeper(loader):
    lib = loader(ctypes.util.find_library("c"))
    lib.usleep.argtypes = [ctypes.c_uint]
    lib.usleep.restype = ctypes.c_int

    def work():
        lib.usleep(SLEEP_US)

    return work


def hasher():
    data = bytes(HASH_MB << 20)

    def work():
        hashlib.sha256(data).digest()

    return work


def python_loop():
    def work():
        total = 0
        for i in range(PY_ITERS):
            total += i
        return total

    return work


def row(label, work):
    one = run_parallel(work, 1)
    many = run_parallel(work, THREADS)
    ideal = one * THREADS
    print(f"  {label:<34} {one * 1e3:8.1f} {many * 1e3:9.1f} {ideal / many:7.2f}x")


def main():
    print(f"=== 161.1  1 thread vs {THREADS} threads, same work per thread ===")
    print(provenance())
    print(f"method      : min of {REPEAT} runs of each configuration, wall clock")
    print(f"speedup     : (1-thread time x {THREADS}) / {THREADS}-thread time."
          f"  {THREADS}.00x is perfect scaling,")
    print("              1.00x means the threads serialised completely.")
    print()
    print(f"  {'case':<34} {'1 thd ms':>8} {'4 thd ms':>9} {'speedup':>8}")
    print("  " + "-" * 62)
    row(f"C sleep via CDLL  (GIL released)", sleeper(ctypes.CDLL))
    row(f"C sleep via PyDLL (GIL held)", sleeper(ctypes.PyDLL))
    row(f"sha256 over {HASH_MB} MB (GIL released)", hasher())
    row(f"pure-Python loop  (GIL held)", python_loop())

    print()
    print("Reading this. The CDLL row is the clean case: the C function touches no")
    print("Python object, ctypes drops the GIL for the duration, and four threads take")
    print("as long as one. The PyDLL row is the same C function with the GIL held, and")
    print("it serialises exactly as the model predicts. sha256 is the same story inside")
    print("the standard library, and it is the reason threads are the right tool for")
    print("hashing, compressing, and IO even before free-threading. The pure-Python row")
    print("is the control: no C boundary, nothing to release, and the four-thread run")
    print("takes about four times the one-thread run, a speedup of 1.0, which is the")
    print("definition of no parallelism. Threads did not make it slower here, but they")
    print("bought nothing, and every millisecond of the GIL handoff is pure overhead.")


if __name__ == "__main__":
    main()
