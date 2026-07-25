"""Benchmark 126.1 - the boundary cost is FFI marshalling, not the C-API itself.

len(x) and ctypes.pythonapi.PyObject_Length(x) ultimately run the SAME C function
(the object's length slot). Yet the ctypes route is many times slower, because it
marshals the argument across the FFI boundary (wrap as py_object, dispatch through
libffi) on every call, while len() reaches the C function directly. This measures
both, to show that a COMPILED extension (which has no marshalling: it already holds
the PyObject*) is the fast way to do C-API-heavy work, not the ctypes route.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import ctypes
import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402

N = 5_000_000


def main():
    print("=== 126.1  len(x) vs the same C function via ctypes.pythonapi ===")
    print(provenance())
    print()

    api = ctypes.pythonapi
    api.PyObject_Length.restype = ctypes.c_ssize_t
    api.PyObject_Length.argtypes = [ctypes.py_object]

    x = [1, 2, 3, 4, 5]

    t_builtin = min(timeit.repeat(lambda: len(x), number=N, repeat=5)) / N
    t_ctypes = min(timeit.repeat(lambda: api.PyObject_Length(x), number=N, repeat=5)) / N

    print(f"  len(x)  (direct C call)               : {t_builtin * 1e9:6.1f} ns   1.0x")
    print(f"  ctypes.pythonapi.PyObject_Length(x)   : {t_ctypes * 1e9:6.1f} ns   {t_ctypes / t_builtin:.1f}x")

    print()
    print("Reading this. Both calls run the SAME C function (the object's length")
    print("slot), yet the ctypes route is ~10x slower. The difference is pure FFI")
    print("marshalling: ctypes wraps the argument as a py_object and dispatches")
    print("through libffi on every call, while len() reaches the C code directly.")
    print("So the boundary cost measured in Chapters 43-44 is the MARSHALLING, not")
    print("the C-API. A COMPILED extension calls PyObject_Length with no marshalling")
    print("at all (it already holds the PyObject*), so it runs at len()'s speed. That")
    print("is why C-API-heavy work belongs in a compiled extension, not routed")
    print("through ctypes: ctypes is for calling EXISTING foreign libraries, a")
    print("compiled extension is for writing new fast code against CPython itself.")


if __name__ == "__main__":
    main()
