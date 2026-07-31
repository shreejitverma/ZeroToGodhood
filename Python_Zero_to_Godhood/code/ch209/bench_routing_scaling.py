"""Benchmark 209.1 - linear routing vs a trie: where the crossover actually is.

Dispatch one request against route tables of 10, 100, and 1,000 routes, two
ways: the linear list (try each compiled regex until one matches, worst case
= last route) and a segment trie (walk the path's segments down a dict tree,
O(segments) regardless of table size). The linear scan's worst case grows
with the table; the trie's does not. The table shows the crossover - and its
lesson is that for the route counts real services have (tens), linear's
simplicity beats the trie's asymptotics, exactly Chapter 168's constants-vs-
complexity argument at the web layer.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402


def build_linear(n):
    routes = []
    for i in range(n):
        routes.append((re.compile(f"^/resource{i}/(?P<id>[0-9]+)$"), i))
    return routes


def dispatch_linear(routes, path):
    for regex, handler in routes:
        m = regex.match(path)
        if m:
            return handler
    return None


def build_trie(n):
    root = {}
    for i in range(n):
        node = root.setdefault(f"resource{i}", {})
        node.setdefault(":id", {})["$"] = i
    return root


def dispatch_trie(root, path):
    node = root
    params = {}
    for seg in path.strip("/").split("/"):
        if seg in node:
            node = node[seg]
        elif ":id" in node and seg.isdigit():
            params["id"] = int(seg)
            node = node[":id"]
        else:
            return None
    return node.get("$")


def best(fn, repeat=7):
    times = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        for _ in range(50_000):
            fn()
        times.append(time.perf_counter() - t0)
    return min(times) / 50_000 * 1e9


def main():
    print("=== 209.1  dispatch one request, by table size ===")
    print(provenance())
    print("method      : worst-case path (matches the LAST route); min of 7")
    print()
    print("  routes   linear (ns)   trie (ns)")
    print("  ---------------------------------")
    for n in (10, 100, 1_000):
        linear = build_linear(n)
        trie = build_trie(n)
        target = f"/resource{n - 1}/99"          # the last route: linear worst case
        lin_ns = best(lambda: dispatch_linear(linear, target))
        tr_ns = best(lambda: dispatch_trie(trie, target))
        print(f"  {n:>6}   {lin_ns:>11,.0f}   {tr_ns:>9,.0f}")

    print()
    print("Reading this. The linear scan's worst case grows with the table -")
    print("it may try every regex - while the trie is flat, deciding on the")
    print("path's own segments. But read the small-N row: at 10 routes the")
    print("linear scan is already sub-microsecond, and a service with 10 to")
    print("50 routes that then queries a database spends a thousand times")
    print("longer on the query than on any router. So most frameworks ship")
    print("linear (or lightly optimised linear) and are right to: the trie's")
    print("asymptotic win is real and irrelevant until routes reach the")
    print("hundreds AND routing is a measured hot path - Chapter 168's")
    print("'complexity beats constants, once the constants stop mattering',")
    print("with the web's usual answer that they never start.")


if __name__ == "__main__":
    main()
