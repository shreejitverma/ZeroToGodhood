"""Listing 19.5 - what the object header costs at scale.

A million 64-bit integers is 8 MB in C. This measures what the same million
integers cost in Python, and then what three standard escape hatches recover.

Uses `tracemalloc` rather than `sys.getsizeof`, because `getsizeof` is shallow:
it reports the container's own footprint and not the objects it points at, which
is exactly the cost being measured here.
"""

import array
import sys
import tracemalloc

N = 1_000_000


def peak_mb(build) -> float:
    tracemalloc.start()
    obj = build()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del obj
    return peak / 1024 / 1024


print(f"--- storing {N:,} integers, four ways ---")
print(f"  {'representation':32} {'MB':>8}  {'bytes/element':>14}")

cases = [
    ("list of int  (0..N)", lambda: list(range(N))),
    ("tuple of int (0..N)", lambda: tuple(range(N))),
    ("array('q')  (int64)", lambda: array.array("q", range(N))),
    ("bytes       (raw)  ", lambda: bytes(N * 8)),
]
for label, build in cases:
    mb = peak_mb(build)
    print(f"  {label:32} {mb:>8.1f}  {mb * 1024 * 1024 / N:>14.1f}")

print()
print("--- why the list is not simply 8 bytes per element ---")
print(f"  one pointer in the list's ob_item array : {8:>3} bytes")
print(f"  one int object it points at             : {sys.getsizeof(N):>3} bytes")
print("  the pointer is the cheap half; the object header is the expensive half")

print()
print("--- and why small integers are nearly free ---")
small = peak_mb(lambda: [i % 256 for i in range(N)])
large = peak_mb(lambda: [i + 1000 for i in range(N)])
print(f"  list of {N:,} ints in 0..255      : {small:>6.1f} MB")
print(f"  list of {N:,} ints above the cache: {large:>6.1f} MB")
print("  the first list holds a million pointers to 256 shared, immortal objects.")
print("  the second allocates a million distinct int objects.")
