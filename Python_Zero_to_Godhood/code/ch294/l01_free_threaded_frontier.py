# requires: free-threaded
"""Listing 294.1 - The frontier: living on the free-threaded (no-GIL) build.

Volume 17 introduced the free-threaded build; here at the frontier the question
is practical: how do you KNOW you are on it, and what does your code owe that
world? On a no-GIL build sys._is_gil_enabled() is False and threads run Python
bytecode in genuine parallel - which means the GIL is no longer silently
serialising your shared-state mutations. Code that got away with unsynchronised
updates because the GIL made bytecode steps effectively atomic can now RACE. The
discipline the frontier demands is explicit synchronisation: guard shared mutable
state with a lock. Deep L owns the full model; this chapter is about detecting the
build and respecting its contract. This listing runs only on the free-threaded
build. Verified on the free-threaded build.
"""

import sys
import sysconfig
import threading


def main() -> None:
    print("--- detecting the free-threaded build ---")
    print(f"  sys._is_gil_enabled() : {sys._is_gil_enabled()}")
    print(f"  sysconfig Py_GIL_DISABLED : {sysconfig.get_config_var('Py_GIL_DISABLED')}")
    print("  the GIL is OFF: threads execute Python bytecode truly in parallel.")
    print("  these two checks are how code detects the build at runtime and at")
    print("  build-configuration time respectively")

    print("--- the contract: shared mutable state now needs explicit locking ---")
    counter = 0
    lock = threading.Lock()

    def add_many():
        nonlocal counter
        for _ in range(10000):
            with lock:                           # the lock makes the update safe
                counter += 1

    threads = [threading.Thread(target=add_many) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print(f"  8 threads x 10000 locked increments = {counter}")
    print(f"  the total is exactly correct : {counter == 8 * 10000}")
    print("  `with lock:` serialises the read-modify-write, so no update is lost")
    print("  even with 8 threads running in parallel. this is the discipline the")
    print("  no-GIL world requires - protect shared mutable state yourself")

    print("--- why it matters: the GIL used to hide the race ---")
    print("  `counter += 1` is load, add, store - THREE bytecode steps. under the")
    print("  GIL, a thread rarely lost the CPU mid-sequence, so unsynchronised")
    print("  increments usually (not always) worked. with the GIL gone, two")
    print("  threads can interleave those steps and lose updates. the lock was")
    print("  ALWAYS the correct fix; free-threading makes skipping it visibly wrong")

    print("--- the frontier trade, stated plainly ---")
    print("  free-threading buys real multi-core parallelism for pure-Python")
    print("  CPU-bound work - the thing the GIL denied for 30 years. the price is")
    print("  that you now owe the same thread-safety discipline as C or Java:")
    print("  locks, or immutable/shared-nothing designs (the subinterpreter path,")
    print("  Chapter 287). the GIL's convenience is gone with its limitation")

    print("--- the constraint answered ---")
    print("  at the frontier, free-threading is real: detect it with")
    print("  sys._is_gil_enabled(), and honour its contract by synchronising")
    print("  shared mutable state - the GIL no longer does it for you. genuine")
    print("  parallelism in exchange for genuine thread-safety responsibility.")
    print("  Deep L develops the model; this is the practitioner's version")


if __name__ == "__main__":
    main()
