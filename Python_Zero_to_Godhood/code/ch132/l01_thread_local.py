"""Listing 132.1 - thread-local storage, and which operations are atomic under the GIL.

Two tools for correct threading that AVOID locks:
  - threading.local() gives each thread its OWN copy of an attribute. Threads do not
    share it, so there is nothing to race on and no lock needed. Use it for per-thread
    state (a per-thread connection, buffer, or request context).
  - Some operations are ATOMIC under the GIL, completing in a single, uninterruptible
    bytecode: list.append, a single dict/attribute assignment, list.pop. These need NO
    lock. But read-modify-write (counter += 1, Chapter 46) is SEVERAL bytecodes and is
    NOT atomic, it needs a lock.
Knowing the difference lets you lock only what actually needs it. This listing shows
per-thread storage and a lock-free atomic append giving the correct total.
"""

import threading


_tls = threading.local()                 # one object; each thread sees its own attrs


def main() -> None:
    print("--- threading.local: each thread has its OWN value (no sharing) ---")
    per_thread = {}

    def set_and_read(tid):
        _tls.value = tid * 100           # this thread's own copy
        per_thread[tid] = _tls.value     # (distinct dict keys per thread: atomic)

    threads = [threading.Thread(target=set_and_read, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"  each thread's own _tls.value : {dict(sorted(per_thread.items()))}")
    print(f"  the main thread never set it : {hasattr(_tls, 'value')}   (separate per thread)")

    print("--- list.append is ATOMIC under the GIL: correct WITHOUT a lock ---")
    shared = []

    def appender():
        for _ in range(10_000):
            shared.append(1)             # single atomic bytecode; no lock needed

    workers = [threading.Thread(target=appender) for _ in range(4)]
    for t in workers:
        t.start()
    for t in workers:
        t.join()
    print(f"  4 threads x 10,000 lock-free appends : {len(shared)}")
    print(f"  equals 40,000 exactly (no lost items): {len(shared) == 40_000}")

    print("--- but read-modify-write is NOT atomic (Chapter 46): that needs a lock ---")
    print(f"  atomic (no lock)  : append, pop, single dict/attr assignment")
    print(f"  NOT atomic (lock) : counter += 1, check-then-act, multi-step updates")

    print("--- the rule ---")
    print(f"  use threading.local for per-thread state; lock only compound")
    print(f"  read-modify-write, single append/assignment is already atomic")


if __name__ == "__main__":
    main()
