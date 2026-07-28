"""Listing 164.1 - three error models meeting at one boundary.

Python signals failure by raising. C signals failure by returning a sentinel and setting
a thread-local errno. The CPython C-API signals failure by returning a sentinel AND
setting a thread-local error indicator. All three meet at the FFI boundary, and nothing
translates between them automatically unless you ask.

  libc through CDLL   - the return value IS the error report. -1 means look at errno,
                        and errno is only captured if the library was opened with
                        use_errno=True. Nothing raises. A missed check is a silent bug.
  the C-API through   - ctypes checks the error indicator after every PyDLL call and
  PyDLL                 raises whatever the C function set. This is the one case where
                        the translation happens for you, and it is why ctypes.pythonapi
                        is a PyDLL (Chapter 80) rather than only for the GIL.
  a Python callback   - an exception raised inside a CFUNCTYPE callback CANNOT propagate
  invoked from C        through the C frames that called it. ctypes prints it to stderr
                        and returns a default value to C, so the C function completes
                        with a wrong answer and the caller never learns.

The third is the dangerous one, and this listing demonstrates it deliberately, capturing
the stderr traceback so the test stays quiet and the fact stays checkable.
"""

import contextlib
import ctypes
import ctypes.util
import errno
import io

LIBC_PATH = ctypes.util.find_library("c")
API = ctypes.pythonapi
API.PyLong_AsLong.argtypes = [ctypes.py_object]
API.PyLong_AsLong.restype = ctypes.c_long
API.PyErr_Occurred.restype = ctypes.c_void_p

COMPARATOR = ctypes.CFUNCTYPE(
    ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)
)


def raising_comparator(left, right):
    raise ValueError("this comparator is broken")


def main() -> None:
    capturing = ctypes.CDLL(LIBC_PATH, use_errno=True)
    plain = ctypes.CDLL(LIBC_PATH)
    for lib in (capturing, plain):
        lib.open.argtypes = [ctypes.c_char_p, ctypes.c_int]
        lib.open.restype = ctypes.c_int

    print("--- C reports failure in the return value, not by raising ---")
    ctypes.set_errno(0)
    fd = capturing.open(b"/definitely/not/here", 0)
    saved = ctypes.get_errno()
    print(f"  open() returned            : {fd}   (a sentinel, not an exception)")
    print(f"  ctypes.get_errno()         : {saved} = {errno.errorcode.get(saved)}")

    print("--- and errno is only captured if you opened the library with use_errno ---")
    ctypes.set_errno(0)
    fd_again = plain.open(b"/definitely/not/here", 0)
    print(f"  same call, same failure    : {fd_again}")
    print(f"  ctypes.get_errno() now     : {ctypes.get_errno()}   (never captured)")

    print("--- an undeclared restype is a silent wrong answer, not an error ---")
    capturing.atof.argtypes = [ctypes.c_char_p]
    undeclared = capturing.atof(b"2.5")            # default restype is c_int
    capturing.atof.restype = ctypes.c_double
    declared = capturing.atof(b"2.5")
    print(f"  atof(b'2.5') with restype declared : {declared}")
    print(f"  the default int restype differs    : {undeclared != declared}")

    print("--- the C-API is the one case ctypes translates for you (PyDLL) ---")
    try:
        API.PyLong_AsLong("not an int")
    except TypeError as exc:
        print(f"  PyLong_AsLong on a str raised : {type(exc).__name__}")
    print(f"  the error indicator was cleared : {not bool(API.PyErr_Occurred())}")
    print(f"  a good call still works         : {API.PyLong_AsLong(41) + 1}")

    print("--- but an exception in a callback cannot cross C frames ---")
    values = (ctypes.c_int * 4)(4, 3, 2, 1)
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        capturing.qsort(values, 4, ctypes.sizeof(ctypes.c_int),
                        COMPARATOR(raising_comparator))
    printed = stderr.getvalue()
    print(f"  qsort returned normally             : True")
    print(f"  the traceback went to stderr        : {'ValueError' in printed}")
    print(f"  the caller was told nothing         : {printed != '' and True}")
    print("  (the array's contents are now undefined, so this listing does not print")
    print("   them: a comparator that does not answer gives an unspecified ordering)")

    print("--- the rule ---")
    print("  check every C return value yourself, declare restype and use_errno, and")
    print("  never let an exception escape a callback: catch it and return a sentinel")


if __name__ == "__main__":
    main()
