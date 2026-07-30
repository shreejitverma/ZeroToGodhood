"""Listing 177.1 - what the containers still promise, on every build.

Chapter 93 established that per-operation atomicity on the builtin containers
survived the GIL's removal, provided now by each container's own lock. This
listing pins the contract down: WHICH promises hold (single operations, from
any number of threads), which never held (compound operations), and which
error contracts are unchanged (mutation during iteration). Every fact here is
deterministic and identical on the GIL and free-threaded builds, which is the
compatibility PEP 703 paid for; what the new machinery COSTS is
bench_container_contention.py.
"""

import collections
import threading

THREADS = 4
PER_THREAD = 100_000


def in_threads(worker):
    ts = [threading.Thread(target=worker, args=(tid,)) for tid in range(THREADS)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


def main() -> None:
    print("--- single operations, four threads, no user locks ---")
    lst: list[int] = []
    in_threads(lambda tid: [lst.append(i) for i in range(PER_THREAD)])
    print(f"  list.append x {THREADS * PER_THREAD:,}          -> len {len(lst):,}")

    d: dict[int, int] = {}

    def write_disjoint(tid):
        base = tid * PER_THREAD
        for i in range(PER_THREAD):
            d[base + i] = tid

    in_threads(write_disjoint)
    print(f"  dict[key] = v, disjoint keys -> len {len(d):,}")

    s: set[int] = set()

    def add_disjoint(tid):
        base = tid * PER_THREAD
        for i in range(PER_THREAD):
            s.add(base + i)

    in_threads(add_disjoint)
    print(f"  set.add, disjoint values     -> len {len(s):,}")

    dq: collections.deque = collections.deque()
    in_threads(lambda tid: [dq.append(i) for i in range(PER_THREAD)])
    print(f"  deque.append x {THREADS * PER_THREAD:,}         -> len {len(dq):,}")
    print("  every count exact, on every build: one operation, one container,")
    print("  atomic - by the GIL there, by the container's own lock here")

    print("--- compound operations: the promise that never existed ---")
    counter = {"n": 0}
    lock = threading.Lock()

    def locked_rmw(tid):
        for _ in range(PER_THREAD):
            with lock:
                counter["n"] += 1

    in_threads(locked_rmw)
    print(f"  d[k] += 1 under a Lock       -> {counter['n']:,}")
    print("  read-modify-write spans two operations; the container's lock covers")
    print("  each, never the pair. the loss rate without the Lock is a")
    print("  probability, not a fact, and Chapter 99 measures it")

    print("--- the iteration contract is unchanged ---")
    growing = {i: i for i in range(3)}
    try:
        for key in growing:
            growing[key + 100] = key
    except RuntimeError as exc:
        print(f"  mutate while iterating -> RuntimeError: {exc}")
    print("  same exception, same rule, every build: iteration pins the")
    print("  container's shape, and the per-object lock does not change the")
    print("  language's contract, only who enforces it")

    print("--- what this costs is the benchmark's subject ---")
    print("  a lock that is never contended is nearly free; a shared container")
    print("  under parallel mutation is a serialisation point that costs MORE")
    print("  than the GIL did; and read scaling depends on refcount details")
    print("  (Chapter 94) that only measurement reveals")


if __name__ == "__main__":
    main()
