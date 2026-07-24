"""Listing 19.1 - the two fields every Python object begins with.

`object()` is the smallest possible Python object. It holds no data. It is
16 bytes, and this listing accounts for every one of them.
"""

import sys

x = object()

print("--- the smallest possible object ---")
print("sys.getsizeof(object())  =", sys.getsizeof(x), "bytes")
print("  8 bytes: ob_refcnt  (Py_ssize_t)")
print("  8 bytes: ob_type    (PyTypeObject *)")

print()
print("--- both fields are readable from Python ---")
print("ob_type, via type()      =", type(x))
print("ob_refcnt, via getrefcount =", sys.getrefcount(x))

print()
print("--- getrefcount always reports one more than you expect ---")
y = x
z = x
print("after 'y = x' and 'z = x', getrefcount(x) =", sys.getrefcount(x))
print("the bindings are x, y, z = 3, plus getrefcount's own argument = 4")

print()
print("--- the header is why a Python int is not a machine int ---")
print("sys.getsizeof(0)         =", sys.getsizeof(0), "bytes")
print("sys.getsizeof(1)         =", sys.getsizeof(1), "bytes")
print("a C int64_t              = 8 bytes")
print("the difference is the header plus CPython's arbitrary-precision digits")
