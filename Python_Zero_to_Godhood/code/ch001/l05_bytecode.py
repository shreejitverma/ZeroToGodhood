"""Listing 2.5 - the real bytecode, as an instruction stream.

This prints opname + argrepr rather than raw dis.dis output, so the listing is
stable regardless of what line the function lands on, and so the 3.13-vs-3.14
difference is crisp rather than buried in line-number noise.

Run it on both interpreters: the opcodes are not the same. That is the point.
"""

import dis


def example_fn(a, b):
    local_val = 42
    return a + b + local_val


print("bytecode of example_fn (opname [arg]):")
for ins in dis.get_instructions(example_fn):
    arg = f"  {ins.argrepr}" if ins.argrepr else ""
    print(f"  {ins.opname}{arg}")
