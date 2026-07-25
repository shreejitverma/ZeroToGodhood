"""Listing 29.2 - the weakref toolkit: ref, callbacks, and the weak containers.

weakref.ref(obj) returns a callable that yields the object while it lives and
None after it is reclaimed. A callback fires when the referent dies. The weak
containers (WeakValueDictionary, WeakSet) hold their members weakly, so an entry
vanishes automatically when nothing else references it, the standard way to build
a cache that does not keep its contents alive.
"""

import weakref


class Resource:
    def __init__(self, name):
        self.name = name


print("--- a bare weakref is alive until the referent is reclaimed ---")
obj = Resource("r1")
r = weakref.ref(obj)
print("  r() while alive:", r().name)
del obj
print("  r() after the target is freed:", r())

print()
print("--- a callback fires when the referent dies ---")
died = []
obj2 = Resource("r2")
wr = weakref.ref(obj2, lambda ref: died.append("callback fired"))  # keep wr alive
del obj2
print("  callback record:", died)

print()
print("--- WeakValueDictionary: entries vanish when nothing else holds them ---")
cache = weakref.WeakValueDictionary()
kept = Resource("kept")
cache["kept"] = kept
cache["transient"] = Resource("transient")   # no other reference
print("  keys right after insert:", sorted(cache.keys()))
import gc
gc.collect()
print("  keys after collection   :", sorted(cache.keys()), "(transient dropped itself)")
print()
print("This is the caching pattern: a WeakValueDictionary caches objects without")
print("keeping them alive, so a cached value is reclaimed as soon as the rest of")
print("the program stops using it, and its cache entry disappears with it. No")
print("manual eviction, no leak.")
