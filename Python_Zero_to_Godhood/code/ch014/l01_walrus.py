"""Listing 14.1 - the walrus operator binds a name inside an expression.

Python deliberately separated statements (x = 1, yields no value) from
expressions (which do). That forced two patterns to be clumsy: a value both
tested and reused required either a pre-loop assignment plus while-True/break, or
computing the value twice. PEP 572's := is an assignment expression: it binds a
name AND evaluates to the bound value, without abolishing the statement/
expression distinction (it is a separate operator, not a redefinition of =).
"""

import dis
import io

print("--- := duplicates the value on the stack (COPY in 3.11+) ---")
ops = [i.opname for i in dis.get_instructions(compile("(x := 1)", "<s>", "exec"))]
print("  has COPY (dup for the expression value):", "COPY" in ops)
print("  has STORE_NAME (the binding)           :", "STORE_NAME" in ops)

print()
print("--- the two canonical uses ---")
stream = io.StringIO("aaa\nbbb\nccc\n")
lines = []
while (line := stream.readline()):        # read-until-sentinel, no while True / break
    lines.append(line.strip())
print("  loop-until-empty:", lines)


def parent_func(data):
    result = [y for x in data if (y := x * 2) > 2]   # compute once, test and reuse
    return result, y                                  # y survives in the surrounding scope


print("  filter-and-reuse:", parent_func([1, 2, 3]))

print()
print("--- the scoping subtlety: a walrus in a comprehension binds OUTWARD ---")
nested = [c.co_name for c in parent_func.__code__.co_consts if hasattr(c, "co_name")]
print("  nested code objects in parent_func:", nested, "(empty => PEP 709 inlined)")
print("  yet y leaked to the enclosing scope: that hoisting survived inlining.")

print()
print("--- the compiler forbids the dangerous cases ---")
try:
    compile("[i for i in range(3) if (i := 2)]", "<s>", "eval")
except SyntaxError as exc:
    print("  rebinding the loop var ->", exc.msg)
print()
print("Use := to remove a redundant evaluation or a temporary line, not to win")
print("golf. If it makes a line harder to scan, use a plain assignment.")
