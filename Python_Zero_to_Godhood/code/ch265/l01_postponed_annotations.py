"""Listing 265.1 - Python 3.7 (2018): PEP 563, postponed evaluation of annotations.

By default an annotation is EVALUATED when the def/class runs, as a real
expression. That caused two pains: a forward reference (annotating a type not yet
defined) was a NameError unless you quoted it as a string, and every annotation
cost import-time work even though most annotations are only read by type
checkers, never at runtime. PEP 563 (opt-in via `from __future__ import
annotations`) makes ALL annotations be stored as STRINGS, evaluated lazily only
if something asks. Forward references just work, self-referential types need no
quotes, and annotations add near-zero import cost. typing.get_type_hints resolves
the strings to real objects on demand. Deep I owns the type system; this is the
release that decoupled annotations from runtime evaluation. Verified on current
interpreters.
"""

from __future__ import annotations               # the opt-in; must be at module top

import typing


class Node:
    def __init__(self, value: int, nxt: Node = None) -> None:
        # `Node` used INSIDE Node's own definition - a forward reference that
        # would be a NameError without postponed evaluation, no quotes needed.
        self.value = value
        self.nxt = nxt

    def link(self, other: Node) -> Node:
        self.nxt = other
        return other


def process(items: list[int], factor: float = 1.0) -> dict[str, int]:
    return {str(i): int(i * factor) for i in items}


def main() -> None:
    print("--- annotations are stored as STRINGS, not evaluated objects ---")
    ann = process.__annotations__
    print(f"  process.__annotations__ : {ann}")
    print(f"  the 'items' annotation is a str : {isinstance(ann['items'], str)}")
    print("  with `from __future__ import annotations`, def did NOT evaluate")
    print("  list[int] etc. - it stored the SOURCE TEXT. no runtime cost, and no")
    print("  requirement that the annotated types even be resolvable yet")

    print("--- forward / self references work WITHOUT quotes ---")
    a = Node(1)
    b = Node(2)
    a.link(b)
    print(f"  built a linked pair : a.value={a.value} -> nxt.value={a.nxt.value}")
    print(f"  Node.__init__ annotates its own type `Node` : "
          f"{Node.__init__.__annotations__['nxt']!r}")
    print("  `nxt: Node` inside Node's own body would be a NameError under")
    print("  eager evaluation (Node is not defined yet at that point). as a")
    print("  string it is fine - the classic reason you used to write 'Node'")

    print("--- get_type_hints resolves the strings to real types on demand ---")
    hints = typing.get_type_hints(process)
    print(f"  get_type_hints(process)['items'] : {hints['items']}")
    print(f"  it is the actual type object now : "
          f"{hints['items'] == list[int]}")
    print("  the strings are not useless: tools (and you) resolve them to real")
    print("  objects with typing.get_type_hints when needed. lazy by default,")
    print("  evaluated only when something actually inspects the types")

    print("--- the payoff: annotations cost nothing at import unless read ---")
    print("  under eager evaluation, every `x: SomeType` runs SomeType at")
    print("  def-time - import cost for information usually only a type checker")
    print("  reads. as strings, that work is deferred to whoever (if anyone)")
    print("  actually calls get_type_hints - near-zero runtime overhead")

    print("--- the trade-off to know ---")
    print("  code that inspects annotations at RUNTIME (some dataclass-like or")
    print("  validation libraries) must call get_type_hints to resolve strings,")
    print("  and needs the names in scope when it does. that is why the string")
    print("  behaviour stayed OPT-IN rather than becoming the unconditional default")

    print("--- the constraint answered ---")
    print("  eager annotations forced quoted forward references and charged")
    print("  import-time cost for type info most code never reads. PEP 563")
    print("  (`from __future__ import annotations`, 3.7) stores annotations as")
    print("  strings: forward refs just work, import cost drops, and")
    print("  get_type_hints resolves them on demand. types decoupled from runtime")


if __name__ == "__main__":
    main()
