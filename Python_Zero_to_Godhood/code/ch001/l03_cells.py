"""Listing 2.3 - captured locals become cells, shared by reference.

A nested function can outlive the call that created it, yet still read the
enclosing function's locals. Those locals cannot live in the outer frame's
fast-locals array, which dies when the frame is popped. CPython promotes a
captured local to a cell: a one-slot heap object shared between the enclosing
and nested functions. The compiled code object records which names are cells.
"""

SRC = """
def outer_func(x):
    z = 10
    def inner_func():
        nonlocal z
        return x + z
    return inner_func
"""

top = compile(SRC, "<string>", "exec")
(outer_code,) = [c for c in top.co_consts if getattr(c, "co_name", None) == "outer_func"]
(inner_code,) = [c for c in outer_code.co_consts if getattr(c, "co_name", None) == "inner_func"]

print("outer_func co_cellvars:", outer_code.co_cellvars)
print("inner_func co_freevars:", inner_code.co_freevars)

print()
print("the cell is shared, so a closure sees LIVE updates, not a snapshot:")


def make_counter():
    n = 0
    def bump():
        nonlocal n
        n += 1
        return n
    return bump


counter = make_counter()
print("  bump() ->", counter(), counter(), counter())
