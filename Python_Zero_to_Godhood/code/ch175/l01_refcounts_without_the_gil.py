"""Listing 175.1 - what a refcount is on each build: immortality, headers, and meaning.

Without the GIL, `ob_refcnt += 1` from two threads is a data race, so PEP 703
rebuilt the reference count itself: split into an owner-thread field written
without atomics and a shared field written with them, with immortal objects
(PEP 683) opting out entirely. This listing shows what is OBSERVABLE of that
redesign from pure Python; bench_refcount_contention.py prices it.

Three facts here are identical on every build, one is not, and the exception is
the point: the free-threaded object header is twice the size, except where it
isn't, and the exception's exception teaches how the header was rebuilt.
"""

import sys


class SlottedPair:
    __slots__ = ("x", "y")


def main() -> None:
    print("--- immortality: the objects that opted out of counting ---")
    before = sys.getrefcount(None)
    hoard = [None] * 1_000
    print(f"  1,000 new references to None moved its refcount : "
          f"{sys.getrefcount(None) != before}")
    obj = object()
    before = sys.getrefcount(obj)
    hoard = [obj] * 1_000
    print(f"  1,000 references to an ordinary object moved it by : "
          f"{sys.getrefcount(obj) - before:+,}")
    print("  None, True, False, small ints, and interned strings are immortal on")
    print("  every current build (PEP 683); incref and decref on them are no-ops.")
    print("  built FOR free-threading: the most-shared objects generate no")
    print("  refcount writes, so they cannot become cache-line contention points")

    print("--- the object header, by build ---")
    print(f"  sizeof(object())          : {sys.getsizeof(object())} bytes")
    print(f"  sizeof([]) (GC-tracked)   : {sys.getsizeof([])} bytes")
    print(f"  sizeof(two-slot instance) : {sys.getsizeof(SlottedPair())} bytes")

    print("--- container references are still exact; frame references are not ---")
    fresh = object()
    baseline = sys.getrefcount(fresh)
    print(f"  getrefcount(fresh local object) : {baseline}")
    holder = []
    holder.append(fresh)
    print(f"  append moves it by exactly +1   : "
          f"{sys.getrefcount(fresh) - baseline == 1}")
    holder.pop()
    print(f"  pop restores it                 : {sys.getrefcount(fresh) == baseline}")
    print("  the raw report depends on how the FRAME holds its references: 3.13")
    print("  counts the local variable's reference; 3.14's frames hold deferred")
    print("  stack references that getrefcount does not see, on both builds. the")
    print("  accounting of CONTAINER references is exact everywhere; what changed")
    print("  is who may write the count and at what price:")

    print("--- the price list the benchmark measures ---")
    print("  owner thread, its own object   : plain increment, no atomics")
    print("  another thread, same object    : atomic operation on a shared field")
    print("  many threads, one hot object   : atomics + cache-line ping-pong")
    print("  any thread, an immortal        : no write at all")


if __name__ == "__main__":
    main()
