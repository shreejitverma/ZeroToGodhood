"""Listing 28.1 - pymalloc: the arena/pool/block structure, and the free-list
reuse that makes small-object allocation fast.

Python allocates constantly: every int result, every tuple, every frame is a
heap object, and most are small and short-lived. Calling the system malloc for
each would be slow and would fragment the heap. pymalloc (obmalloc.c) is
CPython's allocator for small objects (<= 512 bytes): it requests large arenas
from the OS, carves them into pools, carves pools into fixed-size blocks, and
keeps a free list per size class so a freed block is reused immediately.
"""

import sys

print("--- the small-object threshold and size classes ---")
print("  small block threshold: 512 bytes, 32 size classes (obmalloc.c)")
print("  allocations up to 512 bytes go through pymalloc pools; larger go to")
print("  the system malloc directly.")

print()
print("--- object sizes step through the size classes ---")
for size in (8, 32, 64, 512, 513):
    print(f"  getsizeof(bytes({size:>3})) = {sys.getsizeof(bytes(size))}")

print()
print("--- pymalloc reuses a freed block immediately (the free list) ---")
first = id(bytes(24))               # allocate, then it is freed (refcount 0)
second = id(bytes(24))              # same size class -> same block reused
print("  two same-size allocations reused the block:", first == second)
print("  this is why churning small short-lived objects is cheap: the block")
print("  goes straight back on the free list and the next allocation of that")
print("  size class pops it off, no system call, no search.")

print()
print("--- the arena hierarchy (sizes from sys._debugmallocstats) ---")
print("  ARENA  (1 MB)  requested from the OS with mmap")
print("    POOL (16 KB) one size class per pool")
print("      BLOCK      fixed size for the pool's class; the unit handed out")
print("  a freed block returns to its pool's free list; an empty pool returns")
print("  to the arena; a fully-empty arena can be released back to the OS.")
