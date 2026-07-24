"""Listing 2.2 - the compiler classifies every name before any code runs.

The symbol-table pass decides, statically, whether each name is a local, a
parameter, a global, or a free variable captured from an enclosing scope. That
decision is what lets CPython use array-indexed local access instead of a dict
lookup for every variable. The `symtable` module exposes exactly this pass.
"""

import symtable

SRC = """
def outer_func(x):
    z = 10
    def inner_func():
        nonlocal z
        return x + z
    return inner_func
"""

table = symtable.symtable(SRC, filename="<string>", compile_type="exec")
outer = table.lookup("outer_func").get_namespace()

print("outer identifiers:", sorted(outer.get_identifiers()))
print("'z' is_local in outer:", outer.lookup("z").is_local())
print("'x' is_parameter in outer:", outer.lookup("x").is_parameter())

inner = outer.lookup("inner_func").get_namespace()
print("inner free vars (closure):", tuple(sorted(inner.get_frees())))
print("'z' is_free in inner:", inner.lookup("z").is_free())
