"""Listing 3.4 - a cycle survives reference counting; the cyclic collector
reclaims it, and since PEP 442 it finalizes the objects rather than abandoning
them.

Reference counting frees an object the instant its count hits zero, which
handles all acyclic garbage instantly and deterministically. It cannot free a
cycle: each object in the cycle keeps the others' counts above zero. The cyclic
collector exists for exactly this and nothing else.
"""

import gc
import sys


class Node:
    def __init__(self, name):
        self.name = name
        self.ref = None

    def __del__(self):
        print(f"  __del__ {self.name}")


gc.collect()                       # clean slate
a = Node("A")
b = Node("B")
a.ref = b
b.ref = a                          # build the cycle

print("--- the cycle keeps both objects alive despite no outside references ---")
print("  refcount(A) inside the cycle:", sys.getrefcount(a) - 1)
del a, b                           # bindings gone; the cycle keeps both alive
print("  after 'del a, b': nothing was freed (no __del__ yet)")

print()
print("--- gc.collect() finds the unreachable cycle and finalizes it ---")
reclaimed = gc.collect()
print("  objects reclaimed:", reclaimed)

print()
print("PEP 442 (3.4+): the __del__ methods above ran. Before 3.4, an object with")
print("__del__ inside a cycle was deemed uncollectable and parked in gc.garbage")
print("forever. That era is over; do not design around gc.garbage.")
print()
print("default GC threshold on this build:", gc.get_threshold())
