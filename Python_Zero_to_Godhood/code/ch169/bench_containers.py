"""Benchmark 169.1 - what the container choice is worth, at a size where it shows.

Listing 169.1 counted the operations. This times them, at one size, for three access
patterns where the wrong container is the most common Python performance bug:

  169.1a  membership. list scan against set, dict, and bisect on a sorted list.
  169.1b  work at the FRONT of a sequence. list against collections.deque.
  169.1c  repeatedly taking the smallest item. re-sorting, min() over a list, and heapq.

The point of each table is not the winner, which the cost model already predicted. It is
the SIZE of the gap, because that is what decides whether a one-line change is worth
making. A factor of two is a judgement call; a factor of a thousand is not.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

N = 10_000
FRONT_OPS = 5_000
EXTRACTS = 1_000

MEMBERSHIP_SETUP = f"""
import bisect
N = {N}
as_list = list(range(N))
as_set = set(as_list)
as_dict = {{value: value for value in as_list}}
as_sorted = sorted(as_list)
missing = N + 1


def bisect_contains(seq, value):
    index = bisect.bisect_left(seq, value)
    return index < len(seq) and seq[index] == value
"""

FRONT_SETUP = f"""
from collections import deque
OPS = {FRONT_OPS}


def list_front():
    out = []
    for i in range(OPS):
        out.insert(0, i)
    while out:
        out.pop(0)
    return len(out)


def deque_front():
    out = deque()
    for i in range(OPS):
        out.appendleft(i)
    while out:
        out.popleft()
    return len(out)
"""

SMALLEST_SETUP = f"""
import heapq
N = {N}
EXTRACTS = {EXTRACTS}
source = [(i * 7919) % N for i in range(N)]


def resort_each_time():
    data = list(source)
    taken = 0
    for _ in range(EXTRACTS):
        data.sort()
        taken += data.pop(0)
    return taken


def min_then_remove():
    data = list(source)
    taken = 0
    for _ in range(EXTRACTS):
        smallest = min(data)
        data.remove(smallest)
        taken += smallest
    return taken


def with_a_heap():
    data = list(source)
    heapq.heapify(data)
    taken = 0
    for _ in range(EXTRACTS):
        taken += heapq.heappop(data)
    return taken
"""


def main():
    membership = [
        measure("x in set", "missing in as_set", MEMBERSHIP_SETUP),
        measure("x in dict", "missing in as_dict", MEMBERSHIP_SETUP),
        measure("bisect on a sorted list", "bisect_contains(as_sorted, missing)",
                MEMBERSHIP_SETUP),
        measure("x in list", "missing in as_list", MEMBERSHIP_SETUP, number=2_000),
    ]
    report(f"169.1a  one membership test against {N:,} items", membership,
           baseline="x in set")

    print()
    front = [
        measure("deque appendleft/popleft", "deque_front()", FRONT_SETUP,
                repeat=7, number=20),
        measure("list insert(0)/pop(0)", "list_front()", FRONT_SETUP,
                repeat=7, number=20),
    ]
    report(f"169.1b  {FRONT_OPS:,} pushes then {FRONT_OPS:,} pops at the FRONT",
           front, baseline="deque appendleft/popleft")

    print()
    smallest = [
        measure("heapq", "with_a_heap()", SMALLEST_SETUP, repeat=5, number=5),
        measure("min() then remove()", "min_then_remove()", SMALLEST_SETUP,
                repeat=5, number=5),
        measure("sort, then pop(0)", "resort_each_time()", SMALLEST_SETUP,
                repeat=5, number=5),
    ]
    report(f"169.1c  take the {EXTRACTS:,} smallest of {N:,}, one at a time",
           smallest, baseline="heapq")

    print()
    print("Reading this. The membership table is the one to internalise, because the")
    print("linear row is the most common accidental quadratic in Python: a list scan")
    print("inside a loop. Building the set costs one linear pass and every subsequent")
    print("lookup is constant, so the set wins outright unless you look something up")
    print("exactly once. bisect sits between them and is the right answer only when you")
    print("need order as well - a nearest-match or a range query, which a set cannot do.")
    print()
    print("The front-operations table is the same argument in a different shape. A list")
    print("is an array: inserting at the front moves every element. A deque is a linked")
    print("list of blocks and does not. Neither is 'faster'; they have different")
    print("exponents for this operation and the same exponent for iteration.")
    print()
    print("The smallest-item table shows the cost of an unnecessary invariant. Re-sorting")
    print("maintains total order when only the minimum was needed. A heap maintains just")
    print("enough order to answer that one question, which is why it is the answer to a")
    print("priority queue and the wrong answer to 'give me the items in order'.")


if __name__ == "__main__":
    main()
