"""Listing 180.1 - correctness that survives both builds, by construction.

Chapter 99 is the discipline chapter: what to write so that the question "is
this safe on the free-threaded build?" never needs asking. Every pattern here
is exact and deterministic on every interpreter in the matrix, because each one
either shares nothing, shares only immutables, or crosses a synchronisation
edge that establishes ordering. The broken patterns, and how often they break
per build, are bench_race_lab.py's subject, because a loss RATE is a
distribution, not a fact a listing can record.
"""

import queue
import threading

THREADS = 4
PER_THREAD = 100_000


def main() -> None:
    print("--- partition and merge: the pattern that cannot race ---")
    totals = [0] * THREADS

    def count_into(slot):
        mine = 0                      # thread-private accumulator
        for _ in range(PER_THREAD):
            mine += 1
        totals[slot] = mine           # one write into a private slot

    workers = [threading.Thread(target=count_into, args=(i,))
               for i in range(THREADS)]
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    print(f"  4 private counters, summed after join : {sum(totals):,}")
    print("  no shared mutable state exists during the work, so there is")
    print("  nothing to protect; join() is the synchronisation edge that makes")
    print("  the final reads safe. exact on every build, and the FASTEST")
    print("  correct pattern in the benchmark")

    print("--- hand-off through a Queue: sharing with the lock built in ---")
    channel: queue.Queue = queue.Queue()
    DONE = object()

    def produce():
        for i in range(1_000):
            channel.put(i)
        channel.put(DONE)

    received = 0
    count = 0

    def consume():
        nonlocal received, count
        while (item := channel.get()) is not DONE:
            received += item
            count += 1

    p = threading.Thread(target=produce)
    c = threading.Thread(target=consume)
    p.start(); c.start(); p.join(); c.join()
    print(f"  1,000 items produced, consumed : {count:,}, sum {received:,}")
    print("  a Queue is a lock, a buffer, and a happens-before edge in one")
    print("  object: whatever the producer did before put() is visible to the")
    print("  consumer after get(). ownership transfers; it is never shared")

    print("--- publish with an edge, never with time ---")
    ordered = True
    for _ in range(50):
        payload = {}
        ready = threading.Event()

        def publish():
            payload["value"] = 42     # write BEFORE the edge
            ready.set()               # the edge

        def read(out=[]):             # noqa: B006
            ready.wait()              # the matching edge
            out.append(payload.get("value"))

        seen: list = []
        w = threading.Thread(target=publish)
        r = threading.Thread(target=read, args=(seen,))
        r.start(); w.start(); w.join(); r.join()
        ordered &= (seen == [42])
    print(f"  50 rounds of set-then-wait, reader always saw the write : {ordered}")
    print("  Event, Lock, Queue, Barrier, and join() are ordering edges; a")
    print("  sleep() is a bet. Python has no formal memory model, so the")
    print("  portable rule is: no shared read is ordered unless an edge orders it")

    print("--- the discipline, in four lines ---")
    print("  1  do not share: partition and merge, or isolate (Chapter 98)")
    print("  2  share immutables: constants, frozen data, immortals (Chapter 94)")
    print("  3  mutate behind ONE owner: a Lock, a Queue, or a single thread")
    print("  4  test on the free-threaded build: the GIL build cannot surface")
    print("     call-free races AT ALL, at any switch interval (the benchmark)")


if __name__ == "__main__":
    main()
