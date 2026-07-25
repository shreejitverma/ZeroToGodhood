"""Listing 123.1 - finding a memory leak with tracemalloc.

A "leak" in Python is usually a reference you did not mean to keep (Chapter 31): an
object still reachable from some long-lived container, so refcounting correctly keeps
it alive. tracemalloc finds WHERE that memory was allocated. The pattern:
  1. tracemalloc.start()
  2. take a snapshot
  3. run the suspect code
  4. take another snapshot
  5. snapshot2.compare_to(snapshot1, 'lineno') -> the lines that GREW, biggest first
The top entry points straight at the allocation site of the growth. This listing
plants a leak (a module list that keeps growing) and locates it. Output is reported
as portable booleans (exact byte counts and file paths are machine-specific).
"""

import tracemalloc

_LEAK = []                               # a module-level list: whatever we append lives forever


def leaky():
    _LEAK.append([0] * 1000)             # THIS line is the leak: appends to the global list


def main() -> None:
    tracemalloc.start()

    print("--- snapshot, run suspect code, snapshot again ---")
    before = tracemalloc.take_snapshot()
    for _ in range(100):
        leaky()                          # 100 lists appended to _LEAK, never freed
    after = tracemalloc.take_snapshot()

    print("--- compare_to shows which LINES grew, biggest first ---")
    growth = after.compare_to(before, "lineno")
    top = growth[0]                      # the largest single-line growth

    print(f"  memory grew at the top line     : {top.size_diff > 0}")
    print(f"  the top growth is in THIS file   : {top.traceback[0].filename == __file__}")
    print(f"  new allocation blocks there >= 100 : {top.count_diff >= 100}")

    print("--- get_traced_memory reports current and peak ---")
    current, peak = tracemalloc.get_traced_memory()
    print(f"  current <= peak (both tracked)   : {current <= peak}")
    print(f"  peak is positive                 : {peak > 0}")

    tracemalloc.stop()

    print("--- the rule ---")
    print(f"  snapshot -> run -> snapshot -> compare_to('lineno'); the top entry is")
    print(f"  the allocation site of the growth. The fix is dropping the stray reference")


if __name__ == "__main__":
    main()
