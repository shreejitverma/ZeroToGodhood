"""Benchmark 156.1 - what a local, global, builtin, and attribute read actually cost.

Four loops that differ in ONE instruction: the opcode that reads a name.

    local   -> LOAD_FAST family: index an array slot in the frame.
    global  -> LOAD_GLOBAL: probe the module's globals dict.
    builtin -> LOAD_GLOBAL: miss globals, then probe builtins.
    attr    -> LOAD_ATTR: the other dict-shaped lookup, for scale.

The loop body is UNROLLED to 20 reads per iteration. That is not cosmetic: with one
read per iteration the loop machinery (FOR_ITER, the store, the range iterator) costs
several times the read and swamps the effect, and the four rows come out within noise of
each other. Unrolling moves the reads from a few percent of the row to most of it, which
is what makes the comparison mean anything. An `empty` row measures the shared loop
overhead so the reader can see how much of each row is not the read.

The result is deliberately un-dramatic on a modern interpreter, and that is the point:
3.11+ specializes LOAD_GLOBAL into a version-guarded inline cache (LOAD_GLOBAL_MODULE /
LOAD_GLOBAL_BUILTIN), which turns the dict probe into a guard plus an indexed read once
the site is warm. The gap that motivated a decade of hoisting advice is now small.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

N = 1_000        # loop iterations
UNROLL = 20      # name reads per iteration

TEMPLATE = """
def {name}(n):
    local_name = GLOBAL_NAME
    obj = sys
    y = None
    for _ in range(n):
{body}
    return y
"""


def build(name, read):
    body = "\n".join(f"        y = {read}" for _ in range(UNROLL)) if read else "        pass"
    return TEMPLATE.format(name=name, body=body)


SETUP = f"""
import sys
N = {N}
GLOBAL_NAME = object()
""" + "".join([
    build("read_local", "local_name"),
    build("read_global", "GLOBAL_NAME"),
    build("read_builtin", "len"),
    build("read_attr", "obj.maxsize"),
    build("read_none", ""),
])


def main():
    results = [
        measure("empty loop (no read)", "read_none(N)", SETUP, number=2_000),
        measure("local  (array slot)", "read_local(N)", SETUP, number=2_000),
        measure("global (globals dict)", "read_global(N)", SETUP, number=2_000),
        measure("builtin (globals miss, builtins hit)", "read_builtin(N)", SETUP, number=2_000),
        measure("attribute (obj.attr)", "read_attr(N)", SETUP, number=2_000),
    ]
    report(f"156.1  {N * UNROLL:,} name reads ({N:,} iterations x {UNROLL} unrolled)",
           results, baseline="local  (array slot)")

    base = next(r for r in results if r.label.startswith("empty"))
    print()
    print("per read, with the shared loop overhead subtracted:")
    for r in results[1:]:
        print(f"  {r.label:<38} {(r.min_ns - base.min_ns) / (N * UNROLL):5.2f} ns")
    print()
    print("Reading this. The local read is the floor: a frame's locals are a flat array")
    print("and LOAD_FAST is an indexed read with no hashing and no guard. The global and")
    print("builtin reads go through LOAD_GLOBAL, which on 3.11+ specializes to a")
    print("version-guarded inline cache once the site is warm, so the steady-state gap")
    print("is a guard and an indexed read, not a hash-and-probe. The builtin is the")
    print("slower of the two because its unspecialized form pays two dict probes")
    print("(globals miss, then builtins hit) and its specialized form guards two dict")
    print("versions instead of one. Attribute access is the most expensive of the four")
    print("even specialized, because it guards the type as well. Hoisting still wins,")
    print("but on a warm site it now buys a guard rather than a dict lookup, so it is a")
    print("hot-loop technique, not a style rule.")


if __name__ == "__main__":
    main()
