"""Listing 3.3 - closures capture a live cell, which is why the loop trap exists.

A closure does not snapshot the variable it captures; it shares a cell, a heap
box holding a live reference. Every closure created in a loop shares the SAME
cell, so they all see the loop variable's final value. This is the single most
common closure bug in Python, and the fix exploits that default arguments are
evaluated once, at definition time.
"""


def outer_scope(multiplier):
    secret_value = 100

    def inner_scope(val):
        return val * multiplier + secret_value   # two free variables

    return inner_scope


fn = outer_scope(5)
print("--- closure cells are live, shared boxes, inspectable at runtime ---")
print("  closure cells:", [c.cell_contents for c in fn.__closure__])
print("  inner co_freevars:", fn.__code__.co_freevars)
print("  outer co_cellvars:", outer_scope.__code__.co_cellvars)

print()
print("--- the late-binding trap: all closures share one cell ---")
funcs = [lambda: i for i in range(3)]
print("  late-binding (all see final i):", [f() for f in funcs])

funcs_fixed = [lambda i=i: i for i in range(3)]   # capture by default-arg value
print("  default-arg capture fix:       ", [f() for f in funcs_fixed])

print()
print("i=i works because a default argument is evaluated once, at definition")
print("time, snapshotting the current value. Python only has capture-by-cell;")
print("i=i simulates the capture-by-value that C++ spells [i].")
