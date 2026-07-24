"""Listing 4.1 - a method is not stored on the instance; it is manufactured on
every access.

The surprise that opens the chapter: `c.m is c.m` is False. A method is a
non-data descriptor (a plain function) whose __get__ builds a fresh bound-method
object each time it is read, pairing the function with the instance. There is no
magic behind `self`; there is a small wrapper.
"""


class C:
    def m(self):
        return 1


c = C()

print("--- reading the same method twice yields two different objects ---")
print("  c.m is c.m       :", c.m is c.m)
print("  type(c.m)        :", type(c.m).__name__)
print("  c.m == c.m       :", c.m == c.m, "(equal by value: same func, same self)")

print()
print("--- the bound method is a thin wrapper: function + instance ---")
bound = c.m
print("  bound.__self__ is c   :", bound.__self__ is c)
print("  bound.__func__ is C.m :", bound.__func__ is C.m)

print()
print("--- accessed on the CLASS, __get__ returns the raw function ---")
print("  type(C.m)             :", type(C.m).__name__)
print("  C.m.__get__(c, C) == c.m:", C.m.__get__(c, C) == c.m)
print()
print("So `c.m()` is `C.m.__func__(c)`: the descriptor prepends __self__ as the")
print("first argument. That is the entire mechanism of `self`.")
