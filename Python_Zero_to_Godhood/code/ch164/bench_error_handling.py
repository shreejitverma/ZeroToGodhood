"""Benchmark 164.1 - what the safety machinery costs, and what a callback costs.

Two very different numbers, deliberately in one place.

  164.1a  the per-call cost of the things that make a ctypes call SAFE: capturing errno
          (use_errno=True makes ctypes swap the thread's errno in and out around every
          call) and an errcheck callable that inspects the result. These are the
          overheads people skip to save time.

  164.1b  the per-call cost of the thing that makes a ctypes call UNSAFE and slow at the
          same time: a Python callback invoked from inside C. libc.qsort with a Python
          comparator re-enters the interpreter once per comparison, against list.sort()
          which does the whole sort in C.

The ordering of the two matters more than either number. The safety machinery is cheap
enough that skipping it is never justified by speed; the callback is expensive enough
that it can invert the entire reason for calling into C.

Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

N_SORT = 1_000

SETUP = f"""
import ctypes
import ctypes.util

PATH = ctypes.util.find_library("c")

plain = ctypes.CDLL(PATH)
plain.abs.argtypes = [ctypes.c_int]
plain.abs.restype = ctypes.c_int

capturing = ctypes.CDLL(PATH, use_errno=True)
capturing.abs.argtypes = [ctypes.c_int]
capturing.abs.restype = ctypes.c_int

checked = ctypes.CDLL(PATH)
checked.abs.argtypes = [ctypes.c_int]
checked.abs.restype = ctypes.c_int


def _errcheck(result, func, args):
    if result < 0:
        raise OSError("negative result")
    return result


checked.abs.errcheck = _errcheck

N_SORT = {N_SORT}
COMPARATOR = ctypes.CFUNCTYPE(
    ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)
)


def compare(left, right):
    return (left[0] > right[0]) - (left[0] < right[0])


CMP = COMPARATOR(compare)
source = [(i * 7919) % N_SORT for i in range(N_SORT)]
Array = ctypes.c_int * N_SORT


def qsort_with_python_comparator():
    values = Array(*source)
    plain.qsort(values, N_SORT, ctypes.sizeof(ctypes.c_int), CMP)
    return values[0]


def python_sort():
    values = list(source)
    values.sort()
    return values[0]


def build_only():
    return Array(*source)[0]
"""


def main():
    safety = [
        measure("CDLL, nothing declared", "plain.abs(-1)", SETUP),
        measure("CDLL, use_errno=True", "capturing.abs(-1)", SETUP),
        measure("CDLL, errcheck callable", "checked.abs(-1)", SETUP),
    ]
    report("164.1a  the per-call cost of the safety machinery",
           safety, baseline="CDLL, nothing declared")

    print()
    callback = [
        measure("list.sort()  (all in C)", "python_sort()", SETUP, repeat=9, number=200),
        measure("build the C array only", "build_only()", SETUP, repeat=9, number=200),
        measure("qsort + Python comparator", "qsort_with_python_comparator()",
                SETUP, repeat=9, number=200),
    ]
    report(f"164.1b  sorting {N_SORT:,} ints, with and without a callback per comparison",
           callback, baseline="list.sort()  (all in C)")

    by_label = {r.label: r.min_ns for r in callback}
    sorting_only = by_label["qsort + Python comparator"] - by_label["build the C array only"]
    comparisons = N_SORT * math.log2(N_SORT)
    print(f"derived     : {sorting_only / 1e3:,.0f} us of sorting over about "
          f"{comparisons:,.0f} comparisons")
    print(f"            = {sorting_only / comparisons:.0f} ns per comparison, which is "
          f"one boundary crossing")

    print()
    print("Reading this. The safety machinery is nearly free. Capturing errno costs a")
    print("few nanoseconds per call, because ctypes has to swap the thread's errno in")
    print("and out so that a Python-level operation between your call and your check")
    print("cannot clobber it. An errcheck callable costs more, because it is a Python")
    print("call, and it is still small next to the crossing itself. Neither is a reason")
    print("to leave a C error unchecked.")
    print()
    print("The callback is a different order of magnitude. qsort with a Python")
    print("comparator re-enters the interpreter once per comparison - about n log n")
    print("times - and each re-entry is a boundary crossing plus a frame. The C sort")
    print("loses to the Python sort by a wide margin, which is the point: calling into C")
    print("does not make code fast, moving the LOOP into C does, and a callback moves it")
    print("straight back. The `build the C array only` row separates the marshalling of")
    print("the input from the sorting, so the callback's share is not overstated.")


if __name__ == "__main__":
    main()
