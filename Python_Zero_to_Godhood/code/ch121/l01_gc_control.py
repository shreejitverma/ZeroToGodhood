"""Listing 121.1 - the gc module: controlling the cyclic collector.

The gc module exposes the cyclic collector (Chapter 30) that supplements reference
counting (Chapter 31). Key facts this listing establishes, all version-stable:
  - gc.collect() runs a full collection and RETURNS the number of unreachable
    objects it reclaimed (here, a 2-object cycle -> 2).
  - The collector only TRACKS container objects (things that can hold references
    and thus form cycles); atomic objects like ints and strings are never tracked.
  - There are THREE generations (young to old), the basis of the generational
    algorithm.
  - gc.disable()/enable() turn the collector off and on (reference counting keeps
    running regardless).
"""

import gc


def main() -> None:
    print("--- gc.collect() reclaims cycles and returns how many objects it freed ---")
    gc.collect()                         # clear any pending garbage first
    gc.collect()

    class Node:
        pass

    a, b = Node(), Node()
    a.peer = b
    b.peer = a                           # a 2-object reference cycle
    del a, b                             # unreachable, but refcounts stuck (Chapter 31)
    reclaimed = gc.collect()
    print(f"  gc.collect() reclaimed : {reclaimed}   (the two cycle nodes)")

    print("--- the collector tracks only CONTAINER objects (potential cycle members) ---")
    print(f"  gc.is_tracked([1])      : {gc.is_tracked([1])}   (a list can hold references)")
    print(f"  gc.is_tracked({{'k': []}}) : {gc.is_tracked({'k': []})}   (a dict can)")
    print(f"  gc.is_tracked(1)        : {gc.is_tracked(1)}   (an int cannot form a cycle)")
    print(f"  gc.is_tracked('s')      : {gc.is_tracked('s')}   (nor a str)")

    print("--- three generations underpin the generational algorithm ---")
    print(f"  number of generations : {len(gc.get_stats())}")

    print("--- disable/enable the collector (reference counting is unaffected) ---")
    gc.disable()
    print(f"  after gc.disable() : gc.isenabled() = {gc.isenabled()}")
    gc.enable()
    print(f"  after gc.enable()  : gc.isenabled() = {gc.isenabled()}")

    print("--- the rule ---")
    print(f"  gc controls the CYCLIC collector: collect() reclaims cycles, it tracks")
    print(f"  only containers, uses 3 generations, and can be disabled independently")


if __name__ == "__main__":
    main()
