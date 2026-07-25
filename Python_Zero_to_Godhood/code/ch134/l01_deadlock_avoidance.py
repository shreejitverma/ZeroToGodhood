"""Listing 134.1 - avoiding deadlock: consistent lock ordering, and RLock re-entrancy.

A DEADLOCK is two threads each holding one lock and waiting for the other's, forever.
The classic cause is INCONSISTENT lock ordering: thread 1 takes lock A then B, thread 2
takes B then A; if each grabs its first lock and then waits for the second, neither
proceeds. The fix is a GLOBAL ORDER: every thread acquires locks in the SAME order, so
a cycle is impossible. This listing does NOT run a deadlock (it would hang); it runs the
FIXED version (ordered acquisition), which completes deterministically, and shows RLock,
a re-entrant lock the same thread can acquire twice (a plain Lock would self-deadlock).
"""

import threading


lock_a = threading.Lock()
lock_b = threading.Lock()


def worker_ordered(tid, out):
    # ALWAYS acquire lock_a before lock_b (one global order) -> no cycle -> no deadlock
    for _ in range(1000):
        with lock_a:
            with lock_b:
                out.append(tid)


def main() -> None:
    print("--- consistent lock ordering PREVENTS deadlock (this completes) ---")
    out = []
    threads = [threading.Thread(target=worker_ordered, args=(i, out)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"  4 threads x 1000 (a-then-b order) : {len(out)} operations, no hang")
    print(f"  equals 4000 exactly               : {len(out) == 4000}")

    print("--- the deadlock this avoids (described, NOT run) ---")
    print(f"  if thread1 took a-then-b and thread2 took b-then-a, each could hold one")
    print(f"  and wait for the other forever; one global order makes a cycle impossible")

    print("--- RLock: the SAME thread can re-acquire it (a plain Lock would self-deadlock) ---")
    rlock = threading.RLock()
    depth = 0
    with rlock:
        depth += 1
        with rlock:                      # re-entrant: same thread, OK with RLock
            depth += 1
    print(f"  RLock acquired re-entrantly to depth : {depth}   (a Lock would hang here)")

    print("--- the rules ---")
    print(f"  acquire multiple locks in ONE consistent global order (no cycles);")
    print(f"  use RLock only for genuine re-entrancy; keep critical sections small")


if __name__ == "__main__":
    main()
