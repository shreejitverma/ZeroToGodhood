"""Listing 18.5 - PEP 695 lazy scopes break the class-scope rule, deliberately.

Ordinary nested scopes skip the enclosing class body: a lambda or a
comprehension inside `class C` cannot see `C`'s class-level names. PEP 695
scopes *can*, because annotations that mention class-level names are the
normal case. The mechanism is a dedicated cell and a dedicated opcode.
"""

import dis

print("--- ordinary nested scopes: class-level names are invisible ---")


class Ordinary:
    X = int
    get = lambda self: X  # noqa: E731


try:
    Ordinary().get()
except NameError as exc:
    print("lambda in class body     -> NameError:", exc)

try:
    exec("class C2:\n    X = int\n    v = [X for _ in range(1)]\n")
except NameError as exc:
    print("comprehension in class    -> NameError:", exc)

print()
print("--- a PEP 695 lazy scope in the same position: visible ---")


class WithAlias:
    X = int
    type A = list[X]


print("type alias in class body  -> ", WithAlias.A.__value__)

print()
print("--- the mechanism: a __classdict__ cell plus LOAD_FROM_DICT_OR_GLOBALS ---")
code = compile("class D:\n    X = int\n    type A = list[X]\n", "<d>", "exec")


def find(obj, name):
    for const in obj.co_consts:
        if hasattr(const, "co_name"):
            if const.co_name == name:
                return const
            hit = find(const, name)
            if hit is not None:
                return hit
    return None


body = find(code, "D")
alias = find(body, "A")
print("class-body cellvars       =", body.co_cellvars)
print("alias lazy-scope freevars =", alias.co_freevars)
print("name lookup opcodes       =", [
    (i.opname, i.argrepr)
    for i in dis.get_instructions(alias)
    if i.opname in {"LOAD_DEREF", "LOAD_FROM_DICT_OR_GLOBALS"}
])

print()
print("LOAD_FROM_DICT_OR_GLOBALS consults the live class namespace first and")
print("falls back to globals. It exists for PEP 695 and PEP 649 scopes.")
