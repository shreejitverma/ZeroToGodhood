"""Benchmark 120.1 - refcounting frees acyclic garbage immediately; cycles leak without GC.

With the cyclic collector DISABLED (leaving only reference counting), a loop that
creates and discards ACYCLIC temporaries keeps peak memory flat: each temporary's
refcount hits zero the instant the next iteration rebinds the name, so it is freed
immediately, only one is ever live. The same loop building CYCLIC temporaries (each
referencing itself) leaks every object, because a cycle's refcounts never reach zero,
so peak memory grows without bound. This measures both peaks with gc off.

Memory via tracemalloc. See _harness/bench.py.
"""

import gc
import sys
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 100_000
PAYLOAD = 200          # each temporary carries a list of 200 ints


def main():
    print(f"=== 120.1  {N:,} temporaries, gc OFF: acyclic (freed now) vs cyclic (leaks) ===")
    print(provenance())
    print()

    mb = 1024 * 1024
    gc.disable()       # only reference counting is active now

    tracemalloc.start()
    peak_acyclic = 0
    for _ in range(N):
        obj = {"data": list(range(PAYLOAD))}   # prev obj's refcount -> 0, freed here
        _, peak = tracemalloc.get_traced_memory()
        if peak > peak_acyclic:
            peak_acyclic = peak
    tracemalloc.stop()

    tracemalloc.start()
    peak_cyclic = 0
    for _ in range(N):
        obj = {"data": list(range(PAYLOAD))}
        obj["self"] = obj                       # a cycle: refcount never reaches 0
        _, peak = tracemalloc.get_traced_memory()
        if peak > peak_cyclic:
            peak_cyclic = peak
    tracemalloc.stop()

    gc.enable()

    print(f"  acyclic loop peak : {peak_acyclic / mb:8.2f} MB   (one temporary live at a time)")
    print(f"  cyclic  loop peak : {peak_cyclic / mb:8.1f} MB   (every temporary leaked)")
    print(f"  the cyclic loop holds ~{peak_cyclic // max(peak_acyclic, 1):,}x more")

    print()
    print("Reading this. Reference counting reclaims an object the instant its last")
    print("reference goes away, so the acyclic loop, where each temporary is dropped")
    print("when the next one is bound, never holds more than one object: prompt,")
    print("deterministic, bounded memory with no GC pause. But a cycle keeps its own")
    print("refcounts above zero, so with the cyclic collector off every cyclic")
    print("temporary leaks and memory grows without bound. That is exactly why")
    print("CPython needs BOTH: reference counting for prompt reclamation, and the")
    print("cyclic collector (Chapter 30) to catch what cycles hide from it.")


if __name__ == "__main__":
    main()
