# requires: 3.14+
"""Listing 18.8 - in 3.14 a type alias's lazy scope became a PEP 649 evaluator.

PEP 695 (3.12) invented the lazy scope for type aliases. PEP 649 (3.14) needed
exactly the same thing for annotations, and generalised it: the compiler now
emits scopes that take a *format* argument and can be asked for a value, a
forward reference, or a source string.

Run `l03_bytecode.py` on 3.13 and on 3.14 to see the signature change: the
lazy scope gains a parameter and a `NotImplementedError` guard.
"""

import annotationlib
from annotationlib import Format, call_evaluate_function

type Alias = list[Undefined] | Missing

print("--- the format protocol ---")
print("Format members =", {f.name: f.value for f in Format})

print()
print("--- 3.14 exposes the lazy scope itself ---")
print("Alias.evaluate_value =", type(Alias.evaluate_value).__name__)

print()
print("--- the compiler-generated scope only implements VALUE natively ---")
for fmt in (Format.VALUE, Format.FORWARDREF, Format.STRING):
    try:
        result = repr(Alias.evaluate_value(fmt.value))
    except NameError as exc:
        result = f"NameError: {exc}"
    except NotImplementedError:
        result = "NotImplementedError  <- 'ask the fallback path'"
    print(f"  evaluate_value({fmt.name:11}) -> {result}")

print()
print("--- the high-level API supplies the fallback, via fake globals ---")
for fmt in (Format.FORWARDREF, Format.STRING):
    print(f"  call_evaluate_function({fmt.name:11}) ->",
          repr(call_evaluate_function(Alias.evaluate_value, fmt)))

print()
print("--- which is why repr() of an unresolvable alias still works ---")
print("  repr(Alias) =", repr(Alias))

print()
print("--- the identical machinery now backs function annotations ---")


def f(x: StillUndefined) -> AlsoMissing: ...


for fmt in (Format.VALUE, Format.FORWARDREF, Format.STRING):
    try:
        got = annotationlib.get_annotations(f, format=fmt)
    except NameError as exc:
        got = f"NameError: {exc}"
    print(f"  get_annotations({fmt.name:11}) -> {got}")
