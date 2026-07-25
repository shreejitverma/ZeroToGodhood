"""Listing 91.1 - get_type_hints: resolving string annotations, at a real cost.

With deferred annotations (`from __future__ import annotations`, PEP 563, and the
PEP 649 direction), a function/class's __annotations__ are stored as STRINGS, not
evaluated type objects. That makes definition cheap and lets annotations reference
names not yet defined (forward references, like a class referring to itself). But
a framework that needs the ACTUAL types at runtime (a serializer, a validator,
dependency injection) must RESOLVE those strings with typing.get_type_hints, which
evaluates each annotation in the right namespace and resolves forward references.
That resolution is expensive (the benchmark measures ~600x a raw access), so it
should be done once and CACHED. This listing shows the raw strings and the resolved
types.
"""

from __future__ import annotations   # annotations are stored as strings

import typing


class Node:
    value: int
    next: Node | None                # forward reference to Node itself (a string here)


def handler(user_id: int, tags: list[str]) -> dict:
    return {}


def main() -> None:
    print("--- raw __annotations__ are unevaluated STRINGS ---")
    print(f"  Node.__annotations__ : {Node.__annotations__}")
    print(f"  'value' is a string  : {isinstance(Node.__annotations__['value'], str)}")

    print("--- get_type_hints RESOLVES the strings to real type objects ---")
    hints = typing.get_type_hints(Node)
    print(f"  resolved 'value'     : {hints['value'].__name__}")
    print(f"  'value' is the int type : {hints['value'] is int}")

    print("--- and it resolves FORWARD references (Node referring to itself) ---")
    next_hint = hints["next"]
    print(f"  'next' resolved (not a string) : {not isinstance(next_hint, str)}")
    print(f"  'next' mentions Node : {'Node' in str(next_hint)}")

    print("--- a function's hints, resolved ---")
    fh = typing.get_type_hints(handler)
    print(f"  handler hints keys   : {sorted(fh)}")
    print(f"  return is dict       : {fh['return'] is dict}")

    print("--- the rule ---")
    print(f"  raw __annotations__ is cheap but unresolved (strings under deferral)")
    print(f"  get_type_hints resolves them but is expensive: CACHE the result")


if __name__ == "__main__":
    main()
