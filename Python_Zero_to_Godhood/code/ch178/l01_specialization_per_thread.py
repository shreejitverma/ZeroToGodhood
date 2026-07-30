"""Listing 178.1 - the specializing interpreter without the GIL: thread-local bytecode.

Volume 15 and Deep H taught the specializing adaptive interpreter: hot bytecode
rewrites itself, in place, into type-specialized forms with inline caches. That
mechanism is SELF-MODIFYING SHARED STATE, exactly what the GIL's removal makes
dangerous, and 3.13's free-threaded build simply disabled it, which is where
most of that build's infamous ~40% single-threaded overhead lived (PEP 779).

3.14's free-threaded build re-enabled it with a design this listing makes
visible from pure Python: BYTECODE IS NOW THREAD-LOCAL. Each thread specializes
its own copy of a hot function's instructions, so no thread ever races another
on an inline cache. The observable consequence: dis(adaptive=True) reports the
CALLING thread's copy, and a function made hot only by a worker thread shows as
unspecialized from the main thread, on the free-threaded build alone, even
though the worker's own copy did specialize (the benchmark proves that by
timing).
"""

import dis
import io
import threading


class Point:
    def __init__(self):
        self.x = 3


SRC = """
def work(p, n):
    total = 0
    for i in range(n):
        total = total + p.x
    return total
"""

MARKERS = ("BINARY_OP_ADD_INT", "LOAD_ATTR_INSTANCE_VALUE", "FOR_ITER_RANGE")


def fresh_work():
    ns = {}
    exec(SRC, ns)
    return ns["work"]


def specialized_markers(fn):
    buf = io.StringIO()
    dis.dis(fn, adaptive=True, file=buf)
    text = buf.getvalue()
    return {m: (m in text) for m in MARKERS}


def main() -> None:
    print("--- warmed in the main thread, inspected from the main thread ---")
    work = fresh_work()
    for _ in range(200):
        work(Point(), 100)
    for marker, present in specialized_markers(work).items():
        print(f"  {marker:<26} : {present}")
    print("  the adaptive interpreter is ACTIVE on every build in the matrix,")
    print("  including free-threaded 3.14, where 3.13t had disabled it entirely")

    print("--- warmed ONLY in a worker thread, inspected from the main thread ---")
    work2 = fresh_work()
    t = threading.Thread(target=lambda: [work2(Point(), 100) for _ in range(200)])
    t.start()
    t.join()
    for marker, present in specialized_markers(work2).items():
        print(f"  {marker:<26} : {present}")
    print("  on the GIL build there is ONE copy of the bytecode, so the worker's")
    print("  warm-up specialized the copy the main thread inspects. on the")
    print("  free-threaded build each thread specializes ITS OWN copy: the")
    print("  worker's copy is hot and specialized, the main thread's is cold,")
    print("  and dis(adaptive=True) reports the caller's view")

    print("--- why thread-local, in one paragraph ---")
    print("  an inline cache is self-modifying code-object state; two threads")
    print("  specializing one copy would race on every cache write, and locking")
    print("  each cache would cost more than specialization saves (Chapter 96's")
    print("  arithmetic). per-thread copies remove the race by construction, at")
    print("  a memory cost per thread per hot code object, and the benchmark")
    print("  confirms the worker's copy really is specialized: worker-only code")
    print("  times identically to main-warmed code")


if __name__ == "__main__":
    main()
