# Chapter 45: The C-API from the Outside

The C-API is CPython's other half.
Everything this book has taught, `PyObject` headers (Chapter 19), reference counting (Chapter 31), the type slots that dispatch `len` and `+` (Chapter 20), attribute lookup (Chapter 21), is implemented as C functions operating on `PyObject *` pointers, and those functions, `Py_INCREF`, `PyList_Size`, `PyObject_Length`, `PyObject_GetAttr`, *are* the C-API.
A C extension module is code that calls them directly.
Writing one normally means C source and a compiler, which this pure-Python book cannot execute in its verification harness.
But there is a way to *see* the C-API, and call it, without any of that: **`ctypes.pythonapi`** exposes CPython's own C functions to Python, so you can call `Py_IncRef` or `PyObject_Length` from a Python prompt and watch the machinery you have been reading about operate.

This chapter uses that window for three purposes.
First, to make the C-API **concrete**: `Py_IncRef`/`Py_DecRef` are literally the reference-counting primitives of Chapter 31, and calling them moves the refcount you measured there.
Second, to complete the **boundary picture**: a Python function can be wrapped as a C callback (`CFUNCTYPE`) so C calls *into* Python, the reverse of Chapters 43-44.
Third, to settle *what the boundary cost actually is*: `len(x)` and `ctypes.pythonapi.PyObject_Length(x)` run the identical C function, yet the `ctypes` route is **10x** slower, which proves the cost is FFI **marshalling**, not the C-API, and therefore that a *compiled* extension (no marshalling) is the fast way to do C-API-heavy work.

**This is Deep M's C-API chapter.**
It ties the whole book's mechanisms (Chapters 19, 20, 31) to their C-level implementation, and motivates the compiled extension modules that Deep M's remaining chapters cover. It reuses `ctypes` (Chapters 43-44) as the observation tool.

## Section index

- **45.1** `ctypes.pythonapi`: calling CPython's C functions, and callbacks
- **45.2** What the C-API is, and why extensions compile
- **45.3** Measurement: marshalling, not the C-API, is the cost
- **45.4** Edges and failure modes
- **45.5** Connections
- **45.6** Exercises
- **45.7** Summary and cross-references

Listings live under `code/ch126/` and are re-executed by `make verify` on both verification interpreters.

---

## 45.1 `ctypes.pythonapi`: calling CPython's C functions, and callbacks

```python
# code/ch126/l01_capi_from_python.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- Py_IncRef / Py_DecRef ARE the C-level refcount primitives (Chapter 31) ---
  refcount delta after Py_IncRef : +1
  refcount delta after Py_DecRef : 0   (restored)
--- call the C-API functions behind len() directly ---
  PyList_Size([1, 2, 3])       : 3
  PyObject_Length('hello')     : 5
  (PyObject_Length is the C implementation that len() calls)
--- the other direction: a Python function as a C callback ---
  square is a C function pointer : True
  calling it through C : square(7) = 49
--- the rule ---
  ctypes.pythonapi calls CPython's C-API from Python (Py_IncRef, len's
  C impl); CFUNCTYPE wraps a Python function so C can call back into it
```

**`Py_IncRef`/`Py_DecRef` are Chapter 31, made tangible.**
`ctypes.pythonapi` is a handle on the Python interpreter's *own* symbols, so `api.Py_IncRef(ctypes.py_object(obj))` calls the exact C function that `Py_INCREF` expands to. The output shows it: the refcount rises by 1, and `Py_DecRef` restores it. This is the C-API's central contract (Chapter 31, §31.2), balance every incref with a decref, executed by hand. `ctypes.py_object(obj)` is the marshalling that hands C the real `PyObject *` (not a copy), which is why the C function affects the actual object's count.

**The C-API functions behind builtins.**
`PyList_Size` and `PyObject_Length` are the C implementations that `len()` dispatches to (Chapter 20's slot dispatch, at the C level). Calling them via `ctypes.pythonapi` returns `3` and `5`, the same answers `len()` gives, because it is the same code. Seeing `len("hello")` resolve to `PyObject_Length("hello")` connects the Python builtin to its C slot concretely.

**The reverse direction: Python as a C callback.**
`CFUNCTYPE(restype, *argtypes)` wraps a Python function as a **C function pointer** that C code can call. `square` becomes a real callable-from-C pointer (it *is* a `ctypes` function pointer), and invoking it runs the Python function (`square(7)` is `49`). This is how C libraries take callbacks (`qsort`'s comparator in Chapter 44, an event handler, a signal callback): Python hands C a function pointer, and C calls back across the boundary into the interpreter.

So `ctypes.pythonapi` shows the boundary in both directions: Python calling CPython's C-API (down into C), and C calling a Python callback (up into Python), the same two directions a real extension module works in.

---

## 45.2 What the C-API is, and why extensions compile

With the C-API now concrete, the shape of a real extension module follows, and so does why it must be compiled.

A **C extension module** is a shared library that CPython imports like a `.py` file, but its functions are written in C against the C-API.
Such a module:

- Receives arguments as `PyObject *` and parses them (`PyArg_ParseTuple`).
- Operates on them with C-API calls (`PyList_Size`, `PyLong_AsLong`, `PyDict_GetItem`, the same functions §45.1 called via `ctypes`).
- Manages reference counts by hand (`Py_INCREF`/`Py_DECREF`, the §45.1 primitives), honouring the ownership contract of Chapter 31.
- Returns a `PyObject *` (or `NULL` plus a set exception).

The reason this is *compiled* rather than routed through `ctypes` is exactly §45.3's measurement: a compiled extension calls `PyObject_Length` with **no marshalling**, it already holds the `PyObject *`, so the call is a direct C function call at full speed, whereas `ctypes` wraps and dispatches every argument through `libffi`.
For code that makes many C-API calls (the inner loop of a parser, a numeric kernel, a data-structure operation), that marshalling difference is the whole performance argument.

This clarifies the **two tools and their jobs**, the central Deep M distinction:

- **`ctypes`** calls into an **existing foreign C library** you did not write (a codec, a vendor SDK, an OS function). No build step; you declare signatures and call. It pays FFI marshalling per call (Chapters 43-44), so it suits few-crossings-much-work.
- **A C extension** is **new C code you write against CPython**, compiled into a module. It has full-speed C-API access (no marshalling) and is the tool for C-API-heavy inner loops, but it requires C, a compiler, and manual refcount discipline (with the segfault risk of Chapter 43).

Higher-level tools sit on top: **Cython** compiles annotated Python to a C extension; **pybind11** (C++) and **PyO3** (Rust) generate the C-API glue and manage refcounts for you; **cffi** is a cleaner FFI than `ctypes`. All of them ultimately produce or call the C-API this chapter exposed. Understanding the raw C-API, even from the outside via `ctypes.pythonapi`, is what makes those tools legible: they are automating the `Py_INCREF`/`PyArg_ParseTuple`/`PyObject *` dance you just watched.

---

## 45.3 Measurement: marshalling, not the C-API, is the cost

**Methodology.** `code/ch126/bench_capi_marshalling.py`.
`len(x)` versus `ctypes.pythonapi.PyObject_Length(x)` on the same list, `min` of 5 runs, 5,000,000 calls.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| length of a list | ns/call | vs `len` |
|---|---|---|
| `len(x)` (direct C call) | 16.1 | 1.0x |
| `ctypes.pythonapi.PyObject_Length(x)` | 161.2 | **10.0x** |

Both calls run the **identical C function**, the object's length slot, yet the `ctypes` route is **10x** slower (8.7x on 3.14.6).
Since the C code is the same, the 10x is *entirely* the FFI **marshalling**: `ctypes` wraps the argument as a `py_object` and dispatches through `libffi` on every call, while `len()` reaches the C function directly through the interpreter's slot dispatch (Chapter 20).

This is the measurement that resolves the whole Deep M boundary story.
The ~10x cost seen in Chapters 43-45 is **not the cost of C, and not the cost of the C-API**, it is the cost of the `ctypes` **marshalling layer** that sits between Python and the foreign function.
Two consequences follow:

- **A compiled C extension has no marshalling.** It receives the `PyObject *` and calls `PyObject_Length` directly, so it runs at `len()`'s speed, not `ctypes`'s. This is *why* C-API-heavy work belongs in a compiled extension: it eliminates the layer that costs the 10x.
- **`ctypes` is still right for its job.** Calling an *existing* foreign library where each call does substantial work (Chapters 43-44), the marshalling is amortized and irrelevant. It is the wrong tool only for C-API-heavy inner loops, which is precisely what compiled extensions are for.

So the tool choice is sharp: **`ctypes` to reach existing C libraries** (few crossings, much work each, marshalling amortized); **a compiled extension to write new fast code against CPython** (many C-API calls, no marshalling). The 10x is the dividing line, and this chapter measured it by running the same C function both ways.
This completes the boundary picture: Chapter 43 (call cost), Chapter 44 (amortize with whole buffers), Chapter 45 (the cost is marshalling, so compile when you need many C-API calls), three measurements, one coherent rule for where and how to cross into C.

---

## 45.4 Edges and failure modes

**`ctypes.pythonapi` bugs crash the interpreter.**
Calling C-API functions by hand with wrong signatures, unbalanced refcounts, or invalid `PyObject *`s segfaults the process (Chapter 43). It is a *learning and observation* tool, not something to build production logic on. Real C-API code belongs in a compiled extension where the compiler checks types.

**Refcount balance is on you.** §45.1.
`Py_IncRef` without a matching `Py_DecRef` leaks; an extra `Py_DecRef` frees a live object (use-after-free). The Chapter 31 contract is unforgiving at the C level, and `ctypes.pythonapi` gives you no guardrails.

**`ctypes.py_object` passes the real object, not a copy.**
The C-API operates on your actual `PyObject *`, so a C-API call that mutates the object (or its refcount) affects the live Python object immediately. This is the point, and the hazard.

**Not all C-API is safely reachable via `ctypes`.**
Macros (`Py_INCREF` is often a macro, hence the `Py_IncRef` *function* form), inline functions, and anything depending on compile-time layout are not callable through `ctypes.pythonapi`. It reaches exported *functions* only.

**Callbacks re-cross the boundary and touch the GIL.** §45.1, Chapter 44.
A Python callback called from C pays the boundary per call and must hold the GIL to run Python code. Callback-heavy C loops serialize on the GIL and lose C's potential parallelism.

**Signatures must be declared for correctness.**
As in Chapters 43-44, set `restype`/`argtypes` on `pythonapi` functions. `PyObject_Length` returning a `Py_ssize_t` guessed as `int` truncates on overflow; a wrong argument type corrupts the call.

**The C-API is version-specific.**
C-API functions, structs, and macros change across CPython versions (some are stable-ABI, most are not). Code against the raw C-API may need per-version handling; the **stable ABI** (`abi3`) exists to mitigate this and is a Deep M topic.

---

## 45.5 Connections

**Backward.**
`Py_IncRef`/`Py_DecRef` are Chapter 31's reference counting, at the C level. `PyObject_Length`/`PyList_Size` are the C implementations of Chapter 20's slot dispatch (`len` -> `sq_length`). `PyObject *` and `py_object` marshalling are Chapter 19's uniform object header. The FFI marshalling cost is Chapters 43-44's boundary.

**Forward.**
Writing an actual **compiled extension module** (`PyArg_ParseTuple`, `PyModuleDef`, the build with `setuptools`/`meson`), the **stable ABI** (`abi3`) for version-portable extensions, and the **limited API** are the rest of **Deep M**. Cython, pybind11, PyO3, and cffi (the tools that generate this glue) are ecosystem topics. `Py_buffer` (the C-API side of the buffer protocol) connects to Chapter 44 and Deep Q Chapter 37.

**Across books.**
The C-API is the foundation under **Book I**'s performance-critical native code: NumPy, pandas, and the domain's C/C++/Rust libraries are all C-API extensions, receiving `PyObject *`s, operating in C, managing refcounts. When the order-book system drops to native code for a hot path, a matching kernel, a decoder, it does so as a compiled extension (or via Cython/PyO3), not through `ctypes`, precisely for the §45.3 reason: the inner loop makes many operations, and a compiled extension pays no per-call marshalling, while `ctypes` would pay 10x on each. This chapter's `ctypes.pythonapi` window is how a Python engineer *reads* what those extensions do, before reaching for the compiler.

---

## 45.6 Exercises

**1. Move the refcount by hand.** Reproduce §45.1: use `Py_IncRef`/`Py_DecRef` via `ctypes.pythonapi` and confirm the refcount delta with `sys.getrefcount`. Explain how this is Chapter 31's contract executed manually, and what an unbalanced call would do.

**2. Call len's C function.** Call `PyObject_Length` and `PyList_Size` via `ctypes.pythonapi` and confirm they match `len()`. Explain, using Chapter 20, what C slot `len()` dispatches to and why these give the same answer.

**3. A callback into Python.** Wrap a Python function as a `CFUNCTYPE` and confirm it is a C function pointer that runs your Python code. Then pass it to a C function that uses it (e.g. `qsort` from Chapter 44) and explain the two boundary crossings involved.

**4. Measure the marshalling.** Reproduce §45.3. Confirm the `ctypes.pythonapi` route is ~10x `len()` on the same C function. Explain precisely what the 10x is (not C, not the C-API) and why a compiled extension avoids it.

**5. The design question.** `ctypes` reaches existing libraries with a per-call marshalling cost; a compiled extension writes new C-API code with none. Argue when each is correct, using §45.3's 10x and Chapter 44's amortization. Then argue why tools like Cython/PyO3 exist, what part of the raw C-API (this chapter) do they automate, and why is that automation worth it?

---

## 45.7 Summary and cross-references

- The **C-API** is the set of C functions operating on `PyObject *` that implement CPython; a **C extension** calls them directly. **`ctypes.pythonapi`** exposes them to Python, so you can *see* and call the C-API without writing C.
- **`Py_IncRef`/`Py_DecRef`** are Chapter 31's reference-counting primitives; **`PyObject_Length`/`PyList_Size`** are the C implementations behind `len()`; **`ctypes.py_object`** passes the real `PyObject *`. A **`CFUNCTYPE`** wraps a Python function as a C callback (C calling into Python).
- **Measured:** `len(x)` and `ctypes.pythonapi.PyObject_Length(x)` run the **same C function**, yet `ctypes` is **10x** slower. The cost is FFI **marshalling**, not the C-API, so a **compiled extension** (no marshalling) runs C-API-heavy work at full speed.
- **Tool choice:** **`ctypes`** to call *existing* foreign libraries (marshalling amortized over big work); a **compiled extension** to write *new* C-API-heavy code (no marshalling). The 10x is the dividing line.
- **Edges:** `ctypes.pythonapi` bugs segfault (an observation tool, not for production); refcount balance is manual and unforgiving; declare signatures; the C-API is version-specific (the stable ABI mitigates it).

**Cross-references.** Reference counting (`Py_INCREF`/`DECREF`) → Chapter 31. Slot dispatch behind `len` → Chapter 20. `PyObject` header / `py_object` → Chapter 19. FFI call cost and buffer amortization → Chapters 43-44. Compiled extensions, the stable ABI, `Py_buffer`, Cython/PyO3 → the rest of Deep M. Buffer protocol → Deep Q Chapter 37.
