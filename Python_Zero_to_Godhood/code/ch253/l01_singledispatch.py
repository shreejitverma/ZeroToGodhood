"""Listing 253.1 - Python 3.4 (2014): functools.singledispatch, type-based function overloading.

A function that must behave differently for different argument TYPES usually
grows a chain of isinstance() checks: if isinstance(x, int): ... elif
isinstance(x, list): ... - one function that knows about every type, and that
you must edit to add a new type. Python 3.4's PEP 443 singledispatch inverts it:
you write a base function, then REGISTER a separate implementation per type. The
dispatch on the first argument's type happens automatically, and a new type is
added by registering a new function - without touching the existing ones. It is
the open/closed principle for functions, and it respects inheritance (a
registration for a base class serves its subclasses). Deep C owns the type
model dispatch relies on; this is the release that made single-dispatch generic
functions a standard-library tool. Verified on current interpreters.
"""

from functools import singledispatch


@singledispatch
def describe(value):
    """Fallback for any type without a specific registration."""
    return f"a {type(value).__name__}: {value!r}"


@describe.register
def _(value: int):
    return f"the integer {value} (even={value % 2 == 0})"


@describe.register
def _(value: list):
    return f"a list of {len(value)} items"


@describe.register(str)                           # explicit-type form
def _(value):
    return f"the text {value!r} ({len(value)} chars)"


def main() -> None:
    print("--- one call site, implementation chosen by the argument's TYPE ---")
    for v in [42, [1, 2, 3], "hi", 3.14]:
        print(f"  describe({v!r}) -> {describe(v)}")
    print("  describe() dispatched on the type of its first argument: int, list,")
    print("  and str hit their registered functions; float fell through to the")
    print("  base. no isinstance ladder - the registry does the routing")

    print("--- adding a new type does NOT touch existing implementations ---")
    @describe.register
    def _(value: dict):
        return f"a dict with keys {sorted(value)}"
    print(f"  after registering dict: describe({{'b':2,'a':1}}) -> "
          f"{describe({'b': 2, 'a': 1})}")
    print("  a brand-new case was added by registering ONE function. the int,")
    print("  list, str, and base implementations were never edited - open for")
    print("  extension, closed for modification (the open/closed principle)")

    print("--- dispatch respects inheritance: base registration serves subclasses ---")
    from numbers import Number

    @describe.register(Number)
    def _(value):
        return f"some number: {value}"

    class Celsius(float):                          # a subclass of float (a Number)
        pass
    print(f"  describe(Celsius(21.0)) -> {describe(Celsius(21.0))}")
    print("  Celsius has no registration of its own, but it IS a Number, so the")
    print("  Number implementation handles it. registering a base class covers")
    print("  its whole subtree (Deep C's MRO decides the match)")

    print("--- the registry is inspectable ---")
    registered = sorted(t.__name__ for t in describe.registry
                        if t is not object)
    print(f"  types with a specific implementation : {registered}")
    print("  describe.registry maps each registered type to its function, and")
    print("  'object' is the base fallback. the dispatch table is data you can")
    print("  read, not a buried if/elif chain")

    print("--- the constraint answered ---")
    print("  type-varying behaviour meant an isinstance ladder in one function")
    print("  you had to edit for every new type. singledispatch (3.4) turns it")
    print("  into a base function plus per-type registrations: dispatch is")
    print("  automatic, inheritance-aware, and extensible without editing")
    print("  existing code - overloading by type, the standard-library way")


if __name__ == "__main__":
    main()
