"""Listing 6.3 - a try/except compiles to a static exception table, not to
block-stack setup opcodes.

Through Python 3.10, entering a try executed a SETUP_FINALLY / SETUP_EXCEPT
opcode that pushed a block onto a per-frame runtime stack, so every try cost
work on entry and exit even when nothing was raised. Python 3.11 removed the
block stack and replaced it with a per-code-object exception table: a side
table mapping bytecode ranges to their handler. On the success path a try now
executes nothing extra; the table is consulted only when an exception is
actually raised.

Shown as opcode presence rather than a raw disassembly, so the listing is
stable across interpreters while still proving the structural facts.
"""

import dis


def guarded(x):
    try:
        return 10 / x
    except ZeroDivisionError:
        return -1


ops = [i.opname for i in dis.get_instructions(guarded)]

print("--- structural facts about the compiled try/except ---")
print("  has any SETUP_* block-stack opcode:", any(o.startswith("SETUP") for o in ops))
print("  has an exception table            :", bool(guarded.__code__.co_exceptiontable))

print()
print("  handler opcodes present in order:")
for op in ("PUSH_EXC_INFO", "CHECK_EXC_MATCH", "POP_EXCEPT", "RERAISE"):
    print(f"    {op:16} present: {op in ops}")

print()
print("The try body carries no setup overhead. If the division raises, the")
print("interpreter looks up the current offset in the exception table, finds the")
print("handler, pushes the exception info (PUSH_EXC_INFO), tests it")
print("(CHECK_EXC_MATCH), runs the handler, and clears the state (POP_EXCEPT).")
print("If nothing matches, RERAISE propagates to the caller, whose frame is")
print("searched the same way, building the traceback frame by frame.")

print()
print("--- the two paths produce the two results ---")
print("  guarded(2) :", guarded(2), " (success path: table never consulted)")
print("  guarded(0) :", guarded(0), " (exception path: table lookup finds the handler)")
