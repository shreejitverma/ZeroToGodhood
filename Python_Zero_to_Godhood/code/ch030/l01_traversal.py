"""Listing 30.1 - the collector sees the object graph through tp_traverse, and
only tracks containers.

The cyclic collector must find unreachable cycles, which means it must walk the
references between objects. Each container type implements a tp_traverse slot
that reports the objects it references; gc.get_referents drives it. Only
containers (objects that can reference other objects) are tracked; atomic objects
like int and str are never tracked, because they cannot form a cycle.
"""

import gc


class Node:
    def __init__(self, name):
        self.name = name
        self.ref = None


a = Node("a")
b = Node("b")
a.ref = b
b.ref = a                              # a <-> b cycle

print("--- tp_traverse: what an object references (get_referents) ---")
print("  a references:", sorted(type(x).__name__ for x in gc.get_referents(a)))

print()
print("--- the reverse: who references b (get_referrers) ---")
print("  number of objects referencing b:", len(gc.get_referrers(b)))

print()
print("--- only containers are tracked; atomic objects never are ---")
print("  is_tracked(Node instance):", gc.is_tracked(a))
print("  is_tracked(42)           :", gc.is_tracked(42))
print("  is_tracked('text')       :", gc.is_tracked("text"))
print("  is_tracked([1, 2])       :", gc.is_tracked([1, 2]))
print()
print("An int or str cannot reference another object, so it can never be part of")
print("a cycle, so the collector never tracks it. This keeps the collector's")
print("workload proportional to the number of CONTAINERS, not all objects.")
