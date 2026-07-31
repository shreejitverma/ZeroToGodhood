"""Listing 218.1 - Python 1.0 (1994): lambda, map, filter, reduce - and their heir.

Python 1.0 added functional-programming tools - lambda (anonymous functions),
map, filter, reduce - contributed by a user who wanted Lisp-style constructs.
They fit the founding decision (functions are objects, Chapter 4) perfectly:
if a function is a value, you can make one anonymously and pass it. But the
'one obvious way' value (Chapter 3) later favoured COMPREHENSIONS for most of
what map/filter did, and reduce was moved OUT of builtins into functools in
Python 3. This listing shows the tools, then their modern heir, and the
readability judgement that reshaped them - verified on current interpreters.
"""

import functools


def main() -> None:
    print("--- lambda: an anonymous function, because functions are values ---")
    square = lambda x: x * x                     # noqa: E731 (illustrative)
    print(f"  a lambda is a function object : {type(square).__name__}")
    print(f"  square(5) = {square(5)}")
    print(f"  sorted by a lambda key        : "
          f"{sorted([('b', 2), ('a', 3)], key=lambda p: p[1])}")
    print("  lambda exists because Chapter 4's decision (functions are")
    print("  objects) makes an anonymous one just a value with no name -")
    print("  useful exactly where a short function is passed, like a key")

    print("--- map and filter: 1.0's tools, and the comprehension heir ---")
    nums = [1, 2, 3, 4, 5]
    mapped = list(map(lambda x: x * x, nums))
    comp = [x * x for x in nums]
    print(f"  map(lambda x: x*x, nums) : {mapped}")
    print(f"  [x*x for x in nums]      : {comp}   (same result)")
    filtered = list(filter(lambda x: x % 2, nums))
    fcomp = [x for x in nums if x % 2]
    print(f"  filter(odd, nums)        : {filtered}")
    print(f"  [x for x in nums if x%2] : {fcomp}   (same result)")
    print("  map/filter came first (1.0); comprehensions came later (2.0)")
    print("  and read better for most cases - the 'one obvious way' value")
    print("  (Chapter 3) favoured the comprehension, which now dominates")

    print("--- reduce: demoted from builtin to functools in Python 3 ---")
    total = functools.reduce(lambda a, b: a + b, nums)
    print(f"  functools.reduce(add, nums) : {total}")
    print(f"  but sum(nums) is clearer     : {sum(nums)}")
    print("  reduce was a builtin in Python 2; Python 3 MOVED it to functools")
    print("  because a named reduction (sum, max, any, all) reads better than")
    print("  reduce(lambda...) for the common cases - readability as a")
    print("  language-shaping force, demoting a tool without removing it")

    print("--- where the functional tools still win ---")
    print(f"  map over MULTIPLE iterables : "
          f"{list(map(lambda a, b: a + b, [1, 2], [10, 20]))}")
    print(f"  map with an existing func   : "
          f"{list(map(str.upper, ['a', 'b']))}")
    print("  map shines with an EXISTING function (no lambda) or several")
    print("  iterables; a comprehension shines when there is a condition or")
    print("  a transform worth naming inline. the tools coexist because each")
    print("  is the obvious way for a DIFFERENT case (Chapter 3's tension)")

    print("--- the constraint, and the value ---")
    print("  1.0 added functional tools because functions are objects made")
    print("  them natural. later releases did not REMOVE them but reshaped")
    print("  their role - comprehensions for readability, functools for the")
    print("  rest - which is how the 'one obvious way' value works in")
    print("  practice: not deletion, but the slow crowning of a clearer form")


if __name__ == "__main__":
    main()
