"""Benchmark 132.1 - locking an already-atomic operation is pure overhead.

list.append is atomic under the GIL (Listing 132.1): concurrent appends need no lock.
Wrapping it in a lock anyway adds the lock's acquire/release cost for no benefit, the
operation was already safe. This measures a bare append against a lock-protected one,
to show the cost of over-locking, and why knowing which operations are atomic lets you
lock only what needs it.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import threading
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 5_000_000


def main():
    print("=== 132.1  list.append: bare (already atomic) vs needlessly lock-protected ===")
    print(provenance())
    print()

    lst = []
    lock = threading.Lock()

    def bare():
        lst.append(1)

    def locked():
        with lock:
            lst.append(1)

    t_bare = min(timeit.repeat(bare, number=N, repeat=5)) / N
    t_locked = min(timeit.repeat(locked, number=N, repeat=5)) / N

    print(f"  bare append (already atomic) : {t_bare * 1e9:5.1f} ns   1.0x")
    print(f"  lock-protected append        : {t_locked * 1e9:5.1f} ns   {t_locked / t_bare:.1f}x")

    print()
    print("Reading this. The lock makes an already-atomic append several times slower")
    print("for no benefit: list.append completes in one uninterruptible bytecode under")
    print("the GIL, so concurrent appends were already safe. Over-locking is a common")
    print("reflex ('threads, so lock everything') that costs performance and, worse,")
    print("invites deadlocks (Chapter 46). The discipline: lock only COMPOUND")
    print("operations that a thread switch could interleave, read-modify-write")
    print("(counter += 1), check-then-act (if x in d: ...), multi-step updates. Single")
    print("append, pop, or dict/attribute assignment is atomic and needs no lock. And")
    print("for per-thread state, threading.local avoids sharing (and locking) entirely.")


if __name__ == "__main__":
    main()
