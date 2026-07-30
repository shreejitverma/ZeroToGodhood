"""Benchmark 175.1 - the price of a reference count, by ownership.

Four threads, each doing one million append/pop pairs into a private list. The
only variable is WHICH OBJECT is being appended, because append and pop incref
and decref it, and under biased reference counting (PEP 703) the cost of that
depends entirely on the relationship between the writing thread and the object:

    own object        created by the thread itself: the biased fast path,
                      a plain non-atomic increment
    foreign object    created by (and biased to) the main thread, but not
                      shared between workers: every incref is an atomic
                      operation on the shared field - no contention, just
                      atomics
    one shared object all four threads hammer the same shared field: atomics
                      plus the cache line bouncing between cores
    None              immortal: no refcount write at all

On the GIL build all four rows tie, because the GIL serialises everything and
a refcount write is a plain increment regardless of who makes it. The spread
appearing on the free-threaded build IS biased reference counting, measured.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import threading

N = 1_000_000
THREADS = 4
SHARED = object()
MAIN_OWNED = [object() for _ in range(THREADS)]

def hammer(make_target, n=N):
    target = make_target()
    lst = []
    append, pop = lst.append, lst.pop
    for _ in range(n):
        append(target)
        pop()

def run(factories):
    workers = [threading.Thread(target=hammer, args=(f,)) for f in factories]
    for w in workers:
        w.start()
    for w in workers:
        w.join()

def own():
    run([object] * THREADS)

def foreign():
    run([lambda o=o: o for o in MAIN_OWNED])

def shared():
    run([lambda: SHARED] * THREADS)

def immortal():
    run([lambda: None] * THREADS)

hammer(object, 1000)   # warm
"""


def main():
    rows = [
        measure("own object (thread-created)", "own()", SETUP, repeat=5, number=1),
        measure("foreign object, unshared", "foreign()", SETUP, repeat=5, number=1),
        measure("one object shared by all", "shared()", SETUP, repeat=5, number=1),
        measure("None (immortal)", "immortal()", SETUP, repeat=5, number=1),
    ]
    report("175.1  4 threads x 1M append/pop: the refcount's price by ownership",
           rows, baseline="own object (thread-created)")

    print()
    print("Reading this. The work is identical in every row - same list, same")
    print("append, same pop - and the only change is which object's refcount the")
    print("threads are writing. On the GIL build the rows tie: one lock, one")
    print("price. On the free-threaded build the rows fan out into the price")
    print("list from Listing 175.1: the biased fast path at the bottom, plain")
    print("atomics above it, contended atomics with cache-line ping-pong at the")
    print("top, and the immortal row back at the bottom because it writes")
    print("nothing at all.")
    print()
    print("Two design lessons fall out. First, the bias is to the CREATING")
    print("thread: an object built in main and handed to a worker pays the")
    print("atomic path even if no other thread ever touches it, so on the")
    print("free-threaded build, allocate where you use. Second, immortality is")
    print("not a curiosity: it is why every module, function, and None in a hot")
    print("loop does not become a contention point, and the shared-object row is")
    print("what the interpreter would have looked like without it.")


if __name__ == "__main__":
    main()
