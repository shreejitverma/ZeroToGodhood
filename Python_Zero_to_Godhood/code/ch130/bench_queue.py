"""Benchmark 130.1 - queue.Queue's blocking machinery costs more than a bare deque.

queue.Queue is a thread-safe FIFO built ON a collections.deque, plus locks and
condition variables that implement blocking get/put, maxsize, and task_done/join.
collections.deque's own append/popleft are already atomic (thread-safe) in CPython,
with none of that machinery. So for a simple thread-safe queue with no blocking
semantics, a deque is much cheaper. This measures a put+get pair each way, to show
what queue.Queue's coordination features cost.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import collections
import queue
import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 2_000_000


def main():
    print("=== 130.1  put+get pair: queue.Queue vs collections.deque ===")
    print(provenance())
    print()

    q = queue.Queue()
    d = collections.deque()

    t_q = min(timeit.repeat(lambda: (q.put(1), q.get()), number=N, repeat=5)) / N
    t_d = min(timeit.repeat(lambda: (d.append(1), d.popleft()), number=N, repeat=5)) / N

    print(f"  collections.deque append+popleft : {t_d * 1e9:6.0f} ns   1.0x")
    print(f"  queue.Queue put+get              : {t_q * 1e9:6.0f} ns   {t_q / t_d:.0f}x")

    print()
    print("Reading this. queue.Queue is ~20x more expensive than a bare deque, and")
    print("that cost buys its coordination features: a get() that BLOCKS until an item")
    print("arrives (no busy-waiting), a maxsize that blocks put() when full, and")
    print("task_done()/join() to await completion, all via internal locks and")
    print("condition variables. collections.deque gives you thread-safe append/popleft")
    print("(atomic in CPython) with none of that. So: use queue.Queue when you need")
    print("the BLOCKING producer/consumer semantics (a consumer that waits for work);")
    print("use a deque when you only need a fast thread-safe FIFO and will coordinate")
    print("availability yourself. Pay for the blocking machinery only when you use it.")


if __name__ == "__main__":
    main()
