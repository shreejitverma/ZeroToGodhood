"""Listing 130.1 - coordinating threads: queue.Queue and synchronization primitives.

Chapter 46 showed shared mutable state needs a Lock. But hand-locking is error-prone;
the standard library provides higher-level coordination tools:
  - queue.Queue: a thread-safe FIFO for the producer/consumer pattern. put() and get()
    are safe from any thread, get() BLOCKS until an item is available (no busy-waiting),
    and task_done()/join() track completion. This is the recommended way to hand work
    between threads, no explicit locks.
  - threading.Event: a one-bit signal. Threads wait() until another set()s it.
  - threading.Semaphore(n): limits how many threads hold it at once (a concurrency cap).
This listing shows each, deterministically.
"""

import queue
import threading


def main() -> None:
    print("--- queue.Queue: thread-safe producer/consumer (no explicit locks) ---")
    q = queue.Queue()
    results = []

    def producer():
        for i in range(5):
            q.put(i)
        q.put(None)                          # sentinel: tell the consumer to stop

    def consumer():
        while True:
            item = q.get()                   # blocks until an item is available
            if item is None:
                break
            results.append(item * 10)
            q.task_done()

    p = threading.Thread(target=producer)
    c = threading.Thread(target=consumer)
    p.start()
    c.start()
    p.join()
    c.join()
    print(f"  consumer processed items in order : {results}")

    print("--- threading.Event: one thread signals, others wait ---")
    event = threading.Event()
    log = []

    def waiter():
        event.wait()                         # blocks until the event is set
        log.append("released")

    def setter():
        log.append("setting")
        event.set()                          # wakes all waiters

    w = threading.Thread(target=waiter)
    s = threading.Thread(target=setter)
    w.start()
    s.start()
    w.join()
    s.join()
    print(f"  event coordination order : {log}   (waiter released only after set)")
    print(f"  event.is_set()           : {event.is_set()}")

    print("--- threading.Semaphore(2): cap concurrent holders at 2 ---")
    sem = threading.Semaphore(2)
    acquired = [sem.acquire(blocking=False) for _ in range(3)]
    print(f"  three non-blocking acquires of Semaphore(2) : {acquired}   (2 succeed, 1 fails)")

    print("--- the rule ---")
    print(f"  use queue.Queue to hand work between threads (blocking, no locks);")
    print(f"  Event to signal, Semaphore to cap concurrency; prefer these over raw Locks")


if __name__ == "__main__":
    main()
