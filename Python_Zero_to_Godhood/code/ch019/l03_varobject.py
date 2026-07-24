"""Listing 19.3 - fixed-size objects, variable-size objects, and the GC header.

A type declares its per-instance footprint in two numbers: `tp_basicsize` (the
struct itself) and `tp_itemsize` (bytes per element, zero for fixed-size types).
Both are exposed to Python as `__basicsize__` and `__itemsize__`.

`sys.getsizeof` does not report `tp_basicsize` back to you. It reports what was
actually allocated, which for a GC-tracked object includes a `PyGC_Head` the
type never mentions. This listing reconciles the two, and shows where the naive
formula breaks.
"""

import gc
import sys

print("--- what each type declares ---")
print(f"  {'type':8} {'__basicsize__':>14} {'__itemsize__':>13}")
for t in (object, int, tuple, bytes, list, dict, str):
    print(f"  {t.__name__:8} {t.__basicsize__:>14} {t.__itemsize__:>13}")

print()
print("--- tuple is the clean PyVarObject: size grows with ob_size ---")
for n in (0, 1, 2, 8):
    obj = tuple(range(n))
    declared = tuple.__basicsize__ + n * tuple.__itemsize__
    print(f"  tuple of {n}: declared={declared:>4}  getsizeof={sys.getsizeof(obj):>4}"
          f"  delta={sys.getsizeof(obj) - declared:>3}")

print()
print("--- the constant delta is the GC header, allocated in front of the object ---")
for label, obj in [("object()", object()), ("(1, 2)", (1, 2)), ("[1, 2]", [1, 2])]:
    print(f"  {label:10} gc.is_tracked={gc.is_tracked(obj)!s:5} getsizeof={sys.getsizeof(obj):>4}")

print()
print("--- where the naive formula breaks: list stores items elsewhere ---")
print(f"  list.__itemsize__ = {list.__itemsize__}, yet a list clearly grows:")
for n in (0, 1, 2, 8):
    print(f"    getsizeof(list of {n}) = {sys.getsizeof(list(range(n))):>4}")
print("  a list's elements live in a separate ob_item allocation, so its")
print("  per-element cost is real but is not described by tp_itemsize.")
