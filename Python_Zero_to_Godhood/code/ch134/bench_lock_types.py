"""Benchmark 134.1 - RLock costs more than Lock; use the simplest lock that works.

threading.Lock is a plain mutex. threading.RLock is RE-ENTRANT: it tracks which thread
owns it and a recursion count, so the owning thread can acquire it again. That bookkeeping
makes RLock a bit slower than Lock per acquire/release. This measures both uncontended,
to show the cost of re-entrancy, and why Lock is the default (reach for RLock only when
a lock-holding method calls another method that acquires the same lock).

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
    print("=== 134.1  uncontended acquire/release: Lock vs RLock ===")
    print(provenance())
    print()

    lock = threading.Lock()
    rlock = threading.RLock()

    def use_lock():
        with lock:
            pass

    def use_rlock():
        with rlock:
            pass

    t_lock = min(timeit.repeat(use_lock, number=N, repeat=5)) / N
    t_rlock = min(timeit.repeat(use_rlock, number=N, repeat=5)) / N

    print(f"  threading.Lock  : {t_lock * 1e9:5.1f} ns   1.0x")
    print(f"  threading.RLock : {t_rlock * 1e9:5.1f} ns   {t_rlock / t_lock:.1f}x")

    print()
    print("Reading this. RLock is modestly slower than Lock because it tracks the")
    print("owning thread and a recursion count so the owner can re-acquire it. Use a")
    print("plain Lock by default; reach for RLock only when you genuinely need")
    print("re-entrancy, a method that holds the lock calls another method that")
    print("acquires the same lock (common in a class where public methods lock and")
    print("call each other). But re-entrancy is often a sign the locking is too")
    print("coarse: a smaller critical section, or a lock-free design (queue.Queue,")
    print("thread-local, immutable data), usually beats needing RLock. The broader")
    print("rule from this volume: keep critical sections small, acquire locks in one")
    print("consistent order (no deadlocks), and prefer the simplest primitive.")


if __name__ == "__main__":
    main()
