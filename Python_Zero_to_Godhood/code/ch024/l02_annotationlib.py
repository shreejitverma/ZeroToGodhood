# requires: 3.14+
"""Listing 24.2 - annotationlib and the three formats for reading annotations.

PEP 649 generalized the lazy scope into a protocol with formats. annotationlib
(3.14) exposes it: get_annotations can ask for VALUE (evaluate to real objects),
FORWARDREF (return a ForwardRef for anything unresolvable), or STRING (the source
text). This is what lets a tool inspect annotations that mention names it cannot
resolve, which eager evaluation could never do.
"""

import annotationlib
from annotationlib import Format, get_annotations


def f(x: Undefined) -> AlsoMissing:      # deliberately unresolvable
    ...


print("--- the three formats, on annotations that cannot be resolved ---")

try:
    v = get_annotations(f, format=Format.VALUE)
except NameError as exc:
    v = f"NameError: {exc}"
print("  VALUE     :", v)

print("  FORWARDREF:", get_annotations(f, format=Format.FORWARDREF))
print("  STRING    :", get_annotations(f, format=Format.STRING))

print()
print("--- for resolvable annotations, VALUE returns the real objects ---")


def g(n: int) -> str:
    ...


print("  get_annotations(g, VALUE):", get_annotations(g))

print()
print("VALUE evaluates and raises if a name is missing, exactly as reading")
print("__annotations__ would. FORWARDREF never raises: it returns a ForwardRef")
print("for each unresolvable name, so a checker or documentation tool can work")
print("with partial information. STRING returns the source text. get_type_hints")
print("uses this machinery, which is why 3.14 tools handle forward references")
print("that 3.13 tools choked on.")
