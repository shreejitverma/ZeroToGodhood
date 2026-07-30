"""Listing 176.1 - memory without the GIL: same API, different deaths.

Chapter 95's subject is the machinery under allocation and collection on the
free-threaded build: pymalloc's job went to a per-thread-heap allocator
(mimalloc), the GC pre-header moved into the object header (Chapter 94), and
the cyclic collector became a stop-the-world event that must halt every thread.

Almost none of that is directly visible from Python, and what IS visible is
precise: the collector's API is unchanged, cycles are still collected exactly,
and the one observable seam is WHEN things die. Instances still die at their
last reference on every build. Functions die at their last reference on the
GIL builds and at the NEXT COLLECTION on the free-threaded build, because
their reference counting is deferred (Chapter 94). Classes have always waited
for the collector, on every build, because a class is born in a cycle.
"""

import gc
import weakref


class Plain:
    pass


def module_level_function():
    """A top-level function: exactly the kind deferred refcounting targets."""


def main() -> None:
    global module_level_function
    print("--- the collector's dials are unchanged ---")
    print(f"  gc.get_threshold() : {gc.get_threshold()}")
    print(f"  generations reported by get_stats() : {len(gc.get_stats())}")
    print("  same dials on every build; what turns beneath them differs")

    print("--- when things die, probed with weakrefs ---")
    obj = Plain()
    r_obj = weakref.ref(obj)
    del obj
    print(f"  instance dead at last reference : {r_obj() is None}")

    local_func = lambda: None                              # noqa: E731
    r_local = weakref.ref(local_func)
    del local_func
    print(f"  local function dead at last ref : {r_local() is None}")

    r_func = weakref.ref(module_level_function)
    del module_level_function
    print(f"  MODULE-level function, at del   : {r_func() is None}")

    class Local:
        pass
    r_cls = weakref.ref(Local)
    del Local
    print(f"  class dead at last reference    : {r_cls() is None}")

    gc.collect()
    print(f"  module function after collect   : {r_func() is None}")
    print(f"  class dead after gc.collect()   : {r_cls() is None}")
    print("  instances and LOCAL functions die promptly everywhere. classes wait")
    print("  for the collector everywhere (a class is born in a cycle with its")
    print("  own dict). the MODULE-level function row is the build seam: deferred")
    print("  reference counting (Chapter 94) targets top-level functions, so on")
    print("  the free-threaded build its death waits for the next collection")

    print("--- cycles are still collected, exactly ---")
    gc.disable()
    gc.collect()
    probes = []
    for _ in range(100):
        a, b = Plain(), Plain()
        a.other, b.other = b, a
        probes += [weakref.ref(a), weakref.ref(b)]
    del a, b
    gc.collect()
    print(f"  200 objects in 100 cycles, dead after one collect : "
          f"{sum(r() is None for r in probes)} of 200")
    gc.enable()
    print("  the algorithm (Deep B) is unchanged; what changed is that running")
    print("  it now STOPS EVERY THREAD, which bench 176.1 prices")

    print("--- the rule ---")
    print("  same lifetimes for data, later lifetimes for code objects, and a")
    print("  collector whose pauses are now a parallel-scalability tax: tie")
    print("  resources to 'with', never to garbage collection, on every build")


if __name__ == "__main__":
    main()
