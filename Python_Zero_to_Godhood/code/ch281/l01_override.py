"""Listing 281.1 - Python 3.12 (2023): typing.override, declaring intent to override.

A subtle, expensive bug: you override a base-class method, but MISSPELL the name
(on_recieve vs on_receive) or the base later RENAMES it. Your method still runs -
as a brand-new method nobody calls - and the base's version runs instead, so the
override silently does nothing. Python 3.12's PEP 698 added @typing.override: mark
a method with it to DECLARE 'this overrides a base method'. A type checker then
verifies a base method with that name actually exists and errors if not - turning
a silent no-op into a caught mistake. At runtime it is a passthrough that sets
__override__ = True for tools to see. Deep I owns the type system that enforces
it; this is the release that let 'I am overriding' be stated and checked.
Verified on current interpreters.
"""

from typing import override


class Handler:
    def on_receive(self, msg):
        return f"base handles {msg}"

    def on_error(self, err):
        return f"base error {err}"


class GoodHandler(Handler):
    @override                                    # correctly overrides on_receive
    def on_receive(self, msg):
        return f"custom handles {msg}"


class TypoHandler(Handler):
    # NOTE: no @override here. With @override a checker would FLAG this typo.
    def on_recieve(self, msg):                   # misspelled - does NOT override
        return f"never called: {msg}"


def main() -> None:
    print("--- @override marks a method as intentionally overriding a base one ---")
    g = GoodHandler()
    print(f"  GoodHandler().on_receive('x') : {g.on_receive('x')}")
    print(f"  the override actually took effect (not the base) : "
          f"{g.on_receive('x') == 'custom handles x'}")
    print("  @override declares intent: this method is meant to replace a base")
    print("  method of the same name. a type checker verifies that base method")
    print("  exists - so a rename or typo is caught statically, not in production")

    print("--- the bug it catches: a misspelled override silently does nothing ---")
    t = TypoHandler()
    print(f"  TypoHandler().on_receive('x') : {t.on_receive('x')}   <- BASE ran")
    print(f"  the typo'd on_recieve exists but is never called : "
          f"{hasattr(t, 'on_recieve')}")
    print("  on_recieve (misspelled) did NOT override on_receive, so the BASE")
    print("  method runs and the 'override' is dead code. @override on that")
    print("  method would make a type checker report 'no base method on_recieve'")

    print("--- at runtime @override is a passthrough that sets a marker ---")
    print(f"  GoodHandler.on_receive.__override__ : "
          f"{GoodHandler.on_receive.__override__}")
    print(f"  it did not change the method's behaviour : "
          f"{GoodHandler().on_receive('y') == 'custom handles y'}")
    print("  @override returns the function unchanged, only tagging it with")
    print("  __override__ = True. the ENFORCEMENT is a static type checker's job")
    print("  (Deep I); at runtime the decorator is essentially free and inert")

    print("--- why declaring intent matters as a codebase evolves ---")
    print("  when a base class renames or removes a method, every @override that")
    print("  targeted it lights up in the type checker at once - you find every")
    print("  broken subclass immediately. without the marker, they silently stop")
    print("  overriding and misbehave at runtime, scattered and hard to trace")

    print("--- the constraint answered ---")
    print("  an override that misspells the name or misses a base rename still")
    print("  RUNS - as an uncalled new method - so the base version executes and")
    print("  the override silently vanishes. @override (3.12) states the intent;")
    print("  a checker confirms a matching base method exists, turning a silent")
    print("  no-op into a caught error. runtime cost is a single marker attribute")


if __name__ == "__main__":
    main()
