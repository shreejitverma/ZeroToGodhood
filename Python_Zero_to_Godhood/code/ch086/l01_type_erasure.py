"""Listing 86.1 - type annotations are NOT enforced at runtime (type erasure).

Python does not check type annotations when the program runs. `def f(x: int)`
does not make Python verify that x is an int; the annotation is stored as METADATA
(in __annotations__) for static type checkers (mypy, pyright) and introspection
tools, and then ignored by the interpreter. So a wrongly-typed call runs fine, and
generic parameters like list[int] accept anything at runtime. Static checking
catches type errors BEFORE running; the runtime does not catch them at all unless
you validate explicitly. This listing shows the erasure; the benchmark shows that
annotations are free (no check) while real validation costs.
"""


def greet(name: str) -> str:
    return "hi " + str(name)


def total(items: list[int]) -> int:
    return sum(items)


def main() -> None:
    print("--- annotations are stored as metadata, not enforced ---")
    print(f"  greet.__annotations__ : {greet.__annotations__}")
    # pass an int where a str is annotated: no error, the annotation is ignored
    print(f"  greet(42)             : {greet(42)!r}  (int accepted despite name: str)")

    print("--- generic parameters are erased: list[int] accepts anything ---")
    print(f"  total([1, 2, 3])      : {total([1, 2, 3])}")
    print(f"  total([1.5, 2.5])     : {total([1.5, 2.5])}  (floats in a list[int]: fine)")

    print("--- a function can even violate its OWN return annotation ---")
    def as_int(x) -> int:
        return str(x)             # returns a str despite '-> int'
    print(f"  as_int(5) returned    : {as_int(5)!r}  (a str, despite -> int)")

    print("--- the rule ---")
    print(f"  annotations are for STATIC checkers (mypy/pyright) + introspection")
    print(f"  the runtime ignores them; for runtime guarantees, validate explicitly")
    print(f"  (isinstance, or a validation library like pydantic)")


if __name__ == "__main__":
    main()
