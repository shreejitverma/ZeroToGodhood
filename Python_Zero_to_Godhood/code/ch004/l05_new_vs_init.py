"""Listing 4.5 - construction is two slots: __new__ allocates, __init__
initializes.

tp_new allocates and returns the instance (setting up the PyObject header from
Chapter 19); it runs first and is a static method. tp_init initializes the
already-allocated object and must return None; it runs only if __new__ returned
an instance of cls. The split is what makes immutable types possible.
"""


class Lifecycle:
    def __new__(cls, *args, **kwargs):
        print("  __new__ (allocate)")
        return super().__new__(cls)

    def __init__(self, v):
        print("  __init__ (initialize) with", v)
        self.v = v


print("--- order of construction ---")
obj = Lifecycle(7)
print("  obj.v:", obj.v)

print()
print("--- returning a different type from __new__ silently skips __init__ ---")


class Sneaky:
    def __new__(cls):
        return 42                    # not an instance of Sneaky

    def __init__(self):
        print("  __init__ ran")      # will NOT run


result = Sneaky()
print("  Sneaky() returned:", result, "(an int; __init__ was skipped)")

print()
print("This is why immutable types (int, str, tuple, frozen dataclasses) do")
print("their work in __new__: by the time __init__ could run there is nothing")
print("left to mutate.")
