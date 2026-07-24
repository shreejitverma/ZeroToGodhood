# requires: 3.14+
"""Listing 24.1 - PEP 649 makes annotations lazy, ending three eras of
forward-reference workarounds.

Through 3.13, annotations were evaluated eagerly when the def or class body ran,
so a forward reference to a not-yet-defined name raised NameError, and you had to
quote it or use `from __future__ import annotations`. PEP 649 (3.14) replaces
eager evaluation with a compiler-generated __annotate__ function that runs on
demand, so the definition succeeds and the annotation resolves when something
reads it.
"""


def f(x: Undefined) -> AlsoMissing:      # names that do not exist anywhere
    ...


print("--- a def with undefined annotations now survives definition ---")
print("  defined without error:", f.__name__)
print("  has a lazy __annotate__ function:", hasattr(f, "__annotate__"))


class Node:
    next: Node                            # self-reference; raised NameError on <= 3.13


print()
print("--- a self-referential class annotation also just works ---")
print("  Node.__annotations__:", {k: v.__name__ for k, v in Node.__annotations__.items()})
print()
print("On 3.13 the two definitions above raised NameError at definition time")
print("(Chapter 12 records that behavior). PEP 649 defers the evaluation, so the")
print("names are resolved later, by which time Node exists. This is why")
print("`from __future__ import annotations` is on a path to retirement.")
