"""Benchmark 129.1 - a pool over trivial tasks is far SLOWER than a plain loop.

Every task submitted to an executor pays overhead: a Future is created, the task is
queued, dispatched to a worker, and the result is marshalled back. When the task
itself is trivial, that per-task overhead dominates, and (for CPU work) the GIL
serializes the threads anyway. So farming out tiny per-item work to a ThreadPoolExecutor
is much slower than just doing it in a loop. This measures 100,000 trivial tasks both
ways, to show pools are for SUBSTANTIAL tasks, not tiny ones.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 100_000


def trivial(x):
    return x + 1


def main():
    print(f"=== 129.1  {N:,} trivial tasks: plain loop vs ThreadPoolExecutor ===")
    print(provenance())
    print()

    t0 = time.perf_counter()
    serial = [trivial(i) for i in range(N)]
    t_serial = time.perf_counter() - t0

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as ex:
        pooled = list(ex.map(trivial, range(N)))
    t_pool = time.perf_counter() - t0

    print(f"  plain loop           : {t_serial * 1000:7.1f} ms   1.0x")
    print(f"  ThreadPoolExecutor   : {t_pool * 1000:7.1f} ms   {t_pool / t_serial:.0f}x SLOWER")
    print(f"  results identical    : {serial == pooled}")

    print()
    print("Reading this. The pool is far slower here, not faster, because each of the")
    print("100,000 tasks pays Future creation, queueing, and dispatch overhead, while")
    print("the task itself (add one) does almost nothing, and the GIL serializes the")
    print("threads' trivial CPU work anyway. Pools amortize their overhead only when")
    print("each task does SUBSTANTIAL work (a network call, a heavy computation). The")
    print("rule, again, is amortize the boundary: submit a few big tasks, not many")
    print("tiny ones. To parallelize fine-grained work, batch it, hand each worker a")
    print("chunk of items to loop over, so one task does a lot. A plain loop beats a")
    print("pool every time the per-task overhead exceeds the per-task work.")


if __name__ == "__main__":
    main()
