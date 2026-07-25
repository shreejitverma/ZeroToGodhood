"""Listing 30.2 - the copy-and-subtract algorithm, and the tuple-untracking
optimization.

To find unreachable cycles, the collector cannot just look at refcounts: a cycle
keeps its own counts above zero. It uses copy-and-subtract. (1) Copy each tracked
object's refcount into a private gc_refs field. (2) Traverse every tracked
object's references and, for each reference to another object IN THE SET,
decrement that target's gc_refs. Afterward gc_refs counts only references from
OUTSIDE the set. (3) Objects with gc_refs > 0 are reachable roots and are live;
objects still at 0 are unreachable garbage.

This listing demonstrates the idea with get_referrers, and shows a real
optimization: a tuple containing only immutable objects is untracked, because it
provably cannot be part of a cycle.
"""

import gc


class Node:
    def __init__(self, name):
        self.name = name
        self.ref = None


gc.collect()

# An unreachable cycle: a <-> b, with no outside reference.
a = Node("a")
b = Node("b")
a.ref = b
b.ref = a
del a, b

print("--- copy-and-subtract in one sentence ---")
print("  gc_refs = real refcount, minus references from within the tracked set.")
print("  A cycle's objects are referenced only from within the set, so their")
print("  gc_refs reaches 0 and they are identified as unreachable garbage.")
print()
print("  gc.collect() reclaimed the a<->b cycle:", gc.collect(), "objects")

print()
print("--- the tuple-untracking optimization ---")
t = (1, 2, 3)                          # a tuple of only immutable objects
print("  (1, 2, 3) tracked when created:", gc.is_tracked(t))
gc.collect()                           # the collector untracks it
print("  (1, 2, 3) tracked after a collection:", gc.is_tracked(t))
nested = ([1], 2)                      # contains a mutable list
print("  ([1], 2) stays tracked:", gc.is_tracked(nested), "(it holds a mutable)")
print()
print("A tuple whose elements are all immutable (and themselves untracked) cannot")
print("be part of a cycle, so after the collector proves that once, it untracks")
print("the tuple and never scans it again. This is why a large constant tuple of")
print("numbers costs the collector nothing after the first collection.")
