"""Listing 7.4 - Python 3 made the sequence builtins lazy, dict methods return
live views, and memoryview shares a buffer with zero copy.

range/zip/map/filter return iterators instead of materializing lists;
dict.keys/values/items return live views onto the dict; memoryview exposes
another object's buffer without copying, so a slice can be read and even mutated
across the shared memory.
"""

import sys

print("--- range is O(1) memory with O(1) indexing and membership ---")
r = range(0, 10_000_000, 3)
print("  getsizeof(range(0,10M,3)):", sys.getsizeof(r), "bytes | len:", len(r))
print("  9_999_999 in r          :", 9_999_999 in r)
print("  r[1_000_000]            :", r[1_000_000])
print("  getsizeof(list of 1000) :", sys.getsizeof(list(range(1000))), "bytes")

print()
print("--- dict views are live: they track the dict, they do not snapshot ---")
d = {"a": 1, "b": 2}
ks = d.keys()
d["c"] = 3
print("  view after inserting 'c':", list(ks))

print()
print("--- memoryview slices and edits a buffer with zero copy ---")
data = bytearray(b"system_payload_data")
view = memoryview(data)
sub = view[7:14]
print("  slice          :", sub.tobytes())
sub[0] = ord(b"P")
print("  edit visible in original:", bytes(data))
print()
print("The zero-copy buffer protocol behind memoryview is the foundation of")
print("high-performance I/O and the boundary to C/C++ (Deep A, Deep M).")
