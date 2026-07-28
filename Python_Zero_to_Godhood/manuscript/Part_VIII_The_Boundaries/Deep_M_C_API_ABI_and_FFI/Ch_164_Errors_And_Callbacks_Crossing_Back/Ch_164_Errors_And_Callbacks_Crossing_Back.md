# Chapter 83: Errors and Callbacks Crossing Back

Three error models meet at the C boundary and none of them translates into the others by default.

Python signals failure by **raising**: the exception propagates up the frame stack until something catches it, and ignoring it is impossible.
C signals failure by **returning a sentinel** and setting a thread-local `errno`: the caller must check, and not checking is legal, silent, and common.
The CPython C-API signals failure by returning a sentinel **and** setting a thread-local error indicator, which is a third thing again.

The dangerous case is the one that runs *backwards*. When C calls a Python callback and that callback raises, the exception has nowhere to go: there are C stack frames between it and any Python `except`, and C frames do not unwind Python exceptions. `ctypes` prints the traceback to stderr, returns a default value to C, and the C function finishes with a wrong answer that its caller never learns about.

And the callback is expensive as well as unsafe. Sorting a thousand integers with `libc.qsort` and a Python comparator measures **112x slower** than `list.sort()`, at **283 nanoseconds per comparison**, which is one boundary crossing per comparison. Calling into C does not make code fast; moving the *loop* into C does, and a callback moves it straight back.

**This is a Deep M boundary chapter.**
It is about the three error models, the direction that cannot propagate, and what the safety machinery costs against what ignoring it costs.

## Section index

- **83.1** Three models, one boundary
- **83.2** The direction that cannot propagate
- **83.3** Measurement: cheap safety, expensive callbacks
- **83.4** Edges and failure modes
- **83.5** Connections
- **83.6** Exercises
- **83.7** Summary and cross-references

Listings live under `code/ch164/` and are re-executed by `make verify` on both verification interpreters.

---

## 83.1 Three models, one boundary

```python
# code/ch164/l01_errors_at_the_boundary.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- C reports failure in the return value, not by raising ---
  open() returned            : -1   (a sentinel, not an exception)
  ctypes.get_errno()         : 2 = ENOENT
--- and errno is only captured if you opened the library with use_errno ---
  same call, same failure    : -1
  ctypes.get_errno() now     : 0   (never captured)
--- an undeclared restype is a silent wrong answer, not an error ---
  atof(b'2.5') with restype declared : 2.5
  the default int restype differs    : True
--- the C-API is the one case ctypes translates for you (PyDLL) ---
  PyLong_AsLong on a str raised : TypeError
  the error indicator was cleared : True
  a good call still works         : 42
--- but an exception in a callback cannot cross C frames ---
  qsort returned normally             : True
  the traceback went to stderr        : True
  the caller was told nothing         : True
```

**The return value is the error report.**
`open()` on a path that does not exist returns `-1`. Nothing raises, nothing warns, and if you do not compare against the sentinel your program continues with an invalid file descriptor. Every C function has a convention of this kind and they are not uniform: `-1`, `NULL`, `0`, a negative errno, a status enum. Reading the manual page is part of writing the binding, and there is no substitute.

**`errno` is only captured if you ask.**
The second block is the trap. The same call fails identically through a library opened without `use_errno=True`, and `ctypes.get_errno()` returns `0`, because ctypes never captured it. This is not ctypes being unhelpful: `errno` is thread-local state that *any* intervening operation can overwrite, including the Python bytecode between the call and your check. `use_errno=True` makes ctypes swap a private errno value in and out around each call, so what you read is what your function set and nothing else. Without it you are reading whatever the interpreter did most recently, and getting `0` is the lucky outcome, because a stale non-zero value would have looked like a real error.

**An undeclared `restype` is a wrong answer, not an error.**
`ctypes` defaults `restype` to `c_int`. `atof` returns a `double`, and reading a double's return register as an int produces a value that has nothing to do with 2.5. The listing prints the correct result and a boolean confirming the default differs, rather than printing the garbage, because the garbage is not specified. There is no diagnostic for this. **Declaring `argtypes` and `restype` is not documentation, it is the only correctness mechanism ctypes has**, and the reason Chapter 43 introduced them first.

**The C-API is the one case that translates for you.**
`ctypes.pythonapi` is a `PyDLL`, and a `PyDLL` checks CPython's error indicator after every call and raises whatever the C function set. `PyLong_AsLong("not an int")` returns `-1` and sets a `TypeError`, and ctypes turns that into a raised `TypeError` in your code, leaving the indicator clear afterwards so the next call starts fresh. Chapter 80 introduced `PyDLL` as the loader that holds the GIL; this is its second job, and the two go together, because checking the error indicator is itself a C-API operation that needs the GIL.

---

## 83.2 The direction that cannot propagate

**Forward, Python to C, is fine.** An exception raised before the call simply prevents it. An error returned by C is a value you inspect.

**Backward, C to Python to C, is where the model breaks.**
`libc.qsort` takes a comparator. `ctypes` wraps a Python function in a `CFUNCTYPE` and gives C a function pointer. When C calls it and the Python function raises, the exception must travel up through C stack frames that know nothing about `PyObject`, `sys.exc_info`, or unwinding. It cannot. There is no mechanism, and inventing one would require every C library in existence to be exception-aware.

What `ctypes` does instead is the only safe option available: it catches the exception at the boundary, prints the traceback to stderr through `sys.unraisablehook`, and returns a default value (zero for an integer return) to the C caller. The listing verifies all three parts: `qsort` returned normally, the traceback reached stderr, and the caller was told nothing.

**The consequence is a wrong answer, not a crash.**
A comparator that returns `0` for every pair tells `qsort` that all elements are equal, so the resulting order is unspecified. The listing deliberately does not print the array afterwards, and says why: the contents are undefined, and the two verification interpreters do in fact produce different orderings. A book that printed one of them would be documenting an accident.

**So the discipline is explicit and non-negotiable.**

- **Catch everything inside the callback.** Wrap the body in `try`/`except BaseException`, record the exception somewhere you own, and return the sentinel the C API expects for failure.
- **Check the recorded exception after the C call returns**, and re-raise it there, where you *are* in Python and unwinding works.
- **Never let a callback do work that can fail in ways you have not enumerated**, because "the callback raised" is not a condition the C library has a code path for.

The pattern is small and worth internalising:

```python
error = None

def callback(a, b):
    global error
    try:
        return do_the_work(a, b)
    except BaseException as exc:      # BaseException: KeyboardInterrupt too
        error = exc
        return 0                      # whatever this C API treats as "no opinion"

library.do_something(CALLBACK(callback))
if error is not None:
    raise error                       # now we are back in Python, and this works
```

**The senior-engineer contrast.**
This is the same problem C++ has when an exception escapes a `noexcept` boundary, or that Rust has at an `extern "C"` function, and both languages solved it the same way: terminate, or catch and convert at the boundary. CPython chose "catch, report, continue" rather than "terminate" because terminating an interpreter over a callback in third-party C code is a worse default. The price of that choice is that the failure is quiet, and quiet is exactly what §83.3's second table says you were paying for anyway.

---

## 83.3 Measurement: cheap safety, expensive callbacks

**Methodology.** `code/ch164/bench_error_handling.py`.
`min` of 15 batches at 20,000 calls for the per-call table, 9 batches at 200 calls for the sort.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**What the safety machinery costs.**

| one `libc.abs` call | time | vs undeclared |
|---|---|---|
| `CDLL`, nothing declared | 142 ns | 1.00x |
| `CDLL`, `use_errno=True` | 166 ns | **1.17x** |
| `CDLL`, `errcheck` callable | 175 ns | **1.23x** |

Capturing `errno` costs 24 nanoseconds per call, because ctypes swaps the thread's errno in and out around the call so nothing between your call and your check can clobber it. An `errcheck` callable costs 33 nanoseconds, because it is a Python function call. Both are small fractions of a crossing that already costs 142 nanoseconds, and neither is remotely a reason to leave a C error unchecked. **Skipping the safety machinery buys 17% of one call and costs you the entire error-detection story.**

**What a callback costs.**

| sort 1,000 ints | time | vs `list.sort()` |
|---|---|---|
| `list.sort()` (all in C) | 26 us | 1.00x |
| build the C array only | 57 us | 2.2x |
| `qsort` + Python comparator | 2,875 us | **112x** |

The middle row is there so the callback's share is not overstated: marshalling a thousand Python ints into a `c_int` array costs 57 microseconds, which is already **more than sorting them in Python**. Subtracting it leaves 2,818 microseconds of actual sorting over roughly `n log2 n` = 9,966 comparisons, which is **283 nanoseconds per comparison**. That figure is not a coincidence: it is one boundary crossing, the same 142 to 220 nanoseconds §83.3's first table and Chapter 43 measured, plus the Python frame the comparator runs in.

**The lesson is Chapter 76's, arriving from the C side.**
Calling into C does not make code fast. Moving the **loop** into C makes code fast, and a callback per element moves the loop straight back into the interpreter while adding a boundary crossing to every iteration. `qsort` with a Python comparator is the worst of both: the interpreter's per-element cost *plus* the FFI's per-call cost, for an algorithm Python already implements in C.

The C API shapes that avoid this are the ones that take **data, not behaviour**: sort an array of a known type, hash a buffer, compress a block, multiply a matrix. When a library's only interface is a callback per element, the boundary is in the wrong place and the honest options are to do the work in Python or to write the callback in C.
**Book I** is the version of that second option this series actually recommends: the comparator, the matcher, the per-element predicate all live on the C++ side, and Python hands across the whole batch rather than a function pointer.

---

## 83.4 Edges and failure modes

**`use_errno=True` is per-library, not per-call.** §83.1.
It is an argument to `CDLL`, and a library opened without it never captures `errno` no matter what you do later. Open one handle with it and reuse that handle.

**On Windows the equivalent is `use_last_error=True`**, with `ctypes.get_last_error()` and `ctypes.WinError()`. The `errno` and `GetLastError` channels are separate, and a Win32 function sets the second, not the first.

**`errcheck` runs on success as well as failure.**
It is called with `(result, func, arguments)` after every call and its return value replaces the result. It is the right place to convert a sentinel into an exception, and the wrong place to do expensive work.

**A callback's exception goes to `sys.unraisablehook`, which tests can capture.** §83.2.
The listing redirects stderr; a test suite can install `sys.unraisablehook` and assert on it. What you cannot do is catch it with `try`/`except` around the C call, because it never propagates there.

**Keep a reference to the `CFUNCTYPE` object.**
`CALLBACK(fn)` returns an object holding the trampoline; if it is garbage collected while C still holds the pointer, the next call jumps into freed memory. Assign it to a variable that outlives the C library's use of it. This is Chapter 81's lifetime problem in its most immediately fatal form.

**The default `restype` is `c_int`, including for functions returning pointers.** §83.1.
On a 64-bit platform this truncates a returned pointer to 32 bits, and dereferencing the result is a crash rather than a wrong number. `restype = ctypes.c_void_p` at minimum, for anything that returns an address.

**Do not compare `errno` before checking the return value.**
`errno` is not cleared on success. A function that succeeded may leave a stale non-zero `errno` from an earlier internal call. The sequence is always: check the documented failure sentinel first, and only then read `errno`.

**A callback that returns an inconsistent ordering is undefined behaviour in `qsort`, not merely a wrong sort.** §83.2.
Some `qsort` implementations read out of bounds when the comparator is inconsistent. The failure mode of a raising comparator is therefore worse than "unspecified order", which is another reason the catch-and-return-sentinel pattern must return a *consistent* sentinel.

---

## 83.5 Connections

**Backward.**
`argtypes` and `restype` as the correctness mechanism are Chapter 43. Whole-buffer calls, the design that avoids callbacks entirely, are Chapter 44. `PyDLL`, the GIL, and why the error-indicator check needs it are Chapter 80. Reference lifetime, which is why the `CFUNCTYPE` object must be kept alive, is Chapter 81. The limited API's constraint on which functions exist to be called is Chapter 82.

**Forward.**
Choosing among `ctypes`, `cffi`, Cython, and a hand-written extension, with this chapter's callback cost as one of the deciding factors, is Chapter 84, which closes this volume. Exception groups and `except*`, Python's own answer to multiple simultaneous failures, are Volume 15. Errors crossing process boundaries rather than language boundaries are Deep E.

**Across books.**
The two books' error models are the two halves of this chapter. **Book I** raises and unwinds with destructors running, and its zero-cost exception model is Chapter 73's subject on the Python side. The C ABI between them carries neither: the seam passes status codes and buffers, and each side converts at its own edge. That is not a limitation to be engineered around; it is the only thing that works, and designing the seam to be narrow is what makes it cheap.

---

## 83.6 Exercises

**1. Lose an error.** Call a failing libc function through a library opened without `use_errno=True`, then through one opened with it. Explain what the first `get_errno()` was actually reporting.

**2. Break a return type.** Call a libc function that returns a `double` without declaring `restype`. Explain why the result is wrong rather than an error, and what would have happened had the function returned a pointer.

**3. Swallow an exception, then stop swallowing it.** Reproduce §83.1's last block. Then rewrite the comparator with the catch-and-re-raise pattern from §83.2 and confirm the exception reaches your code. Say what the C library saw in both cases.

**4. Price your own callback.** Reproduce §83.3's second table and derive the per-comparison cost on your machine. Compare it with your ctypes call overhead from Chapter 43 and account for the difference.

**5. Kill it with a garbage collection.** Create a `CFUNCTYPE` object without keeping a reference, pass it to a C function that stores it, and describe (do not run) what happens on the next call. Then fix it and explain what the fix guarantees.

**6. The design question.** `ctypes` could terminate the process when a callback raises, as Rust does at an `extern "C"` boundary, instead of printing and returning zero. Argue both sides: what "print and continue" costs in silent wrong answers, what "terminate" costs in a long-running server, and which you would choose for a library your team ships.

---

## 83.7 Summary and cross-references

- **Three error models meet at the boundary.** Python raises. C returns a sentinel and sets `errno`. The CPython C-API returns a sentinel and sets a thread-local error indicator. Nothing translates automatically except one case.
- **`errno` is only captured with `use_errno=True`**, which makes ctypes swap a private errno in and out around each call. Without it you read whatever the interpreter did most recently, and `0` is the lucky outcome.
- **An undeclared `restype` is a silent wrong answer.** The default is `c_int`; a function returning a `double` or a pointer is misread with no diagnostic. `argtypes`/`restype` are ctypes' only correctness mechanism.
- **`PyDLL` is the one translating case:** `ctypes.pythonapi` checks CPython's error indicator after every call and raises what the C function set, leaving the indicator clear.
- **An exception cannot cross C frames.** A raising `CFUNCTYPE` callback has its traceback printed to stderr and returns a default value to C; the C caller completes with a wrong answer and learns nothing. The remedy is to catch `BaseException` inside the callback, return the API's failure sentinel, and re-raise after the C call returns.
- **Measured on 3.13.5:** `use_errno=True` costs **1.17x** per call and an `errcheck` callable **1.23x**, on a call that is already 142 ns. Skipping them buys 17% of one call and costs the entire error-detection story.
- **A callback costs a different order of magnitude:** `qsort` with a Python comparator is **112x** slower than `list.sort()` on 1,000 ints, deriving to **283 ns per comparison**, one boundary crossing each. Marshalling the input array alone (57 us) already costs more than sorting in Python (26 us).
- **The C API shapes worth crossing for take data, not behaviour.** A callback per element puts the loop back in the interpreter and adds an FFI crossing to every iteration.
- **Edges:** `use_errno` is per-library; Windows uses `use_last_error`; `errcheck` runs on success too; keep a reference to the `CFUNCTYPE` object or the trampoline is freed under C; check the return sentinel before reading `errno`; an inconsistent comparator is undefined behaviour in `qsort`, not merely an unspecified order.

**Cross-references.** `argtypes`/`restype` → Chapter 43. Whole-buffer calls → Chapter 44. `PyDLL` and the GIL → Chapter 80. Callback object lifetime → Chapter 81. What exists to be called → Chapter 82. Choosing a boundary → Chapter 84. Exception groups → Volume 15. Errors across processes → Deep E.
