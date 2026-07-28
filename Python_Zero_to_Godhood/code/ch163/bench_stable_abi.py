"""Benchmark 163.1 - what this book can and cannot measure about the limited API.

This benchmark exists partly to state a negative result honestly, because the obvious
question about the limited API is a performance question and the obvious measurement
does not answer it.

What CANNOT be measured from Python: the difference between a macro that inlines a
struct field read (PyList_GET_ITEM) and the exported function that must replace it under
Py_LIMITED_API (PyList_GetItem). That difference lives entirely inside a compiled
extension, and this book's harness has no extension build. The chapter cites it; it does
not measure it.

What was ATTEMPTED and did not separate: two pairs of C-API entry points that differ in
exactly the way limited-API code cares about - a C-string name against an already-built
one, and a borrowed-reference accessor against a generic new-reference one. Through
ctypes these come out indistinguishable, because the crossing costs about fifty times
what the difference between them could be. That null result is reported rather than
dropped.

What IS measured, and is the useful number: the size of the boundary tax itself. An
attribute read costs about 4 ns in the interpreter and about 220 ns through ctypes. Any
argument about which C-API entry point an extension should use is an argument about a
few nanoseconds inside a call that costs fifty times that to reach from Python - which
is the same conclusion Chapters 43 and 45 reached, arriving from a third direction.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import ctypes

api = ctypes.pythonapi

api.PyObject_GetAttrString.argtypes = [ctypes.py_object, ctypes.c_char_p]
api.PyObject_GetAttrString.restype = ctypes.py_object

api.PyObject_GetAttr.argtypes = [ctypes.py_object, ctypes.py_object]
api.PyObject_GetAttr.restype = ctypes.py_object

api.PyList_GetItem.argtypes = [ctypes.py_object, ctypes.c_ssize_t]
api.PyList_GetItem.restype = ctypes.py_object

api.PySequence_GetItem.argtypes = [ctypes.py_object, ctypes.c_ssize_t]
api.PySequence_GetItem.restype = ctypes.py_object


class Target:
    attribute = 42


target = Target()
name_bytes = b"attribute"
name_str = "attribute"
items = list(range(64))
"""


def main():
    lookup = [
        measure("target.attribute      (interpreter)", "target.attribute", SETUP),
        measure("PyObject_GetAttr      (built name)",
                "api.PyObject_GetAttr(target, name_str)", SETUP),
        measure("PyObject_GetAttrString (C string)",
                "api.PyObject_GetAttrString(target, name_bytes)", SETUP),
    ]
    report("163.1a  one attribute read, with and without the boundary",
           lookup, baseline="target.attribute      (interpreter)")

    print()
    index = [
        measure("items[7]              (interpreter)", "items[7]", SETUP),
        measure("PyList_GetItem        (borrowed ref)", "api.PyList_GetItem(items, 7)", SETUP),
        measure("PySequence_GetItem    (new ref)", "api.PySequence_GetItem(items, 7)", SETUP),
    ]
    report("163.1b  one list index, with and without the boundary",
           index, baseline="items[7]              (interpreter)")

    print()
    print("Reading this. The two C-API rows in each table are within a few percent of")
    print("each other, which is a NULL result and is reported as one: at this resolution")
    print("ctypes cannot separate a C-string name from a built one, or a borrowed-")
    print("reference accessor from a generic new-reference one. The crossing costs about")
    print("fifty times what those differences could amount to, and it swamps them.")
    print()
    print("The number that survives is the tax: about 4-5 ns inside the interpreter")
    print("against about 220 ns through ctypes, roughly 45x. That is the frame for every")
    print("limited-API performance argument. Choosing between two C-API entry points is")
    print("worth a few nanoseconds INSIDE a compiled extension, where there is no")
    print("crossing to pay; it is worth nothing at all from ctypes. And the cost the")
    print("limited API really imposes - inlined field reads becoming calls - is a cost")
    print("inside that extension, which is exactly where this measurement cannot reach.")


if __name__ == "__main__":
    main()
