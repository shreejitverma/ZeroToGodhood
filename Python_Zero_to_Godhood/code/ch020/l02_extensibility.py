"""Listing 20.2 - the decision that separated Python from ABC.

Guido's stated diagnosis of ABC was that it could not be extended: its parser
knew the built-in types, and there was no standard library into which a third
party could add anything. Python's built-in types are ordinary objects living in
ordinary namespaces, reachable and replaceable at runtime.

This listing demonstrates that property as it exists today. It is evidence about
modern CPython, not about ABC, which is not runnable here.
"""

import builtins
import types

print("--- built-in types are ordinary objects in an ordinary module ---")
print("  builtins is a module:", isinstance(builtins, types.ModuleType))
print("  'list' is an attribute of it:", builtins.list is list)
print("  and it is a plain dict:", type(vars(builtins)).__name__)

print()
print("--- so a built-in type can be subclassed like any other ---")


class Ledger(dict):
    """A dict that records every key ever written."""

    def __init__(self):
        super().__init__()
        self.seen = []

    def __setitem__(self, key, value):
        self.seen.append(key)
        super().__setitem__(key, value)


led = Ledger()
led["a"] = 1
led["b"] = 2
print("  Ledger(dict) instance:", dict(led), "seen:", led.seen)
print("  still a dict:", isinstance(led, dict))

print()
print("--- and a type can be built at runtime, with no compiler involvement ---")
Made = type("Made", (object,), {"kind": "runtime", "speak": lambda self: "hello"})
print("  type() built:", Made.__name__, "| kind:", Made.kind, "| speak():", Made().speak())

print()
print("--- the same door the C-API uses ---")
print("  a type written in C is indistinguishable from one written in Python:")
for t in (list, Ledger, Made):
    origin = "C" if t.__module__ == "builtins" else "Python"
    print(f"    {t.__name__:8} __module__={t.__module__:10} written in {origin}")
print("  both are PyTypeObjects; the caller cannot tell. That is the")
print("  extensibility ABC lacked, and it is why the stdlib could grow.")
