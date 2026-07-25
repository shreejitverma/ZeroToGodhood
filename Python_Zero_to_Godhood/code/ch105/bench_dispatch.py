"""Benchmark 105.1 - the operator is not a fast shortcut for the dunder.

Folklore says operators are a fast path. This measures x + y (the full binary-op
protocol: try __add__, on NotImplemented try the reflected __radd__) against
x.__add__(y) (a direct method call that skips the protocol), for a Python class
whose operands match. The operator does MORE work, so it is slightly slower, the
value it adds is the NotImplemented fallback, not speed.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 5_000_000


class V:
    __slots__ = ("n",)

    def __init__(self, n):
        self.n = n

    def __add__(self, o):
        return V(self.n + o.n)


def main():
    print("=== 105.1  x + y (operator protocol) vs x.__add__(y) (direct call) ===")
    print(provenance())
    print()

    a, b = V(1), V(2)

    t_op = min(timeit.repeat(lambda: a + b, number=N, repeat=5)) / N
    t_dun = min(timeit.repeat(lambda: a.__add__(b), number=N, repeat=5)) / N

    print(f"  a + b        (operator protocol)  : {t_op * 1e9:6.1f} ns/call")
    print(f"  a.__add__(b) (direct method call) : {t_dun * 1e9:6.1f} ns/call")
    print(f"  the operator costs ~{t_op / t_dun:.1f}x the direct call")

    print()
    print("Reading this. The operator is slightly SLOWER than calling the dunder")
    print("directly, because x + y runs the binary-op protocol: it invokes")
    print("type(x).__add__, checks for the NotImplemented sentinel, and would try")
    print("the reflected type(y).__radd__ if the first declined. a.__add__(b) skips")
    print("all of that. So the operator does not buy speed; it buys the two-sided")
    print("fallback that lets the right operand cooperate. Call the dunder directly")
    print("only when you have already decided which operand handles it and want no")
    print("fallback; otherwise use the operator and get the protocol.")


if __name__ == "__main__":
    main()
