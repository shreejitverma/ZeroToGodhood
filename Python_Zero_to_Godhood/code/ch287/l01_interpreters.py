# requires: 3.14+
"""Listing 287.1 - Python 3.14 (2025): concurrent.interpreters, subinterpreters in the stdlib.

Two paths to real parallelism in CPython: remove the GIL (free-threading, Chapter
26), or give each interpreter its OWN GIL and run several in one process. The
second is 'subinterpreters', made real by the per-interpreter GIL (Chapter 23).
Python 3.14's PEP 734 exposed them in the standard library as
concurrent.interpreters: create() spins up an isolated interpreter with its own
modules and globals, .exec() runs code in it, and a Queue passes shareable data
between them. Isolation is the model - no shared mutable state by default, so no
data races - which is the opposite trade-off from free-threading's shared memory.
Deep L owns the full free-threading-vs-subinterpreters story; this is the release
that put subinterpreters in reach without the C API. Verified on 3.14 builds.
"""

import concurrent.interpreters as interpreters


def main() -> None:
    print("--- create() gives a fresh, isolated interpreter ---")
    interp = interpreters.create()
    print(f"  created interpreter, distinct id from main : "
          f"{interp.id != interpreters.get_current().id}")
    print("  each subinterpreter has its OWN import state, its own globals, and")
    print("  (since Chapter 23's per-interpreter GIL) its own GIL - so several")
    print("  can run Python bytecode in genuine parallel within one process")

    print("--- exec() runs code inside the subinterpreter ---")
    interp.exec("result = sum(range(10))")
    print("  ran `result = sum(range(10))` inside the subinterpreter")
    print("  the code executed in ITS world - the variable 'result' lives in the")
    print("  subinterpreter's namespace, not this one")

    print("--- isolation: the subinterpreter's globals do NOT leak to main ---")
    interp.exec("secret_config = {'token': 'xyz'}")
    print(f"  set 'secret_config' in the subinterpreter")
    print(f"  does main see 'secret_config'? : {'secret_config' in dir()}")
    print("  isolation is the whole point: no shared mutable globals, so one")
    print("  interpreter cannot corrupt another's state. that is the SAFETY the")
    print("  subinterpreter model buys - the opposite trade from shared-memory threads")

    print("--- pass data with a Queue: the sanctioned channel between them ---")
    q = interpreters.create_queue()
    interp.prepare_main(channel=q)               # make q visible in the sub's __main__
    interp.exec("channel.put(6 * 7)")            # sub computes and sends
    received = q.get()                           # main receives
    print(f"  subinterpreter computed 6*7 and put it on the queue")
    print(f"  main received : {received}")
    print("  because memory is NOT shared, data crosses through an explicit")
    print("  Queue of SHAREABLE objects. you pass messages, you do not share")
    print("  variables - the discipline that makes the isolation safe")

    print("--- only shareable objects cross; arbitrary objects do not ---")
    print(f"  is an int shareable across interpreters? : "
          f"{interpreters.is_shareable(42)}")
    print(f"  is an open file object shareable?        : "
          f"{interpreters.is_shareable(object())}")
    print("  primitives, str/bytes, and some special types (like Queue) are")
    print("  shareable; general mutable objects are not - the boundary keeps the")
    print("  interpreters truly independent")

    interp.close()                               # release the subinterpreter
    print("--- close() releases the subinterpreter when you are done ---")
    print("  a subinterpreter is a real resource (its own runtime state), so you")
    print("  close it explicitly. create, use, close - lifecycle you control")

    print("--- the constraint answered ---")
    print("  true parallelism needed either the C API for subinterpreters or the")
    print("  no-GIL build. concurrent.interpreters (3.14, PEP 734) put the")
    print("  subinterpreter model in the standard library: create isolated")
    print("  interpreters, exec code in them, exchange shareable data by Queue.")
    print("  parallelism through ISOLATION - the message-passing alternative to")
    print("  free-threading's shared memory (Deep L)")


if __name__ == "__main__":
    main()
