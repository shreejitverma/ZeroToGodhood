"""Listing 222.1 - Python 2.1 (2001): __future__, how Python ships change gradually.

Introducing a change that alters existing behaviour is a problem: do it all at
once and you break the world; never do it and the language calcifies. Python
2.1 invented a third way: `from __future__ import feature` opts a MODULE into a
behaviour that will become default in a LATER release, so the change can be
adopted per-file, on the author's schedule, before it is mandatory. It was
first used for nested scopes (2.1->2.2); it carried the division change, the
print function, unicode literals across the 2->3 boundary; and it is still
live today (`from __future__ import annotations`). This listing shows the
mechanism as it works now - a real, per-module opt-in - on current interpreters.
"""

from __future__ import annotations   # this file opts into deferred annotations

import __future__


def order(symbol: NotDefinedYet, qty: int) -> Receipt:   # forward refs, unquoted
    """These annotations reference names not yet defined - legal because
    'from __future__ import annotations' makes them STRINGS, not evaluated."""
    return qty


class NotDefinedYet:
    pass


class Receipt:
    pass


def main() -> None:
    print("--- __future__ is a real module listing every deferred feature ---")
    features = [name for name in dir(__future__)
                if isinstance(getattr(__future__, name),
                              __future__._Feature)]
    print(f"  __future__ names {len(features)} features across history")
    print(f"  a sample: {sorted(features)[:5]}")
    print("  each is a change that was OPTIONAL for a while, then became")
    print("  default - the mechanism that lets Python evolve without a")
    print("  flag day (2.1 introduced it, for nested scopes)")

    print("--- each feature records WHEN it was optional and WHEN mandatory ---")
    for name in ("nested_scopes", "division", "print_function", "annotations"):
        feat = getattr(__future__, name)
        optional = f"{feat.getOptionalRelease()[0]}.{feat.getOptionalRelease()[1]}"
        mandatory = feat.getMandatoryRelease()
        mand = f"{mandatory[0]}.{mandatory[1]}" if mandatory else "still optional"
        print(f"  {name:<16} optional in {optional:<5} mandatory in {mand}")
    print("  the two dates ARE the gradual-migration mechanism: a window")
    print("  where the feature is available but not forced, so code can move")
    print("  on its own schedule (division and print_function eased 2->3)")

    print("--- this file uses 'annotations': forward refs work UNQUOTED ---")
    hints = order.__annotations__
    print(f"  the annotations are stored as strings : "
          f"{all(isinstance(v, str) for v in hints.values())}")
    print(f"  order's return annotation : {hints['return']!r}")
    print("  because this file imported 'annotations' from __future__, the")
    print("  hints referencing NotDefinedYet and Receipt (defined LATER) are")
    print("  legal - they are strings, evaluated only if asked (Deep I owns")
    print("  the type machinery; this is the release mechanism that ships it)")

    print("--- the constraint answered ---")
    print("  2.1 faced the change-management problem every language has: how")
    print("  to alter behaviour without a flag day. __future__ is the answer -")
    print("  opt in per module, on your schedule, before it is mandatory. it")
    print("  made the 2->3 transition SURVIVABLE and is still how Python ships")
    print("  behaviour changes gently today")


if __name__ == "__main__":
    main()
