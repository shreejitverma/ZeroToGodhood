"""Listing 93.1 - Union types: X | Y, Optional, and the isinstance cost trap.

X | Y (PEP 604, Python 3.10+) is the modern union syntax, equivalent to the older
Union[X, Y]. Optional[X] is just X | None (a value that may be the type OR None),
NOT "an optional argument". Unlike most typing constructs, X | Y is also a real
RUNTIME object usable in isinstance (3.10+): isinstance(x, int | str) works. But
building `int | str` inline on every isinstance call allocates a union object each
time, so a hot loop should PRECOMPUTE the union (or use an (int, str) tuple). This
listing shows the equivalences and the runtime isinstance; the benchmark shows the
inline-union cost.
"""

from typing import Optional, Union


def main() -> None:
    print("--- X | Y is equivalent to Union[X, Y] ---")
    print(f"  (int | str) == Union[int, str] : {(int | str) == Union[int, str]}")
    print(f"  Optional[int] == (int | None)  : {Optional[int] == (int | None)}")
    print(f"  Optional means 'or None', not 'optional argument'")

    print("--- X | Y is a real runtime object: usable in isinstance (3.10+) ---")
    print(f"  isinstance(5, int | str)   : {isinstance(5, int | str)}")
    print(f"  isinstance('a', int | str) : {isinstance('a', int | str)}")
    print(f"  isinstance(1.5, int | str) : {isinstance(1.5, int | str)}")

    print("--- a union narrows in the checker; at runtime you branch/isinstance ---")
    def describe(x: int | str) -> str:
        if isinstance(x, int):
            return f"int:{x}"          # here the checker narrows x to int
        return f"str:{x}"             # here to str
    print(f"  describe(42)  : {describe(42)!r}")
    print(f"  describe('hi'): {describe('hi')!r}")

    print("--- the rule ---")
    print(f"  X | Y is the modern union; Optional[X] is X | None")
    print(f"  usable in isinstance, but precompute the union for a hot loop")
    print(f"  (building `int | str` inline allocates a union object per call)")


if __name__ == "__main__":
    main()
