"""Listing 2.4 - the compiled blueprint, readable from Python.

Compilation produces a PyCodeObject: an immutable description of a unit of
executable code. A function is a thin mutable wrapper around one. Every co_*
field is readable, which is what makes Python introspection total rather than
partial.
"""


def example_fn(a, b):
    local_val = 42
    return a + b + local_val


co = example_fn.__code__
print("co_varnames :", co.co_varnames)
print("co_consts   :", co.co_consts)
print("co_argcount :", co.co_argcount)
print("co_nlocals  :", co.co_nlocals)
print("co_stacksize:", co.co_stacksize)
print("co_flags    :", bin(co.co_flags))

print()
print("co_flags 0b11 = CO_OPTIMIZED | CO_NEWLOCALS: 'a real function'.")
print("a module or class body sets neither, which is why module-level code")
print("uses dict-based LOAD_NAME and is slower (see l06).")
print()
print("the code object is immutable; the function wrapper around it is not:")
print("  example_fn.__defaults__ =", example_fn.__defaults__)
example_fn.__defaults__ = (0,)
print("  after setting a default  =", example_fn.__defaults__, "(wrapper changed, code did not)")
