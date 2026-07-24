"""Listing 8.1 - the new GIL switches on time, not on a bytecode count.

The GIL is the mutex that lets only one thread execute Python bytecode at a time,
so CPython's reference counting needs no per-object locking. Before 3.2 it was
handed off by a bytecode ticker (release after ~100 bytecodes), which on a
multi-core machine produced the convoy effect: the just-released thread, still
hot on its core, usually won the lock back before a thread on another core could
wake. Python 3.2 (Antoine Pitrou) switched to a time interval, so a waiting
thread is guaranteed a turn within roughly one interval.
"""

import sys

print("--- the switch interval replaced the old bytecode ticker ---")
print("  sys.getswitchinterval():", sys.getswitchinterval(), "seconds")
print("  that is the maximum a CPU-bound thread holds the GIL before yielding.")

print()
print("--- is the GIL enabled on this build? ---")
if hasattr(sys, "_is_gil_enabled"):
    print("  sys._is_gil_enabled():", sys._is_gil_enabled())
    print("  (a free-threaded 3.13+ build can report False; this is a default build)")
else:
    print("  sys._is_gil_enabled(): not available on this version")

print()
print("This changed FAIRNESS, not parallelism. Even with the new GIL, two")
print("CPU-bound Python threads still cannot run bytecode simultaneously; the")
print("interval only bounds how long one waits for its turn. True multi-core")
print("CPU parallelism needs processes, subinterpreters, or the free-threaded")
print("build (Deep L). The measurement in this chapter shows exactly that.")
