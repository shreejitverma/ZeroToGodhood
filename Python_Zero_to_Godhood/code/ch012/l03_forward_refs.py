"""Listing 12.3 - forward references, and how PEP 649 changed them in 3.14.

A self-referential class annotation names a type that does not yet exist during
its own body. What happens next depends on the interpreter, and this is one of
the sharpest behavioral differences between 3.13 and 3.14.

  3.13 and earlier: class/module annotations are evaluated EAGERLY at definition
  time, so a bare forward reference raises NameError. You must quote it.

  3.14 (PEP 649): annotations are evaluated LAZILY via a compiler-generated
  __annotate__ function, so the definition succeeds and the annotation resolves
  when something reads __annotations__ (by which time the name is bound).

This listing prints which behavior the running interpreter exhibits. Its output
differs between 3.13 and 3.14 by design; both are recorded.
"""

print("--- a bare self-reference in a class annotation ---")
try:
    class Node:
        parent: Node              # Node is not bound yet during its own body

    resolved = Node.__annotations__
    print("  DEFINED without error (PEP 649 lazy annotations, 3.14+)")
    print("  Node.__annotations__ resolves to:", {k: v.__name__ for k, v in resolved.items()})
except NameError as exc:
    print("  NameError at definition (eager annotations, <= 3.13):", exc)

print()
print("--- the portable idiom that works on every version: quote it ---")


class NodeOK:
    parent: "NodeOK"              # string forward reference; stored unevaluated on <= 3.13


print("  NodeOK.__annotations__:", NodeOK.__annotations__)
print()
print("PEP 649 (Chapter 18) makes the eager-evaluation NameError go away in 3.14,")
print("which is also why `from __future__ import annotations` (PEP 563) is on a")
print("path to retirement. Until 3.14 is your floor, quote forward references or")
print("import annotations from __future__.")
