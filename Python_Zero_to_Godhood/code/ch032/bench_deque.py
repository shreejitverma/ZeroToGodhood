"""Benchmark 32.1 - deque is O(1) at both ends; list is O(n) at the left.

A list stores its elements in a contiguous array, so inserting or removing at the
front shifts every other element: O(n). A deque is a doubly-linked list of
blocks, so both ends are O(1). This benchmark measures a left-insert-and-remove
at two list sizes, and the growing ratio is the O(n) vs O(1) difference made
visible.

Coarse-grained timing done directly; provenance header reused from the harness.
"""

import sys
import time
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402


def deque_ns(n, iters=20000):
    dq = deque(range(n))
    t0 = time.perf_counter()
    for _ in range(iters):
        dq.appendleft(1)
        dq.popleft()
    return (time.perf_counter() - t0) / iters * 1e9


def list_ns(n, iters=5000):
    li = list(range(n))
    t0 = time.perf_counter()
    for _ in range(iters):
        li.insert(0, 1)
        li.pop(0)
    return (time.perf_counter() - t0) / iters * 1e9


def main():
    print("=== 32.1  left insert+remove: deque (O(1)) vs list (O(n)) ===")
    print(provenance())
    print("method      : appendleft+popleft vs insert(0)+pop(0), ns/op")
    print()

    print(f"  {'n':>6}   {'deque ns':>10}   {'list ns':>10}   {'ratio':>6}")
    for n in (100, 1000, 4000):
        d = min(deque_ns(n) for _ in range(3))
        li = min(list_ns(n) for _ in range(3))
        print(f"  {n:>6}   {d:>10.0f}   {li:>10.0f}   {li / d:>5.0f}x")

    print()
    print("Reading this. The deque time is flat, it does not care how big the")
    print("deque is, because appendleft touches only the front block: O(1). The")
    print("list time grows with n, because insert(0) shifts every element: O(n).")
    print("So the ratio widens as the container grows. Use a deque for a queue,")
    print("a sliding window, or anything with front-end operations; a list is")
    print("fine only when you append and pop at the RIGHT end.")


if __name__ == "__main__":
    main()
