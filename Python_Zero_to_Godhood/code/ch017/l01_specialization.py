"""Listing 17.1 - watch the interpreter specialize its own bytecode.

PEP 659 (3.11) observes what actually flows through each instruction and, once a
call site is stable, patches the bytecode in memory with a specialized opcode
that assumes that shape and falls back safely if it breaks. Warm a function by
running it, then disassemble with adaptive=True to see the specialized opcodes.
"""

import dis


class P:
    def __init__(self, x):
        self.x = x


def hot(p):
    return p.x + p.x


for _ in range(1000):       # make the call site hot and monomorphic
    hot(P(5))

print("--- after warm-up, generic opcodes are patched to specialized ones ---")
specialized = [i.opname for i in dis.get_instructions(hot, adaptive=True)
               if i.opname.startswith(("LOAD_ATTR", "BINARY_OP"))]
print("  specialized opcodes:", specialized)
print()
print("  LOAD_ATTR_INSTANCE_VALUE reads the attribute by offset, no dict lookup")
print("  and no MRO walk. BINARY_OP_ADD_INT runs the int-only add that skips the")
print("  general nb_add dispatch. Each is GUARDED: it checks a cached type version")
print("  and deoptimizes to the generic path if a different type appears, so")
print("  correctness is never at risk, only speed.")


def addints(a, b):
    return a + b


for _ in range(1000):
    addints(1, 2)

print()
print("--- the binary-op specialization in isolation ---")
binop = [i.opname for i in dis.get_instructions(addints, adaptive=True)
         if i.opname.startswith("BINARY_OP")]
print("  addints(int, int) specialized to:", binop)
