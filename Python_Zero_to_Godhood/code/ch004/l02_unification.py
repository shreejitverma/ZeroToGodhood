"""Listing 4.2 - types and classes are one thing, and the slots bridge C and
Python in both directions.

Python 2.2 collapsed two parallel universes (classic classes and built-in
types) into one: every class is a PyTypeObject, an instance of `type`,
descending from object. The C-level payoff is the slot system, and it is
observable: a Python __init__ becomes a plain function in the type; a built-in's
C slot is exposed to Python as a wrapper_descriptor.
"""


class NewStyle:            # implicitly subclasses object in Python 3
    pass


n = NewStyle()
print("--- one universe: type(instance) IS the class ---")
print("  type(n)                     :", type(n).__name__)
print("  issubclass(NewStyle, object):", issubclass(NewStyle, object))
print("  type(NewStyle) is type      :", type(NewStyle) is type)

print()
print("--- the slot bridge, both directions ---")


class D:
    def __init__(self):
        pass


print("  a Python __init__ is a function in the type:")
print("    type(D.__init__)          :", type(D.__init__).__name__)
print("  a built-in C slot is a wrapper_descriptor exposed to Python:")
print("    type(object.__init__)     :", type(object.__init__).__name__)
print("    repr(object.__init__)     :", repr(object.__init__))
print("    type(int.__add__)         :", type(int.__add__).__name__, "(the nb_add slot)")
print()
print("The interpreter installs slot_tp_init into tp_init to call a Python")
print("__init__, and exposes a C tp_init as a wrapper_descriptor named __init__.")
print("Python methods and C slots are the same protocol seen from two sides.")
