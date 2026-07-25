"""Benchmark 61.1 - interning deduplicates repeated strings in memory.

Holding N copies of the same string VALUE, built at runtime (so not
auto-interned), each copy is a separate string object. sys.intern makes them all
share one object, so the list holds N pointers to a single string instead of N
distinct strings. For data with many repeated string values (field names,
categorical columns, tokens) the memory saving is large. This measures the held
memory of N distinct-but-equal strings vs N interned ones.

Memory via tracemalloc (deterministic). See _harness/bench.py.
"""

import sys
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 200_000


def make():
    return "".join(["user", "_", "id"])   # runtime-built 'user_id', distinct object


def held(build_list):
    tracemalloc.start()
    obj = build_list()
    current, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del obj
    return current


def main():
    print("=== 61.1  interning N repeated strings: distinct vs shared ===")
    print(provenance())
    print()

    plain = held(lambda: [make() for _ in range(N)])
    interned = held(lambda: [sys.intern(make()) for _ in range(N)])

    print(f"  value repeated           : {make()!r} ({len(make())} chars)")
    print(f"  {N:,} distinct equal      : {plain:>12,} bytes")
    print(f"  {N:,} interned (shared)   : {interned:>12,} bytes")
    print(f"  ratio                    : {plain / interned:>12.1f}x")

    print()
    print("Reading this. Without interning each equal string is its own ~50-byte")
    print("object, so N copies cost N objects. Interning collapses them to a single")
    print("shared object; the list then holds only N pointers to it. For data with")
    print("many repeated string values, interning cuts memory substantially. The")
    print("comparison speedup people associate with interning is modest on modern")
    print("CPython (== already fast-paths length and memcmp); the durable win is")
    print("MEMORY. Intern high-cardinality-of-copies, low-cardinality-of-values")
    print("strings (keys, categories); do not intern unique or short-lived ones.")


if __name__ == "__main__":
    main()
