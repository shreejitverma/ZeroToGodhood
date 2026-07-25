"""Listing 29.1 - a weak reference breaks a cycle so refcounting can reclaim it,
no collector needed.

A parent-child structure where the child holds a strong reference back to the
parent is a reference cycle: refcounting cannot reclaim it (Chapter 3), so it
waits for the cyclic collector. If the back-reference is WEAK, it does not count
toward the parent's refcount, so the cycle is broken and refcounting reclaims
both objects immediately and deterministically.
"""

import gc
import weakref


class Strong:
    def __init__(self, name):
        self.name = name
        self.children = []
        self.parent = None

    def __del__(self):
        print(f"  freed {self.name}")


gc.collect()
print("--- a strong parent<->child cycle: refcounting cannot reclaim it ---")
p = Strong("strong-parent")
c = Strong("strong-child")
p.children.append(c)
c.parent = p                      # strong back-reference -> a cycle
del p, c
print("  after 'del p, c': nothing freed yet (the cycle holds them up)")
print("  running gc.collect() ...")
gc.collect()                      # the collector breaks the cycle


class Weak:
    def __init__(self, name):
        self.name = name
        self.children = []
        self._parent = None

    def __del__(self):
        print(f"  freed {self.name}")

    @property
    def parent(self):
        return self._parent() if self._parent else None

    @parent.setter
    def parent(self, p):
        self._parent = weakref.ref(p) if p is not None else None


print()
print("--- a WEAK back-reference: refcounting reclaims immediately ---")
wp = Weak("weak-parent")
wc = Weak("weak-child")
wp.children.append(wc)
wc.parent = wp                    # weak back-reference -> no cycle
print("  'del wp, wc' frees both at once, before any collection:")
del wp, wc
print("  (both freed above; no gc.collect was needed)")
