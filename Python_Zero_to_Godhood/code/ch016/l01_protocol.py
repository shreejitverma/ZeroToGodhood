"""Listing 16.1 - Protocol gives structural subtyping: conformance by shape, not
inheritance.

Classic OO subtyping is nominal: Dog is an Animal only if it declares
class Dog(Animal). But Python's runtime has always been duck-typed. Before PEP
544 there was no way to express "anything with .render()" statically; you had to
type it Any and lose all checking. Protocol lets a class match an interface by
having the right members, no inheritance required. It is Go's implicit
interfaces brought to Python and checked statically.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Renderable(Protocol):
    def render(self) -> str: ...


class Book:                                   # no base-class relationship to Renderable
    def render(self) -> str:
        return "Book Text"


def display(item: Renderable) -> str:         # a static checker accepts any structural match
    return item.render()


print("--- Book satisfies Renderable structurally, without inheriting it ---")
print("  display(Book())          :", display(Book()))
print("  isinstance(Book(), Renderable):", isinstance(Book(), Renderable))
print("  Renderable in Book.__mro__:", Renderable in Book.__mro__, "(no inheritance)")
print()
print("A static checker verifies Book has render(self) -> str with a compatible")
print("signature. At runtime, Protocol is built by typing._ProtocolMeta, which")
print("collects the protocol's member names into __protocol_attrs__.")
print("  Renderable.__protocol_attrs__:", Renderable.__protocol_attrs__)
