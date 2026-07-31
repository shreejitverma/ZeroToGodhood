"""Listing 269.1 - Python 3.9 (2020): graphlib.TopologicalSorter, dependency ordering in the stdlib.

'Do things in an order that respects dependencies' is everywhere: build targets,
task schedulers, module import order, spreadsheet recalculation, package
installs. The algorithm is a topological sort, and everyone re-implemented it -
usually with a subtle bug in the cycle handling. Python 3.9 added
graphlib.TopologicalSorter: declare each node with the nodes it depends on, and
it produces a valid linear order (dependencies before dependents), detects
cycles as a CycleError, and offers a parallel-execution mode that yields each
group of currently-runnable nodes. Deep volumes own no graph mechanism; this is
the release that made topological ordering batteries-included and correct.
Verified on current interpreters.
"""

from graphlib import TopologicalSorter, CycleError


def main() -> None:
    print("--- declare dependencies; static_order() gives a valid linear order ---")
    ts = TopologicalSorter()
    ts.add("cake", "batter", "oven")             # cake depends on batter and oven
    ts.add("batter", "eggs", "flour")            # batter depends on eggs and flour
    ts.add("oven", "electricity")
    order = list(ts.static_order())
    print(f"  a valid build order : {order}")
    print(f"  eggs before batter  : {order.index('eggs') < order.index('batter')}")
    print(f"  batter before cake  : {order.index('batter') < order.index('cake')}")
    print("  every node appears AFTER the things it depends on. that is a")
    print("  topological sort: a linear order consistent with all dependencies,")
    print("  which is exactly a correct build/execution sequence")

    print("--- add(node, *deps): the dependency direction ---")
    print("  add('cake', 'batter', 'oven') reads 'cake DEPENDS ON batter, oven',")
    print("  so batter and oven come BEFORE cake in the output. you declare what")
    print("  each thing NEEDS; the sorter works out the order")

    print("--- cycles are detected and reported, not looped forever ---")
    cyclic = TopologicalSorter()
    cyclic.add("a", "b")
    cyclic.add("b", "c")
    cyclic.add("c", "a")                          # a -> b -> c -> a : impossible
    try:
        list(cyclic.static_order())
    except CycleError as exc:
        print(f"  a->b->c->a raised CycleError : {exc.args[0]}")
    print("  a dependency cycle has NO valid order, and a hand-rolled sort often")
    print("  loops forever or silently drops nodes on one. TopologicalSorter")
    print("  raises CycleError naming the cycle - the bug most people's version")
    print("  gets wrong")

    print("--- the parallel mode: which nodes are runnable RIGHT NOW ---")
    tp = TopologicalSorter()
    tp.add("cake", "batter", "oven")
    tp.add("batter", "eggs", "flour")
    tp.add("oven", "electricity")
    tp.prepare()
    waves = []
    while tp.is_active():
        ready = tp.get_ready()                    # all nodes with deps satisfied
        waves.append(sorted(ready))
        tp.done(*ready)                           # mark them completed
    print(f"  waves of concurrently-runnable nodes : {waves}")
    print("  get_ready() returns every node whose dependencies are ALL done, so")
    print("  each wave can run in PARALLEL. this is the scheduler interface: run")
    print("  a wave, mark it done, ask what unlocked - the basis of a build")
    print("  system's parallel executor")

    print("--- the constraint answered ---")
    print("  ordering work by dependencies is a universal need and a topological")
    print("  sort, re-implemented everywhere with buggy cycle handling.")
    print("  graphlib.TopologicalSorter (3.9) made it standard: declare deps, get")
    print("  a valid order, get CycleError on impossible graphs, and get a")
    print("  wave-at-a-time parallel scheduler - correct, batteries-included")


if __name__ == "__main__":
    main()
