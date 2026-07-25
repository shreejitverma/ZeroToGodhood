"""Listing 127.1 - threads share memory under the GIL; a lock makes updates safe.

CPython threads are real OS threads, but the Global Interpreter Lock (GIL) ensures
only ONE runs Python bytecode at a time, rotating between them (default every 5 ms,
sys.getswitchinterval()). Two consequences this listing establishes deterministically:
  - Threads SHARE memory: a counter or list is the same object in every thread (unlike
    processes, which copy). So they can cooperate on shared state...
  - ...but a read-modify-write like `counter += 1` is several bytecodes, and the GIL
    can switch between them, so concurrent unsynchronized updates LOSE increments (a
    race). A threading.Lock makes the update atomic, giving the correct total.
This listing shows shared state and the lock-protected correct result. (The GIL's
timing effect, CPU-bound vs IO-bound, is the benchmark.)
"""

import sys
import threading


def main() -> None:
    print("--- the GIL rotates between threads on a fixed interval ---")
    print(f"  sys.getswitchinterval() : {sys.getswitchinterval()} s   (GIL check interval)")

    print("--- threads SHARE memory: the counter is one object in all threads ---")
    counter = 0
    lock = threading.Lock()

    def increment(times):
        nonlocal counter
        for _ in range(times):
            with lock:                       # make read-modify-write atomic
                counter += 1

    workers = [threading.Thread(target=increment, args=(100_000,)) for _ in range(4)]
    for t in workers:
        t.start()
    for t in workers:
        t.join()                             # main thread waits for all workers

    print(f"  4 threads x 100,000 increments (locked) : {counter}")
    print(f"  equals 4 * 100,000 exactly              : {counter == 400_000}")

    print("--- threads append to ONE shared list (lock-protected) ---")
    shared = []
    slock = threading.Lock()

    def append_id(value):
        with slock:
            shared.append(value)

    ts = [threading.Thread(target=append_id, args=(i,)) for i in range(5)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    print(f"  5 threads each appended once : list length {len(shared)}")
    print(f"  all five values present      : {sorted(shared) == [0, 1, 2, 3, 4]}")

    print("--- join() synchronizes: after join, all workers have finished ---")
    print(f"  active threads after all joins : {threading.active_count()}   (just main)")

    print("--- the rule ---")
    print(f"  threads share memory (cooperate on state) but need a Lock for")
    print(f"  read-modify-write; the GIL serializes bytecode, one thread at a time")


if __name__ == "__main__":
    main()
