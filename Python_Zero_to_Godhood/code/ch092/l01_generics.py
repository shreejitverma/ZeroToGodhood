"""Listing 92.1 - generics preserve the type relationship the checker needs.

A TypeVar links a function's input and output types: def first[T](items: list[T])
-> T tells the checker the return type EQUALS the element type, so first([1,2,3])
is known to be an int and first(['a']) a str. Without it, annotating the return as
Any (or leaving list unparameterized) LOSES that link, the checker no longer knows
what comes out. Generics preserve precise types statically, at ZERO runtime cost
(they are erased, Chapter 86): first() is an ordinary function with no type check.
The one runtime cost is SUBSCRIPTING a generic (list[int]), which builds a
GenericAlias object. This listing shows the type preservation and the erasure.
(Uses PEP 695 syntax, Python 3.12+.)
"""

from typing import Any


def first[T](items: list[T]) -> T:      # generic: return type == element type
    return items[0]


def first_any(items: list) -> Any:      # loses the type link: returns Any
    return items[0]


def main() -> None:
    print("--- a generic function returns the element type (statically) ---")
    print(f"  first([1, 2, 3]) : {first([1, 2, 3])}   (checker knows: int)")
    print(f"  first(['a', 'b']): {first(['a', 'b'])}   (checker knows: str)")
    print(f"  first_any([1,2]) : {first_any([1, 2])}   (checker only knows: Any, link lost)")

    print("--- PEP 695 records the type parameters ---")
    print(f"  first.__type_params__ : {first.__type_params__}")

    print("--- generics are erased: no runtime type check ---")
    print(f"  first([1, 'mixed']) : {first([1, 'mixed'])}   (runtime does not check T)")

    print("--- subscripting a generic builds a GenericAlias (a runtime object) ---")
    alias = list[int]
    print(f"  type(list[int])       : {type(alias).__name__}")
    print(f"  list[int].__origin__  : {alias.__origin__.__name__}")
    print(f"  list[int].__args__    : {tuple(a.__name__ for a in alias.__args__)}")

    print("--- the rule ---")
    print(f"  a TypeVar preserves precise types the checker needs (vs Any, which loses them)")
    print(f"  generics are free at runtime; only subscripting (list[int]) allocates")


if __name__ == "__main__":
    main()
