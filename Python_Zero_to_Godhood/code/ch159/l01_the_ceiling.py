"""Listing 159.1 - the same computation at five levels, and the floor each one sets.

The evaluation loop is a fetch-decode-dispatch cycle: read the next instruction, jump to
its implementation, run a bounded amount of C, come back. Everything Deep H has measured
is a variation on one quantity - how many times that cycle runs - and this listing puts
the five ways to reduce it side by side on one task, the sum of squares below n.

    explicit loop        8 instructions per element
    sum([comprehension]) 6
    sum(genexpr)         7
    sum(map(lambda))     3
    closed form          0    (the algorithm changed; there is no per-element work)

All five return the same value. The first four differ by constant factors and the fifth
differs by an exponent, which is the chapter's argument in one table: the interpreter
sets a floor under any per-element formulation, and the only way under that floor is to
stop having per-element work.

Instruction counts are measured with sys.monitoring (PEP 669) and reported as the SLOPE
between 100 and 200 elements, so the per-version call-and-return constant cancels. The
slopes are identical on 3.13.5 and 3.14.6.
"""

import sys

MONITOR = sys.monitoring
TOOL = MONITOR.PROFILER_ID

BUDGET_N = 10_000_000


def instructions(fn, arg):
    n = 0

    def hook(code, offset):
        nonlocal n
        n += 1

    MONITOR.use_tool_id(TOOL, "instruction counter")
    try:
        MONITOR.register_callback(TOOL, MONITOR.events.INSTRUCTION, hook)
        MONITOR.set_events(TOOL, MONITOR.events.INSTRUCTION)
        fn(arg)
    finally:
        MONITOR.set_events(TOOL, 0)
        MONITOR.register_callback(TOOL, MONITOR.events.INSTRUCTION, None)
        MONITOR.free_tool_id(TOOL)
    return n


def per_element(fn):
    return (instructions(fn, 200) - instructions(fn, 100)) // 100


def explicit_loop(n):
    total = 0
    for i in range(n):
        total += i * i
    return total


def comprehension(n):
    return sum([i * i for i in range(n)])


def generator(n):
    return sum(i * i for i in range(n))


def mapped(n):
    return sum(map(lambda i: i * i, range(n)))


def closed_form(n):
    """sum of squares below n, in constant time and constant instructions."""
    return (n - 1) * n * (2 * n - 1) // 6


LEVELS = [
    ("explicit loop", explicit_loop),
    ("sum([comprehension])", comprehension),
    ("sum(genexpr)", generator),
    ("sum(map(lambda))", mapped),
    ("closed form", closed_form),
]


def main() -> None:
    reference = explicit_loop(1000)

    print("--- one task, five formulations: all agree ---")
    for label, fn in LEVELS:
        print(f"  {label:<22} {fn(1000)} == reference : {fn(1000) == reference}")

    print("--- bytecode instructions executed per element ---")
    for label, fn in LEVELS:
        print(f"  {label:<22} {per_element(fn):3d}")

    print(f"--- the budget: instructions the interpreter must dispatch for n = {BUDGET_N:,} ---")
    for label, fn in LEVELS:
        print(f"  {label:<22} {per_element(fn) * BUDGET_N:>12,}")

    print("--- the loop's own parameters, which do not depend on your code ---")
    print(f"  recursion limit (frames)        : {sys.getrecursionlimit()}")
    print(f"  thread switch interval (seconds): {sys.getswitchinterval()}")

    print("--- the rule ---")
    print("  constant factors move you between the first four rows; only changing the")
    print("  algorithm, or leaving the interpreter entirely, reaches the fifth")


if __name__ == "__main__":
    main()
