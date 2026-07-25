"""Listing 94.1 - @overload: multiple static signatures, one runtime implementation.

Some functions return a type that DEPENDS on the argument type: parse(int) -> str
but parse(str) -> int. A single signature cannot express that, `parse(x: int | str)
-> int | str` loses the correspondence (the checker would not know which comes
out). @overload declares several signatures, one per case, so the checker picks
the right return type per call. At RUNTIME there is exactly ONE implementation (the
final, undecorated def); the @overload stubs are declarations only, erased from the
call path, so an overloaded function costs the same as a plain one. This listing
shows the per-argument return types and the single runtime implementation.
"""

from typing import get_overloads, overload


@overload
def parse(x: int) -> str: ...
@overload
def parse(x: str) -> int: ...
def parse(x):                       # the ONE real implementation
    if isinstance(x, int):
        return str(x)
    return int(x)


def main() -> None:
    print("--- the return type depends on the argument type (per the checker) ---")
    print(f"  parse(42)  : {parse(42)!r}  (type {type(parse(42)).__name__}; checker: str)")
    print(f"  parse('7') : {parse('7')!r}   (type {type(parse('7')).__name__}; checker: int)")

    print("--- at runtime there is ONE implementation; the stubs are declarations ---")
    print(f"  registered overloads : {len(list(get_overloads(parse)))}")
    print(f"  parse is the impl (callable) : {callable(parse)}")

    print("--- a single union signature could not express the correspondence ---")
    print(f"  parse(x: int|str) -> int|str would lose which output goes with which input")

    print("--- the rule ---")
    print(f"  @overload: multiple static signatures when the return depends on the input")
    print(f"  one runtime implementation (the stubs vanish); zero runtime cost")


if __name__ == "__main__":
    main()
