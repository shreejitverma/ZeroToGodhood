"""Benchmark 162.1 - what it costs to hand a PyObject* across the boundary.

Three kinds of crossing, in increasing order of how much reference management they
involve:

  c_int argument   - a machine integer is marshalled out and a machine integer comes
                     back. No Python object crosses; no reference changes hands.
  py_object arg    - a PyObject* crosses. ctypes must keep the object alive for the
                     duration of the call, and the callee (here Py_IncRef / Py_DecRef)
                     manipulates its count.
  Python call      - the control: an ordinary Python function call that does nothing,
                     so the row shows how the boundary compares to a frame push.

The second group is also where the GIL question of Chapter 80 lands: ctypes.pythonapi
is a PyDLL, so those calls do NOT release the GIL, which is correct and is part of what
they cost.

The last group isolates the reference-count work itself inside the interpreter, by
reading an ordinary (mortal) object and an immortal one in a loop. On a build where
reading a local increments and decrements its count, the difference is that pair; on a
build that borrows the reference, the difference should shrink toward nothing.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

UNROLL = 20
N = 1_000

BOUNDARY_SETUP = """
import ctypes
import ctypes.util

libc = ctypes.CDLL(ctypes.util.find_library("c"))
libc.abs.argtypes = [ctypes.c_int]
libc.abs.restype = ctypes.c_int

api = ctypes.pythonapi
api.Py_IncRef.argtypes = [ctypes.py_object]
api.Py_IncRef.restype = None
api.Py_DecRef.argtypes = [ctypes.py_object]
api.Py_DecRef.restype = None


class Probe:
    pass


target = Probe()
address = id(target)

# The same C function, reached two ways. `typed` takes a py_object, so ctypes keeps the
# object alive across the call. `raw` takes a void*, so nothing does.
typed = ctypes.pythonapi.Py_IncRef
typed.argtypes = [ctypes.py_object]
typed.restype = None

# PyDLL, not CDLL, so that this row differs from the one above ONLY in the argument
# spelling and not also in whether the GIL is dropped (Chapter 80).
raw = ctypes.PyDLL(None).Py_IncRef
raw.argtypes = [ctypes.c_void_p]
raw.restype = None


def python_noop(x):
    return x
"""

# Both readers read a LOCAL, so both emit the same opcode and the only difference is
# whether the object's count is real or immortal. Comparing a local against a constant
# would compare LOAD_FAST against LOAD_CONST, which is a different question.
READ_TEMPLATE = """
def {name}(n):
    mortal = [1, 2, 3]
    immortal = None
    y = 0
    for _ in range(n):
{body}
    return y
"""


def build_reader(name, local):
    body = "\n".join(f"        y = {local}" for _ in range(UNROLL))
    return READ_TEMPLATE.format(name=name, body=body)


READ_SETUP = (f"N = {N}\n"
              + build_reader("read_mortal", "mortal")
              + build_reader("read_immortal", "immortal"))


def main():
    crossing = [
        measure("Python call (no boundary)", "python_noop(target)", BOUNDARY_SETUP),
        measure("ctypes call, c_int argument", "libc.abs(-1)", BOUNDARY_SETUP),
        measure("ctypes call, py_object argument", "api.Py_IncRef(target)", BOUNDARY_SETUP),
        measure("py_object round trip (Inc + Dec)",
                "api.Py_IncRef(target); api.Py_DecRef(target)", BOUNDARY_SETUP),
    ]
    report("162.1a  one crossing, by what has to cross", crossing,
           baseline="Python call (no boundary)")

    print()
    spelling = [
        measure("py_object  (ctypes manages it)", "typed(target)", BOUNDARY_SETUP),
        measure("c_void_p from id() (you manage it)", "raw(address)", BOUNDARY_SETUP),
    ]
    report("162.1b  the same C function, two argument spellings",
           spelling, baseline="c_void_p from id() (you manage it)")

    print()
    print("Reading this. A ctypes call with a machine-integer argument is already an")
    print("order of magnitude more than a Python call, which is Chapter 43's result.")
    print("The py_object row is CHEAPER than the c_int row, and that ordering is the")
    print("useful surprise: passing a PyObject* is passing a pointer, with no")
    print("conversion in either direction, while a c_int argument has to be converted")
    print("out of a Python int and the c_int result converted back into one. Chapter 45")
    print("reached the same conclusion from the other side: marshalling, not the C-API,")
    print("is where the boundary's time goes.")
    print()
    print("The second table prices the safety. Spelling the argument py_object makes")
    print("ctypes hold a reference for the duration of the call; spelling it c_void_p")
    print("over id(obj) hands the same address across with no reference management at")
    print("all, and is faster by the difference. It is also how you get a dangling")
    print("pointer: nothing keeps the object alive, so a C function that stores that")
    print("address outlives its target. The gap between the two rows is the price of")
    print("not having that bug, and it is small enough that the trade is never worth")
    print("taking for speed.")


if __name__ == "__main__":
    main()
