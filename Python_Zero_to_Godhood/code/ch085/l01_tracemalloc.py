"""Listing 85.1 - tracemalloc: find WHERE memory is allocated (and what leaks).

To debug a memory leak or a fat resident set, you need to know which LINES
allocate the memory. tracemalloc records the allocation site (a traceback) for
every allocation, so a snapshot tells you the top allocators, and comparing two
snapshots (compare_to) tells you what GREW between them, the leak-finding
technique. The cost is high (it hooks every allocation; the benchmark measures
~10x), so it is a diagnose-then-disable tool, not a production setting. This
listing shows locating the top allocation site and diffing snapshots, reporting
DETERMINISTIC facts (which line, how many objects), not noisy byte counts.
"""

import tracemalloc


def build(n):
    return [[0] * 100 for _ in range(n)]     # n lists of 100 ints each


def top_site_in_this_file(diff):
    grower = max(diff, key=lambda s: s.size_diff)
    return __file__ in grower.traceback[0].filename, grower.traceback[0].lineno


def main() -> None:
    tracemalloc.start()
    print(f"  tracing enabled : {tracemalloc.is_tracing()}")

    before = tracemalloc.take_snapshot()
    data = build(1000)                        # the allocation we want to locate
    after = tracemalloc.take_snapshot()

    print("--- compare_to finds what grew between the snapshots ---")
    diff = after.compare_to(before, "lineno")
    in_file, line = top_site_in_this_file(diff)
    print(f"  top grower is in this file : {in_file}")
    print(f"  it is the build() line     : {line == build.__code__.co_firstlineno + 1}")
    print(f"  the structure built        : {len(data)} lists of {len(data[0])} ints")

    print("--- current traced memory is nonzero while data is alive ---")
    current, peak = tracemalloc.get_traced_memory()
    print(f"  current > 0 : {current > 0}")
    print(f"  peak >= current : {peak >= current}")

    tracemalloc.stop()
    print(f"  tracing after stop : {tracemalloc.is_tracing()}")
    print("  (enable to diagnose a leak, read the top growers, then disable)")


if __name__ == "__main__":
    main()
