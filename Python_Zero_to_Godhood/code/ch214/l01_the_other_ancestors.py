"""Listing 214.1 - the ancestors beyond ABC: Modula's modules, C's substrate.

Chapter 1 read the ABC ledger. But ABC was not Python's only parent. Two other
languages left marks visible in every program written today: Modula (-2 and
-3) gave the MODULE as a first-class namespace with explicit import, and the
EXCEPTION as structured control flow; C gave the implementation substrate and
the value model (a Python int is unbounded precisely because Guido REFUSED C's
machine-word int). This listing demonstrates the modern consequence of each
inheritance on the verification interpreters - it does not regenerate 1991
output, it shows what those 1989 decisions became.
"""

import sys
import types


def main() -> None:
    print("--- Modula's inheritance I: a module is a namespace object ---")
    print(f"  a module is an object of type : {type(sys).__name__}")
    print(f"  its namespace IS a dict       : {type(sys.__dict__).__name__}")
    made = types.ModuleType("made_at_runtime")
    made.answer = 42
    print(f"  and one can be built at runtime: {made.answer}")
    print("  Modula gave Python the module as an explicit, named namespace")
    print("  you import from - not C's textual #include, but a real object")
    print("  with its own dict (Deep G owns the machinery this seeded)")

    print("--- Modula-3's inheritance: exceptions as structured control ---")
    trace = []

    def risky(fail):
        try:
            trace.append("try")
            if fail:
                raise ValueError("boundary")
            trace.append("ok")
        except ValueError as exc:
            trace.append(f"caught:{exc}")
        finally:
            trace.append("finally")

    risky(fail=False)
    risky(fail=True)
    print(f"  no-fail path : {trace[:3]}")
    print(f"  fail path    : {trace[3:]}")
    print("  try/except/finally is Modula-3's structured exception model:")
    print("  errors are not returned codes to check (C) but raised objects")
    print("  that unwind the stack to a matching handler (Chapter 6, Deep A)")

    print("--- C's inheritance, and the decision to reject its int ---")
    big = 2 ** 200
    print(f"  2**200 is an exact Python int  : {big}")
    print(f"  it did not overflow a 64-bit word (C would): {big > 2**64}")
    print(f"  its type is plain int          : {type(big).__name__}")
    print("  Python is implemented IN C, but a Python int is NOT a C int:")
    print("  ABC had arbitrary-precision numbers and Python kept them, so")
    print("  the value model comes from ABC while the runtime comes from C -")
    print("  the split that defines CPython (Deep A owns the object; the")
    print("  implementation substrate is the whole C-API story, Deep M)")

    print("--- the three ancestors, as one sentence each ---")
    print("  ABC     : the ergonomics (indentation, few powerful types)")
    print("  Modula  : the module and the exception (structure at the seams)")
    print("  C       : the substrate and the counter-example (unbounded int")
    print("            over the machine word, an object over a struct)")
    print("  Python is not any one of them; it is a set of deliberate choices")
    print("  ABOUT them, which is why the timeline that follows is a series")
    print("  of constraints answered, never a changelog")


if __name__ == "__main__":
    main()
