"""Listing 3.2 - the compiler bakes the LEGB scope decision into the opcode.

LEGB (Local, Enclosing, Global, Built-in) is not a runtime dictionary search.
The symbol-table pass (Chapter 2) decides each name's scope statically, and the
opcode chosen IS the decision: a local is a fast-locals read, a free variable
is a cell dereference, a global is a global load. Only module-top-level and
dynamic scopes fall back to the dict-based LOAD_NAME.

Printed as an instruction stream so the output is stable across interpreters;
the load-family names differ between 3.13 and 3.14 and both are recorded.
"""

import dis


def fast_local_demo(x):
    y = x + 1
    return y


print("bytecode of fast_local_demo (loads and stores):")
for ins in dis.get_instructions(fast_local_demo):
    if "FAST" in ins.opname or "DEREF" in ins.opname or "NAME" in ins.opname \
            or "GLOBAL" in ins.opname or ins.opname.startswith("STORE"):
        arg = f"  {ins.argrepr}" if ins.argrepr else ""
        print(f"  {ins.opname}{arg}")

print()
print("both x and y resolve through the fast-locals array, no dict involved.")
print("(the exact opcode name is LOAD_FAST on 3.13 and LOAD_FAST_BORROW on 3.14;")
print(" the point is the scope class, not the spelling.)")
