"""Listing 167.1 - call counts and time rank disagree, and that is the whole problem.

The instinct when a program is slow is to look for the function that is CALLED the most.
That instinct is wrong often enough to be dangerous, because a profile has two orderings
and they answer different questions:

  ncalls   how often a function ran
  tottime  time spent INSIDE it, excluding what it called   <- what to optimise
  cumtime  time spent inside it AND everything it called    <- where to look first

This program is built so the two orderings disagree by construction. `cheap` is called a
thousand times and does almost nothing. `hot_leaf` is called once and does all the work.
Ranking by call count points at `cheap`; ranking by tottime points at `hot_leaf`. Only
one of those is worth a morning.

The listing reports RANKS and CALL COUNTS, which are deterministic, rather than times,
which are not. That is the same discipline the chapter argues for when reading a real
profile: the numbers move between runs, the ordering and the structure do not.
"""

import cProfile
import pstats


def hot_leaf(n):
    """Called once. Does essentially all of the program's work."""
    total = 0
    for i in range(n):
        total += i * i
    return total


def wrapper(n):
    """Called once. Its own body is trivial; its cumtime is hot_leaf's."""
    return hot_leaf(n)


def cheap(x):
    """Called a thousand times. Costs almost nothing each time."""
    return x + 1


def workload(n, calls):
    result = wrapper(n)
    for i in range(calls):
        result = cheap(result)
    return result


def profile(fn, *args):
    profiler = cProfile.Profile()
    profiler.enable()
    fn(*args)
    profiler.disable()
    return pstats.Stats(profiler)


def rows(stats, names):
    """(name, ncalls, tottime, cumtime) for the functions defined in this file."""
    out = {}
    for (_, _, func), entry in stats.stats.items():
        if func in names:
            calls, _, tottime, cumtime, _ = entry
            out[func] = (calls, tottime, cumtime)
    return out


def rank(table, index):
    """Function names ordered by one column, largest first."""
    return [name for name, _ in sorted(table.items(), key=lambda kv: (-kv[1][index], kv[0]))]


def main() -> None:
    names = {"hot_leaf", "wrapper", "cheap", "workload"}
    stats = profile(workload, 400_000, 1_000)
    table = rows(stats, names)

    print("--- how often each function ran ---")
    for name in ("workload", "wrapper", "hot_leaf", "cheap"):
        print(f"  {name:<10} ncalls = {table[name][0]:>5}")

    by_calls = rank(table, 0)
    by_tottime = rank(table, 1)
    by_cumtime = rank(table, 2)

    print("--- three orderings of the same profile ---")
    print(f"  by ncalls  : {by_calls}")
    print(f"  by tottime : {by_tottime}")
    print(f"  by cumtime : {by_cumtime}")

    print("--- and they disagree, which is the point ---")
    print(f"  most-called function        : {by_calls[0]}")
    print(f"  function holding the time   : {by_tottime[0]}")
    print(f"  they are different          : {by_calls[0] != by_tottime[0]}")
    print(f"  optimising the most-called one would change nothing measurable")

    print("--- tottime excludes callees; cumtime includes them ---")
    wrapper_tot, wrapper_cum = table["wrapper"][1], table["wrapper"][2]
    leaf_tot = table["hot_leaf"][1]
    print(f"  wrapper's own body is nearly free  : {wrapper_tot < leaf_tot / 10}")
    print(f"  but its cumtime contains the leaf  : {wrapper_cum >= leaf_tot}")
    print(f"  so cumtime says WHERE to look, tottime says WHAT to change")

    print("--- how much of the program is in one function ---")
    total_tottime = sum(value[1] for value in table.values())
    share = table["hot_leaf"][1] / total_tottime
    print(f"  hot_leaf's share of measured time is above 90% : {share > 0.90}")
    print(f"  number of functions holding the first 90%      : 1")

    print("--- the rule ---")
    print("  read cumtime to choose the subtree, tottime to choose the line, and never")
    print("  read ncalls as a proxy for either")


if __name__ == "__main__":
    main()
