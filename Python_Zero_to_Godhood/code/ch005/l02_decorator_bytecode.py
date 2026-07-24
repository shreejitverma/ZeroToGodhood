"""Listing 5.2 - what the compiler emits for a stacked decorator.

A decorator is not a runtime feature the interpreter special-cases; it is sugar
the compiler expands into loads and calls. Printed as an instruction stream so
the listing is stable across interpreters (MAKE_FUNCTION and the call opcode
have both changed across versions).
"""

import dis

SRC = "@dec1\n@dec2\ndef t():\n    return 1\n"
code = compile(SRC, "<demo>", "exec")

print("bytecode for  @dec1 / @dec2 / def t (opname [arg]):")
for ins in dis.get_instructions(code):
    if ins.opname in {"LOAD_NAME", "MAKE_FUNCTION", "CALL", "STORE_NAME",
                      "PUSH_NULL", "LOAD_CONST"}:
        arg = ""
        if ins.opname == "LOAD_NAME":
            arg = f"  {ins.argrepr}"
        elif ins.opname == "STORE_NAME":
            arg = f"  {ins.argrepr}"
        print(f"  {ins.opname}{arg}")

print()
print("the decorators load, the function is built, then the calls apply")
print("outermost-last: dec2(t) first, then dec1(dec2(t)). That is the")
print("bottom-up composition, made explicit in bytecode.")
