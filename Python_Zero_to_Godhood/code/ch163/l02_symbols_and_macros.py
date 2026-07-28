"""Listing 163.2 - why the fast C-API accessors can never be part of a stable ABI.

A stable ABI can only contain things that exist in the shared library: exported SYMBOLS,
called through the dynamic linker at a fixed calling convention. It cannot contain a
MACRO, because a macro is expanded at compile time into the caller's code, and what it
expands to - "read the field at offset 16" - is exactly the struct layout the stable ABI
exists to hide.

CPython's C-API has both, and the naming tells you which is which:

  PyList_GetItem   mixed case   a real function, an exported symbol
  PyList_GET_ITEM  ALL CAPS     a macro that indexes ob_item directly, no symbol

This listing checks each name against the interpreter's own exported symbol table, via
ctypes.pythonapi, which fails with AttributeError for a name the dynamic linker cannot
resolve. The ALL-CAPS accessors are absent on both verification interpreters, and that
absence is the whole argument: the fast path is fast BECAUSE it knows the layout, and it
is unstable for the same reason.
"""

import ctypes

SAMPLE = [
    # (name, what it is)
    ("PyList_GetItem", "function"),
    ("PyList_GET_ITEM", "macro"),
    ("PyTuple_GetItem", "function"),
    ("PyTuple_GET_ITEM", "macro"),
    ("PyBytes_AsString", "function"),
    ("PyBytes_AS_STRING", "macro"),
    ("Py_IncRef", "function"),
    ("Py_INCREF", "macro"),
    ("PyObject_Size", "function"),
    ("Py_SIZE", "macro"),
    ("PyLong_FromLong", "function"),
    ("PyLong_AsLong", "function"),
    ("PyObject_GetAttrString", "function"),
    ("PyUnicode_AsUTF8String", "function"),
    ("PyType_GetSlot", "function"),
    ("PyFrame_GetBack", "function"),
]


def exported(name):
    """Can the dynamic linker resolve this name in the running interpreter?"""
    return hasattr(ctypes.pythonapi, name)


def main() -> None:
    print("--- is the name a symbol the dynamic linker can find? ---")
    for name, kind in SAMPLE:
        print(f"  {name:<24} {kind:<9} exported: {exported(name)}")

    functions = [n for n, k in SAMPLE if k == "function"]
    macros = [n for n, k in SAMPLE if k == "macro"]
    print("--- the split is total, not a tendency ---")
    print(f"  documented functions in the sample : {len(functions)}")
    print(f"  of those, exported                 : {sum(exported(n) for n in functions)}")
    print(f"  documented macros in the sample    : {len(macros)}")
    print(f"  of those, exported                 : {sum(exported(n) for n in macros)}")

    print("--- what a macro expands to is the thing the stable ABI hides ---")
    print("  PyList_GET_ITEM(o, i) reads ob_item[i] out of the struct at a fixed offset;")
    print("  PyList_GetItem(o, i)  is a call that can change its implementation freely")

    print("--- so the limited API's cost is stated exactly ---")
    print("  every ALL-CAPS accessor becomes a real call, and every struct field")
    print("  becomes an accessor function; you trade inlined field reads for calls")

    print("--- the rule ---")
    print("  if you can see the layout, the layout can change under you; the stable ABI")
    print("  is the promise that you never looked")


if __name__ == "__main__":
    main()
