"""Listing 120.1 - reference counting: deterministic destruction, and its one blind spot.

CPython's primary memory manager is reference counting: every object counts the
references to it, and the instant that count reaches zero the object is freed,
IMMEDIATELY and DETERMINISTICALLY (its __del__ runs right then, at the last del/
rebind, not 'eventually' like a tracing GC). The benefit is predictable, prompt
cleanup. The one thing refcounting alone CANNOT free is a REFERENCE CYCLE: objects
that reference each other keep each other's count above zero forever, so they leak
until the separate cyclic collector (Chapter 30) finds them. This listing shows both.
"""

import gc
import sys


class Loud:
    def __init__(self, name):
        self.name = name

    def __del__(self):
        print(f"  {self.name}: __del__ runs NOW (refcount hit 0)")


def main() -> None:
    print("--- deterministic: freed at the LAST reference, immediately ---")
    a = Loud("A")
    b = a                                # now 2 references to the one object
    print("  del a (b still holds it, so it lives):")
    del a
    print("  del b (last reference gone):")
    del b                                # __del__ runs right here, deterministically

    print("--- the refcount tracks references as they come and go ---")
    # NOTE: the ABSOLUTE count differs across versions (3.14 reports locals
    # differently), so we show the stable DELTA against a baseline.
    x = Loud("X")
    base = sys.getrefcount(x)
    holder = [x, x]                      # two more references
    print(f"  after [x, x]     : refcount rose by {sys.getrefcount(x) - base}   (2 refs in the list)")
    del holder
    print(f"  after del holder : refcount change from baseline is {sys.getrefcount(x) - base}   (back to baseline)")
    print("  del x:")
    del x                                # freed now

    print("--- the blind spot: a reference CYCLE refcounting cannot free ---")
    gc.collect()                         # clean slate

    class Node:
        def __del__(self):
            print("  Node: __del__ (freed by the cyclic collector)")

    n1, n2 = Node(), Node()
    n1.peer = n2                         # n1 -> n2
    n2.peer = n1                         # n2 -> n1  (a cycle)
    del n1, n2                           # each still referenced by the other: NOT freed
    print("  after del n1, n2: no __del__ yet (refcounts stuck at 1 via the cycle)")
    print("  gc.collect() (the cyclic collector) reclaims them:")
    gc.collect()                         # finds and frees the cycle

    print("--- the rule ---")
    print(f"  reference counting frees an object the instant its count hits 0")
    print(f"  (deterministic); cycles need the separate cyclic collector")


if __name__ == "__main__":
    main()
