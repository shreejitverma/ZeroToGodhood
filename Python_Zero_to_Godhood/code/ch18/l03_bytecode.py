"""Listing 18.3 - what the compiler emits for `type Alias = list[int]`.

The `type` statement is not sugar for an assignment. It compiles to a nested
code object plus one intrinsic call, and that nested code object is the lazy
scope.
"""

import dis

SOURCE = "type Alias = list[int]\n"
code = compile(SOURCE, "<demo>", "exec")

print("--- module-level bytecode ---")
dis.dis(code, depth=0)

print()
print("--- the nested code object the compiler built for the value ---")
(lazy,) = [k for k in code.co_consts if hasattr(k, "co_name") and k.co_name == "Alias"]
print("co_name    =", lazy.co_name)
print("co_argcount=", lazy.co_argcount)
print("co_flags   =", hex(lazy.co_flags))

print()
print("--- disassembly of the lazy value scope ---")
dis.dis(lazy)
