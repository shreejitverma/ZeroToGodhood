"""Listing 174.1 - build identity, the unchanged API, and what the GIL never promised.

Deep L opens with the ground truth that the rest of the volume stands on. The
free-threaded interpreter is a separate BUILD of CPython, not a runtime switch on
the ordinary one; the threading API is identical on both; per-operation atomicity
on the builtin containers is preserved by per-object locking; and the locking
discipline Deep E taught for compound operations was never optional on any build.

This listing runs on the whole verification matrix: the two GIL builds record one
output, the free-threaded build records its own, and the differences between the
two recordings are exactly the facts this volume is about.
"""

import sys
import sysconfig
import threading

THREADS = 4
PER_THREAD = 100_000


def main() -> None:
    print("--- build identity ---")
    print(f"  compiled with Py_GIL_DISABLED : "
          f"{bool(sysconfig.get_config_var('Py_GIL_DISABLED'))}")
    print(f"  abiflags                      : {sys.abiflags!r}")
    print(f"  sys._is_gil_enabled()         : {sys._is_gil_enabled()}")
    print("  the build is the identity; the runtime state is the report. on the")
    print("  free-threaded build, -X gil=1 can re-enable the GIL for one run, and")
    print("  importing an extension that needs it re-enables it automatically")

    print("--- the API is unchanged, and so is the discipline ---")
    counter = 0
    lock = threading.Lock()

    def add_locked():
        nonlocal counter
        for _ in range(PER_THREAD):
            with lock:
                counter += 1

    workers = [threading.Thread(target=add_locked) for _ in range(THREADS)]
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    print(f"  {THREADS} threads x {PER_THREAD:,} locked increments : {counter:,}")
    print("  same Thread, same Lock, same result on every build: code that locked")
    print("  its compound operations (Chapter 46) does not notice the GIL leaving")

    print("--- single container operations stay atomic ---")
    shared: list[int] = []

    def append_unlocked():
        for i in range(PER_THREAD):
            shared.append(i)

    workers = [threading.Thread(target=append_unlocked) for _ in range(THREADS)]
    for w in workers:
        w.start()
    for w in workers:
        w.join()
    print(f"  {THREADS} threads x {PER_THREAD:,} list.append, no lock : {len(shared):,}")
    print("  on the GIL build the GIL made one append atomic; on the free-threaded")
    print("  build the LIST'S OWN LOCK does (Chapter 96). the guarantee survives;")
    print("  the mechanism providing it changed completely")

    print("--- what the GIL never promised, on any build ---")
    print("  check-then-act and read-modify-write span multiple operations, and no")
    print("  build makes a SEQUENCE atomic: 'counter += 1' unlocked loses updates")
    print("  under the GIL too (Chapter 46 measured it). the free-threaded build")
    print("  raises the frequency of the loss; it does not create the obligation")

    print("--- the two escapes this volume measures ---")
    print("  free-threading  (PEP 703/779) : one interpreter, shared objects, no GIL")
    print("  subinterpreters (PEP 684/734) : isolated interpreters, a GIL each")
    print("  the first buys shared memory and pays per-object coordination; the")
    print("  second buys isolation and pays for every byte that crosses it")


if __name__ == "__main__":
    main()
