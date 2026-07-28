"""Listing 157.1 - counting the bytecode a loop actually executes, per element.

The interpreter's per-instruction cost is the floor under every Python-level loop, so
the question that matters for a hot loop is not "how fast is each instruction" but "how
many instructions run per element". A builtin that loops in C - sum, min, any, join,
sorted, list(map(...)) with a C callable - runs ZERO Python instructions per element:
its entire loop is below the bytecode layer and invisible to a bytecode counter.

This listing measures that directly with sys.monitoring (PEP 669, 3.12+), registering an
INSTRUCTION callback and counting how many bytecode instructions each operation executes.
The absolute count carries a per-version constant (the call and return sequence differs
between 3.13 and 3.14), so what is reported is the SLOPE: run the same operation over
100 and over 200 elements and take the difference per element. The slope is the
per-element instruction cost, and it is exact and version-stable.
"""

import sys

MONITOR = sys.monitoring
TOOL = MONITOR.PROFILER_ID


def instructions(fn, arg):
    """Bytecode instructions executed by fn(arg), counted with sys.monitoring."""
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
    """Instructions executed per element: the slope, with the constant differenced out."""
    small = instructions(fn, list(range(100)))
    large = instructions(fn, list(range(200)))
    return (large - small) // 100


# --- the same reduction, four ways ------------------------------------------------

def loop_sum(xs):
    total = 0
    for x in xs:
        total += x
    return total


def builtin_sum(xs):
    return sum(xs)


def loop_min(xs):
    best = xs[0]
    for x in xs:
        if x < best:
            best = x
    return best


def builtin_min(xs):
    return min(xs)


# --- the same map, three ways -----------------------------------------------------

def double(x):
    return x * 2


def loop_double(xs):
    out = []
    for x in xs:
        out.append(double(x))
    return out


def map_python_callable(xs):
    return list(map(double, xs))           # the callable is Python: its body still runs


def map_c_callable(xs):
    return list(map(str, xs))              # the callable is C: nothing runs in bytecode


# --- the same search, two ways ----------------------------------------------------

def loop_any(xs):
    for x in xs:
        if x > 1_000_000:
            return True
    return False


def builtin_any_genexpr(xs):
    return any(x > 1_000_000 for x in xs)  # any loops in C, the genexpr resumes in Python


# --- the same build, two ways -----------------------------------------------------

def loop_concat(xs):
    s = ""
    for x in xs:
        s += "x"
    return s


def builtin_join(xs):
    return "".join("x" for _ in xs)


# Cases whose loop body contains no comparison. Their slopes are identical on 3.13.6
# and 3.14.6, so the chapter can quote one table for both.
STABLE = [
    ("reduce   for-loop sum", loop_sum),
    ("reduce   sum(xs)", builtin_sum),
    ("map      for-loop + append", loop_double),
    ("map      list(map(python_fn, xs))", map_python_callable),
    ("map      list(map(str, xs))", map_c_callable),
    ("build    s += 'x' in a loop", loop_concat),
    ("build    ''.join(genexpr)", builtin_join),
    ("reduce   min(xs)", builtin_min),
]

# Cases whose loop body contains a comparison. These differ between 3.13.6 and 3.14.6,
# which is data, not noise: the chapter quotes both. Kept contiguous and last so the
# version-specific quote is one block.
COMPARING = [
    ("compare  for-loop min", loop_min),
    ("compare  for-loop with a test", loop_any),
    ("compare  any(genexpr)", builtin_any_genexpr),
]


def main() -> None:
    print("--- bytecode instructions executed PER ELEMENT (the slope) ---")
    for label, fn in STABLE:
        print(f"  {label:<36} {per_element(fn):3d}")

    print("--- the same measure, for bodies containing a comparison ---")
    for label, fn in COMPARING:
        print(f"  {label:<36} {per_element(fn):3d}")

    print("--- what the zeros mean ---")
    print("  a builtin that loops in C executes NO bytecode per element: its loop is")
    print("  below the interpreter, so the per-instruction cost never applies to it")

    print("--- what the non-zeros mean ---")
    print("  a Python-level loop pays the interpreter once per instruction per element;")
    print("  a genexpr fed to a C builtin still resumes a Python frame per element")

    print("--- the rule ---")
    print("  the cheapest bytecode instruction is the one that never executes; push the")
    print("  loop into C when a builtin expresses it, and shrink the body when it cannot")


if __name__ == "__main__":
    main()
