"""Listing 19.2 - immortal objects, and the sentinel that marks them.

PEP 683 (Python 3.12) gave certain objects a reference count that the
interpreter never modifies. `None` is shared by every module, every thread, and
every frame in the process; incrementing and decrementing its refcount was pure
contention with nothing to show for it.

The sentinel value differs between 3.13 and 3.14. That is not drift in this
listing; it is CPython changing the constant. Both are recorded.
"""

import sys

print("--- refcounts of objects the interpreter shares everywhere ---")
for name, obj in [("None", None), ("True", True), ("False", False),
                  ("0", 0), ("1", 1), ("256", 256), ("'a'", "a")]:
    print(f"  refcount({name:6}) = {sys.getrefcount(obj):>12}")

print()
print("--- and one that is not immortal ---")
print(f"  refcount(257   ) = {sys.getrefcount(257):>12}")

print()
print("--- the sentinel, in hex ---")
r = sys.getrefcount(None)
print(f"  refcount(None) = {r} = {hex(r)}")

print()
print("--- consequence: refcounts of immortal objects carry no information ---")
holders = [None] * 1_000_000
print("  after binding None one million more times:")
print(f"  refcount(None) = {sys.getrefcount(None):>12}  (unchanged)")
del holders
