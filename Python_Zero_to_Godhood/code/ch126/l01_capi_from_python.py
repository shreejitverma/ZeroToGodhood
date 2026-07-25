"""Listing 126.1 - the C-API from the outside: ctypes.pythonapi and callbacks.

A C extension does not use ctypes; it calls CPython's C-API directly, functions like
Py_INCREF, PyList_Size, PyObject_Length that operate on PyObject pointers. ctypes lets
you call those SAME functions from Python via ctypes.pythonapi, which is a superb way
to SEE the C-API without writing C:
  - Py_IncRef/Py_DecRef ARE the reference-counting primitives of Chapter 31, exposed.
  - ctypes.py_object marshals a real Python object as the PyObject* the C-API expects.
  - PyList_Size, PyObject_Length are the C implementations behind len().
And the reverse direction, a Python function wrapped as a C callback (CFUNCTYPE), lets
C call back into Python. This listing shows both directions across the boundary.
"""

import ctypes
import sys


def main() -> None:
    api = ctypes.pythonapi

    print("--- Py_IncRef / Py_DecRef ARE the C-level refcount primitives (Chapter 31) ---")
    obj = [1, 2, 3]
    base = sys.getrefcount(obj)
    api.Py_IncRef(ctypes.py_object(obj))         # the C-API Py_INCREF, from Python
    print(f"  refcount delta after Py_IncRef : +{sys.getrefcount(obj) - base}")
    api.Py_DecRef(ctypes.py_object(obj))         # balance it (Chapter 31's contract)
    print(f"  refcount delta after Py_DecRef : {sys.getrefcount(obj) - base}   (restored)")

    print("--- call the C-API functions behind len() directly ---")
    api.PyList_Size.restype = ctypes.c_ssize_t
    api.PyList_Size.argtypes = [ctypes.py_object]
    print(f"  PyList_Size([1, 2, 3])       : {api.PyList_Size(obj)}")

    api.PyObject_Length.restype = ctypes.c_ssize_t
    api.PyObject_Length.argtypes = [ctypes.py_object]
    print(f"  PyObject_Length('hello')     : {api.PyObject_Length('hello')}")
    print(f"  (PyObject_Length is the C implementation that len() calls)")

    print("--- the other direction: a Python function as a C callback ---")
    CallbackType = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int)

    @CallbackType
    def square(n):
        return n * n

    print(f"  square is a C function pointer : {isinstance(square, ctypes._CFuncPtr)}")
    print(f"  calling it through C : square(7) = {square(7)}")

    print("--- the rule ---")
    print(f"  ctypes.pythonapi calls CPython's C-API from Python (Py_IncRef, len's")
    print(f"  C impl); CFUNCTYPE wraps a Python function so C can call back into it")


if __name__ == "__main__":
    main()
