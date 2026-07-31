"""Listing 238.1 - Python 2.7 (2010): dict and set comprehensions, completing the family.

Python 2.0 gave list comprehensions - [f(x) for x in xs] - and they became the
signature way to build a list. But dicts and sets had no equivalent: to build a
dict you wrote dict((k, v) for ...) around a generator of pairs, and to build a
set you wrote set(f(x) for x in xs). Both worked and both read as a function
call wrapped around a genexpr. Python 3.0 added {k: v for ...} and {x for ...}
syntax, and 2.7 BACKPORTED them - part of 2.7's role as the bridge that let one
codebase target both lines. This completed the comprehension family: the same
readable shape for every builtin container. Deep B owns comprehension scoping;
this is the release that made 'build a dict/set declaratively' first-class on
the 2.x line. Verified on current interpreters.
"""


def main() -> None:
    print("--- dict comprehension: {key: value for ...} ---")
    squares = {n: n * n for n in range(1, 6)}
    print(f"  {{n: n*n for n in range(1,6)}} : {squares}")
    print("  before this you wrote dict((n, n*n) for n in ...) - a dict() call")
    print("  around a generator of pairs. the comprehension says the same thing")
    print("  with the {k: v ...} shape that mirrors a dict literal")

    print("--- the classic use: invert a dict ---")
    name_to_id = {"alice": 1, "bob": 2, "carol": 3}
    id_to_name = {v: k for k, v in name_to_id.items()}
    print(f"  invert {name_to_id}")
    print(f"    -> {id_to_name}")
    print("  swapping keys and values is one line and reads as exactly that.")
    print("  the pre-2.7 dict((v, k) for k, v in ...) buried the intent in a")
    print("  constructor call")

    print("--- dict comprehension with a filter ---")
    prices = {"apple": 3, "banana": 1, "cherry": 5, "date": 2}
    cheap = {name: p for name, p in prices.items() if p <= 2}
    print(f"  items with price <= 2 : {cheap}")
    print("  the same `if` clause list comprehensions have, so filtering while")
    print("  building a dict is one expression - no build-then-delete pass")

    print("--- set comprehension: {expr for ...} ---")
    words = ["Apple", "BANANA", "apple", "Banana", "cherry"]
    distinct_lower = {w.lower() for w in words}
    print(f"  distinct lowercased : {sorted(distinct_lower)}")
    print("  {x for ...} builds a set: unique by construction (Chapter 228),")
    print("  with the comprehension's map-and-filter shape. replaces")
    print("  set(w.lower() for w in words)")

    print("--- the family is now complete: same shape, four containers ---")
    src = range(5)
    list_result = [x * x for x in src]
    set_result = {x % 3 for x in src}
    dict_result = {x: x * x for x in src}
    print(f"  list : {list_result}")
    print(f"  set  : {sorted(set_result)}")
    print(f"  dict : {dict_result}")
    print(f"  gen  : sum -> {sum(x * x for x in src)}  (parens = lazy generator)")
    print("  one comprehension shape - map, optional filter - for list, set,")
    print("  dict, and (lazily) generator. learn it once, build any container")

    print("--- the constraint answered ---")
    print("  list comprehensions (2.0) had no dict/set sibling, so those were")
    print("  built with constructor-around-genexpr calls. 3.0 added {k: v ...}")
    print("  and {x ...}, and 2.7 backported them - bridging the two lines and")
    print("  completing the comprehension family so every builtin container has")
    print("  the same declarative build syntax")


if __name__ == "__main__":
    main()
