# requires: 3.14+
"""Listing 179.1 - subinterpreters: isolation as the concurrency primitive.

The volume's other escape (Chapter 93): instead of removing the GIL, PEP 684
gave every interpreter its OWN GIL, and PEP 734 (Python 3.14) exposed multiple
interpreters per process as `concurrent.interpreters`. Nothing is shared, so
nothing from Chapters 94 to 97 is needed: no biased refcounts, no per-object
locks, no stop-the-world across workers. The costs move to the boundary, and
this listing shows the boundary's three rules: namespaces are isolated,
crossing values are copied, and only "shareable" primitives cross without a
copy. The prices are in bench_interpreter_scaling.py.
"""

import sys
import concurrent.interpreters as interpreters

FLAG = "main"


def main() -> None:
    print("--- isolation: a namespace, a module system, an interpreter each ---")
    child = interpreters.create()
    queue = interpreters.create_queue()
    child.prepare_main(q=queue)

    child.exec("FLAG = 'child'")
    print(f"  child set FLAG='child'; main's FLAG is still : {FLAG!r}")

    child.exec("import sys; q.put('dis' in sys.modules)")
    import dis  # noqa: F401  (imported in main only)
    print(f"  'dis' imported in main; imported in child too : {queue.get()}")
    child.exec("q.put(6 * 7)")
    print(f"  code runs in the child and answers over a queue : {queue.get()}")
    print("  same process, separate worlds: globals, sys.modules, and the GIL")
    print("  are all per-interpreter (PEP 684)")

    print("--- what crosses without a copy: the shareable types ---")
    for value in (42, "text", b"bytes", (1, "a"), None, True,
                  [1, 2], {"k": 1}, object()):
        print(f"  is_shareable({type(value).__name__:<8}) : "
              f"{interpreters.is_shareable(value)}")
    print("  shareable values cross by value-identity, safely, lock-free;")
    print("  everything else is COPIED (pickled) across the boundary")

    print("--- crossing is copying, demonstrated ---")
    original = [1, 2, 3]
    queue.put(original)                 # unshareable: the queue pickles it
    returned = queue.get()
    print(f"  a list makes the round trip equal   : {returned == original}")
    print(f"  ...but it is a different object     : {returned is not original}")
    print("  no aliasing can exist across interpreters, so no data race can;")
    print("  isolation buys Chapter 99's whole problem away, at a copy per value")

    print("--- each interpreter has its own lock ---")
    child.exec("import sys; q.put(sys._is_gil_enabled())")
    print(f"  the child's own GIL is enabled : {queue.get()}")
    child.close()
    print("  four interpreters mean four GILs mean four cores (the benchmark's")
    print("  subject) - parallelism WITHOUT the free-threaded build")


if __name__ == "__main__":
    main()
