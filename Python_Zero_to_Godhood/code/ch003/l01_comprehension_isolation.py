"""Listing 3.1 - a comprehension's loop variable does not leak, and since 3.12
does not even get its own frame.

Three eras: Python 2.x compiled a comprehension as an inline loop that wrote
the loop variable into the enclosing locals (it leaked). Python 3.0 gave each
comprehension its own hidden function frame (isolated, but a frame per
comprehension). PEP 709 (3.12) inlined them again while keeping isolation, by
saving and restoring the loop variable instead of creating a scope.

The proof that the frame is gone: an inlined comprehension leaves no nested
code object behind. A generator expression, which must suspend and genuinely
needs its own frame, still does.
"""

x = 999
data = [x for x in range(5)]
print("--- isolation: the outer x is untouched (since 3.0) ---")
print("  x after comprehension:", x)
print("  data:", data)


def make_list(n):
    return [i * i for i in range(n)]


def make_gen(n):
    return (i * i for i in range(n))


print()
print("--- PEP 709: the list comprehension has no nested code object ---")
list_nested = [c.co_name for c in make_list.__code__.co_consts if hasattr(c, "co_name")]
gen_nested = [c.co_name for c in make_gen.__code__.co_consts if hasattr(c, "co_name")]
print("  nested code objects in make_list:", list_nested)
print("  nested code objects in make_gen: ", gen_nested)
print("  the generator still gets its own frame because it suspends.")
