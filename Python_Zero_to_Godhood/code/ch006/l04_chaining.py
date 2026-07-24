"""Listing 6.4 - exception chaining links the domain error to its root cause.

When handling one error raises another, both matter: the new one for the
abstraction you present, the original for the diagnosis. Python links them.
Implicit: an exception raised during handling sets the new one's __context__.
Explicit: `raise New() from original` sets __cause__ and marks the link
deliberate. Suppressed: `raise New() from None` clears the chain.
"""


def chained():
    try:
        1 / 0
    except ZeroDivisionError as e:
        raise RuntimeError("wrapped") from e


print("--- raise ... from ... sets __cause__; __context__ is kept too ---")
try:
    chained()
except RuntimeError as e:
    print("  __cause__  :", type(e.__cause__).__name__)
    print("  __context__:", type(e.__context__).__name__)


def suppressed():
    try:
        1 / 0
    except ZeroDivisionError:
        raise RuntimeError("clean") from None


print()
print("--- raise ... from None clears the chain when the original is noise ---")
try:
    suppressed()
except RuntimeError as e:
    print("  __cause__  :", e.__cause__)
    print("  __suppress_context__:", e.__suppress_context__)

print()
print("This is how you wrap a low-level error in a domain error without losing")
print("the trail: wrap a KeyError from a config lookup in a ConfigError with")
print("`raise ConfigError(...) from e`, and the traceback shows both.")
