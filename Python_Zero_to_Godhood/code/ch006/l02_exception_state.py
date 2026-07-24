"""Listing 6.2 - the exception hierarchy, and why `except Exception` is not
`except everything`.

Every exception derives from BaseException. The split matters: Exception is one
subtree, but KeyboardInterrupt, SystemExit, and GeneratorExit derive from
BaseException directly, so "catch all errors" (except Exception) deliberately
does NOT swallow the signals that shut a program down. sys.exc_info()
reconstructs the classic (type, value, traceback) tuple from the single
exception object CPython stores on the thread state since 3.11.
"""

import sys

print("--- the hierarchy: control-flow signals sit outside Exception ---")
for exc in (ValueError, KeyError, KeyboardInterrupt, SystemExit, GeneratorExit):
    print(f"  {exc.__name__:18} issubclass(_, Exception) = {issubclass(exc, Exception)}")

print()
print("  so 'except Exception' spares KeyboardInterrupt and SystemExit,")
print("  which is what keeps a program killable and lets shutdown work.")

print()
print("--- sys.exc_info() inside a handler, rebuilt from the active exception ---")
try:
    raise ValueError("v")
except ValueError:
    exc_type, exc_value, exc_tb = sys.exc_info()
    print("  type :", exc_type.__name__)
    print("  value:", exc_value)
    print("  type(value).__traceback__ is exc_tb:", exc_value.__traceback__ is exc_tb)

print()
print("Prefer 'except SomeError as e' and use e directly; sys.exc_info() is for")
print("generic logging or framework code that must work without naming the type.")
