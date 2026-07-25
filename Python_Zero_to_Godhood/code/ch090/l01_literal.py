"""Listing 90.1 - Literal: a fixed set of values, checked statically, free at runtime.

Literal['r', 'w', 'a'] tells the checker a value must be one of those exact
literals, so it flags a wrong value BEFORE running, and at runtime the value is
just a plain str (the annotation is erased, Chapter 86): a Literal parameter
accepts ANY str at runtime. An Enum, by contrast, creates real runtime MEMBERS
(distinct objects with identity, .value, iteration, isinstance), which the runtime
DOES enforce, at a cost. So Literal is for a small fixed value-set where static
checking suffices (a mode flag, an HTTP method); Enum is for when you need runtime
members. This listing shows the runtime difference.
"""

from enum import Enum
from typing import Literal


def set_mode(mode: Literal["r", "w", "a"]) -> str:
    return "opened " + mode


class Mode(Enum):
    R = "r"
    W = "w"
    A = "a"


def set_mode_enum(mode: Mode) -> str:
    return "opened " + mode.value


def main() -> None:
    print("--- a Literal value is a plain str at runtime (erased) ---")
    m: Literal["r"] = "r"
    print(f"  type of a Literal['r'] : {type(m).__name__}")
    print(f"  equals the plain str   : {m == 'r'}")

    print("--- the runtime does NOT enforce the Literal set ---")
    print(f"  set_mode('w') (valid)  : {set_mode('w')!r}")
    print(f"  set_mode('x') (invalid): {set_mode('x')!r}  (runtime accepts it; the checker rejects it)")

    print("--- an Enum creates real runtime members ---")
    print(f"  Mode.W                 : {Mode.W}")
    print(f"  Mode.W.value           : {Mode.W.value!r}")
    print(f"  isinstance(Mode.W, Mode): {isinstance(Mode.W, Mode)}")
    print(f"  runtime-enforced: Mode('x') raises : {_raises(lambda: Mode('x'))}")
    print(f"  iterable members       : {[m.name for m in Mode]}")

    print("--- the rule ---")
    print(f"  Literal: a small fixed value-set, static-only, zero runtime cost")
    print(f"  Enum: real members (identity, .value, iteration, runtime-enforced), at a cost")


def _raises(fn):
    try:
        fn()
        return False
    except ValueError:
        return True


if __name__ == "__main__":
    main()
