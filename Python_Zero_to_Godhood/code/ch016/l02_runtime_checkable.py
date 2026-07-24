"""Listing 16.2 - @runtime_checkable checks that names EXIST, not that signatures
match.

By default a Protocol is static-only: isinstance(obj, SomeProtocol) raises
TypeError. @runtime_checkable enables isinstance/issubclass by walking the
subject's MRO checking that each protocol attribute name exists. The crucial and
dangerous caveat: it checks EXISTENCE ONLY. A class with a method of the right
name but the WRONG signature passes, which gives false confidence.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Renderable(Protocol):
    def render(self) -> str: ...


class Book:
    def render(self) -> str:
        return "ok"


class BadRender:
    def render(self, a, b):        # the NAME 'render' exists; the signature is wrong
        return "wrong signature"


class NoRender:
    pass


print("--- runtime_checkable verifies attribute NAMES exist, not signatures ---")
print("  isinstance(Book(), Renderable)     :", isinstance(Book(), Renderable))
print("  isinstance(BadRender(), Renderable):", isinstance(BadRender(), Renderable),
      "<- WRONG signature, still True")
print("  isinstance(NoRender(), Renderable) :", isinstance(NoRender(), Renderable))
print()
print("The BadRender result is the trap: render(self, a, b) cannot stand in for")
print("render(self) -> str, yet isinstance says it can. @runtime_checkable is a")
print("coarse capability gate ('does it have these attribute names?'), never a")
print("substitute for the static check. Use it for dispatch, and never treat a")
print("passing isinstance as proof of correct implementation.")
