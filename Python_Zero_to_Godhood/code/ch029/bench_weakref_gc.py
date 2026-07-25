"""Benchmark 29.1 - weakref is a determinism tool, not a throughput optimization.

It is tempting to think a weak back-reference is faster than a strong one because
it avoids the cyclic collector. This benchmark shows the honest picture and
corrects that intuition: creating a weakref has a real per-reference cost, so a
weak back-reference is SLOWER per operation than a strong one, not faster. Its
value is that reclamation is immediate and deterministic (Listing 29.1), and that
the collector never has to trace the object, NOT that the churn is faster.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import weakref

class Node:
    __slots__ = ('link', '__weakref__')

target = Node()
"""


def main() -> None:
    results = [
        measure("strong reference", "for _ in range(1000):\n n = Node(); n.link = target", SETUP, number=2000),
        measure("weak reference  ", "for _ in range(1000):\n n = Node(); n.link = weakref.ref(target)", SETUP, number=2000),
    ]
    report("29.1  per-reference cost: strong vs weak",
           results, baseline="strong reference")

    print()
    print("Reading this. Creating a weak reference costs several times a plain")
    print("attribute assignment, because it allocates a weakref object and")
    print("registers it with the referent. So a weak back-reference is not a")
    print("speed win; it is a CORRECTNESS and DETERMINISM tool. Use it to break a")
    print("parent-child cycle so refcounting reclaims both immediately (Listing")
    print("29.1), to build a cache that does not keep its contents alive")
    print("(WeakValueDictionary), or to observe an object's death (a callback).")
    print("Do not scatter weakrefs through a hot path expecting them to be free:")
    print("they are not. The right frame is Chapter 3's, avoid the cycle rather")
    print("than pay the collector, and weakref is how you avoid it when you must,")
    print("accepting a small per-reference cost for deterministic cleanup.")


if __name__ == "__main__":
    main()
