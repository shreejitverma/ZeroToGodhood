"""Benchmark 108.1 - hash quality is the difference between O(1) and O(n).

A set relies on __hash__ scattering elements across buckets so membership is O(1).
Two classes, identical except for __hash__: one returns hash(self.v) (distributes),
the other returns a constant 0 (every element collides into one bucket, so the set
degrades to a linear scan). Membership is timed on a set of 2,000 elements. The
constant-hash version is dramatically slower, and the gap grows with n.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 2000
REPS = 2000


class Good:
    def __init__(self, v):
        self.v = v

    def __eq__(self, other):
        return type(other) is Good and self.v == other.v

    def __hash__(self):
        return hash(self.v)             # distributes across buckets: O(1)


class Bad:
    def __init__(self, v):
        self.v = v

    def __eq__(self, other):
        return type(other) is Bad and self.v == other.v

    def __hash__(self):
        return 0                        # all collide into one bucket: O(n)


def probe(cls):
    s = {cls(i) for i in range(N)}
    target = cls(N // 2)                 # a real member, mid-set
    t0 = time.perf_counter()
    for _ in range(REPS):
        target in s
    return (time.perf_counter() - t0) / REPS


def main():
    print(f"=== 108.1  set membership on {N:,} elements: good __hash__ vs constant __hash__ ===")
    print(provenance())
    print()

    t_good = probe(Good)
    t_bad = probe(Bad)

    print(f"  good __hash__ (distributes) : {t_good * 1e9:8.0f} ns/lookup   1x      (O(1))")
    print(f"  constant __hash__ (collides): {t_bad * 1e9:8.0f} ns/lookup   {t_bad / t_good:.0f}x   (O(n))")

    print()
    print("Reading this. A set finds an element by hashing it to a bucket and")
    print("checking only that bucket. A good __hash__ scatters elements so buckets")
    print("stay tiny and membership is O(1). A constant __hash__ satisfies the")
    print("invariant (equal objects still hash equal) but funnels EVERY element into")
    print("one bucket, so membership becomes a linear scan, hundreds of times slower")
    print("here at 2,000 elements and worse as the set grows. A correct __hash__ is")
    print("not enough; it must also distribute. Derive it from the same fields your")
    print("__eq__ uses (hash of a tuple of them), which distributes for free.")


if __name__ == "__main__":
    main()
