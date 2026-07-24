"""Listing 26.1 - detecting whether the GIL is enabled, and the foundation the
free-threaded build stands on.

The free-threaded build (PEP 703, 3.13+) is a SEPARATE build of CPython, marked
by a 't' ABI suffix (python3.13t), in which the GIL is removed. This listing runs
on an ordinary build and shows how to detect the difference, plus the immortal-
object foundation (Chapter 19) that makes GIL-free reference counting tractable.

This is a default (GIL-enabled) build, so the performance numbers of the free-
threaded build cannot be measured here; they are cited in the chapter and flagged
in the verification queue.
"""

import sys
import sysconfig

print("--- is the GIL enabled on this interpreter? ---")
print("  sys._is_gil_enabled():", sys._is_gil_enabled())
print("  Py_GIL_DISABLED build var:", sysconfig.get_config_var("Py_GIL_DISABLED"))
print("  ABI flags:", repr(sys.abiflags), "(a 't' suffix marks a free-threaded build)")

print()
print("--- the immortal-object foundation (PEP 683, Chapter 19) ---")
print("  refcount(None):", sys.getrefcount(None), "(a sentinel, never modified)")
print("  Immortal objects have a refcount the interpreter never touches, so")
print("  every thread sharing None does no atomic refcount write on it. Without")
print("  this, the free-threaded build would pay an atomic operation on None for")
print("  every function return, a serious scalability problem.")

print()
print("This is a default build: _is_gil_enabled() is True and the ABI has no 't'.")
print("On a free-threaded build (python3.13t) the first would be False and the")
print("ABI would end in 't'. Both builds run the same source; the free-threaded")
print("one removes the GIL and adds per-object synchronization.")
