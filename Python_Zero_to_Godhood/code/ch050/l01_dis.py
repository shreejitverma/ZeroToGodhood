"""Listing 50.1 - dis: reading the bytecode to see what Python actually does.

dis disassembles a function's __code__ into the bytecode the interpreter runs.
It is how you answer "why is this faster?" or "what does this construct compile
to?" with fact instead of guess. Here we compare a list comprehension with an
equivalent append loop: dis shows they compile to STRUCTURALLY different
bytecode (the comprehension uses the dedicated LIST_APPEND opcode; the loop
does a method lookup and call for list.append every iteration). The benchmark
then shows how much that structural difference is worth on a modern interpreter.

The raw disassembly text is version-dependent (opcodes change between releases),
so this listing prints the STABLE structural facts it extracts, which are the
same on every interpreter.
"""

import dis


def comp():
    return [x * x for x in range(1000)]


def loop():
    out = []
    for x in range(1000):
        out.append(x * x)
    return out


def opcodes(fn):
    return [i.opname for i in dis.get_instructions(fn)]


def main() -> None:
    c_ops = opcodes(comp)
    l_ops = opcodes(loop)

    print("--- comprehension: builds the list with a dedicated opcode ---")
    print(f"  uses LIST_APPEND opcode : {'LIST_APPEND' in c_ops}")
    print(f"  CALL instructions       : {c_ops.count('CALL')} (just range())")
    print(f"  does a .append lookup?  : {'LOAD_ATTR' in c_ops}")

    print("--- append loop: looks up and calls list.append each iteration ---")
    print(f"  uses LIST_APPEND opcode : {'LIST_APPEND' in l_ops}")
    print(f"  looks up .append (LOAD_ATTR): {'LOAD_ATTR' in l_ops}")
    print(f"  CALL instructions       : {l_ops.count('CALL')} (range() and .append())")

    print("--- the point: same result, different bytecode ---")
    print(f"  results equal           : {comp() == loop()}")
    print(f"  comprehension avoids the per-item method call the loop pays")


if __name__ == "__main__":
    main()
