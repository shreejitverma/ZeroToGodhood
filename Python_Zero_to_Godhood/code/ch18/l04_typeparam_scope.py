"""Listing 18.4 - the hidden function scope that holds the type parameters.

`class Box[T]` does not create one code object. It creates a chain: an outer
`<generic parameters of Box>` scope that constructs `T`, the class body nested
inside it, and the methods nested inside that. `T` reaches the body as a
closure variable.
"""

import dis

SOURCE = "class Box[T]:\n    def get(self) -> T: ...\n"
code = compile(SOURCE, "<demo>", "exec")

print("--- module-level bytecode: the class statement calls a function ---")
dis.dis(code, depth=0)

print()
print("--- the code-object tree, with cell and free variables ---")


def walk(obj, indent: int = 0) -> None:
    for const in obj.co_consts:
        if hasattr(const, "co_name"):
            print(
                " " * indent
                + f"- {const.co_name!r}"
                + f"  argcount={const.co_argcount}"
                + f"  cellvars={const.co_cellvars}"
                + f"  freevars={const.co_freevars}"
            )
            walk(const, indent + 4)


walk(code)

print()
print("note: '.type_params' is a compiler-generated cell. The leading dot")
print("makes it unspellable in Python source, so it cannot collide with a")
print("name you wrote.")
