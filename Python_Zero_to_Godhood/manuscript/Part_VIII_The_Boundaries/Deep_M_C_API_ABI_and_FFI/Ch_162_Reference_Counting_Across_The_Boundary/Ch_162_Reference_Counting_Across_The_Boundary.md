# Chapter 81: Reference Counting Across the Boundary

Inside Python, reference counting is invisible. The interpreter takes a reference when a name is bound, drops it when the name goes away, and the arithmetic always balances because the same code does both halves.

The moment a `PyObject*` crosses into C, the arithmetic becomes a **contract**, and the contract has exactly two forms.
An **owned** reference is one the C code received or created and must eventually release; failing to release it is a **leak**.
A **borrowed** reference is one the C code may use only while the caller's reference is alive, and must not release; releasing it is a **premature free**, which is a use-after-free for whoever still holds the object.

Neither error is detected. A leak is a program that grows; a premature free is a segmentation fault, usually somewhere unrelated, usually much later. This is the part of the C boundary that is genuinely dangerous, and it is the reason Chapter 80's "hold the GIL when you touch Python objects" is a correctness rule rather than a performance preference.

Python can watch all of it, because CPython's own `Py_IncRef` and `Py_DecRef` are reachable through `ctypes.pythonapi`.

**This is a Deep M boundary chapter.**
It makes the counting observable, stages a real leak, shows the keep-alive graph `ctypes` maintains so you do not have to, and prices what that safety costs.

## Section index

- **81.1** Watching the count, and a leak on purpose
- **81.2** Owned, borrowed, and who keeps the object alive
- **81.3** Measurement: what a reference costs to hand across
- **81.4** Edges and failure modes
- **81.5** Connections
- **81.6** Exercises
- **81.7** Summary and cross-references

Listings live under `code/ch162/` and are re-executed by `make verify` on both verification interpreters.

---

## 81.1 Watching the count, and a leak on purpose

```python
# code/ch162/l01_refcounts_at_the_boundary.py
```

Verified output (CPython 3.13.5):

```text
--- what does sys.getrefcount count? (the local row is version-dependent) ---
  a local name             : 2
  a module global          : 2
  an item read from a list : 2
--- so read DELTAS, not absolute counts: those are version-stable ---
  one Py_IncRef moves the count by : 1
  IncRef then DecRef is balanced   : True
  getrefcount(a temporary)         : 1   (the argument alone)
--- a PyObject* is just an address; id() is that address ---
  cast(id(obj), py_object).value is obj : True
--- immortal objects (PEP 683): the count does not move ---
  a fresh list : delta 1   (ordinary, mortal)
  None         : delta 0   (immortal)
  True         : delta 0   (immortal)
  5            : delta 0   (immortal)
  'spam'       : delta 0   (immortal)
--- a leak, staged: one IncRef that nothing balances ---
  alive after del and a full gc.collect() : True
  (no cycle is involved, so the collector cannot help: the count is simply wrong)
  alive after the missing DecRef is supplied : False
--- ctypes tracks keep-alive edges so a pointer cannot outlive its buffer ---
  cast(buffer, c_char_p)._objects is set : True
  from_buffer(bytearray)._objects is set : True
  writing through it reaches the bytearray : b'abcd' -> b'Abcd'
  bytearray grows once the export is gone : b'Abcd!'
```

**Absolute counts are not portable, and 3.14 is the proof.**
On 3.14.6 the first block differs in exactly one line:

Verified output (CPython 3.14.6):

```text
  a local name             : 1
  a module global          : 2
  an item read from a list : 2
```

`sys.getrefcount(local)` returns one *less* on 3.14 than on 3.13, while the global and the list-item rows are unchanged. The cause is `LOAD_FAST_BORROW` (Chapter 75): 3.14 reads a local without taking a reference when it can prove the borrow is safe, so passing a local to `getrefcount` no longer creates the temporary reference that every previous version created. Reading the same object through `LOAD_GLOBAL` or out of a list still does.

The lesson generalises beyond this one change. **Read deltas, never absolute counts.** `one Py_IncRef moves the count by: 1` is true on both interpreters and will stay true; `getrefcount(x) == 2` is a statement about a compiler optimisation. Test suites that assert on absolute refcounts break on interpreter upgrades, and this is the upgrade that broke a lot of them.

**A `PyObject*` is an address, and `id()` is that address.**
`ctypes.cast(id(obj), ctypes.py_object).value is obj` is `True`. This is worth seeing once because it demystifies the whole boundary: there is no marshalling, no handle table, no proxy. The thing C receives is the same pointer the interpreter holds, which is precisely why the reference contract matters and why nothing can be checked at the boundary.

**Immortal objects have no count to get wrong.**
Since PEP 683 (3.12), `None`, `True`, `False`, small integers, and interned strings are **immortal**: their reference count is pinned at a sentinel and `Py_IncRef` / `Py_DecRef` on them are no-ops. The listing shows the delta is `0` for each and `1` for an ordinary list. This was done for free-threading, so that the most-shared objects in the interpreter do not become a cache-line contention point (Deep L), and it has the side effect that mishandling a reference to `None` is harmless while mishandling one to your own object is not.

**The staged leak.**
`Py_IncRef(victim)` followed by `del victim` is exactly what a C function that forgot its `Py_DECREF` does. The object survives `del` *and* a full `gc.collect()`, and the listing states why in the line beneath: no cycle is involved, so the cyclic collector has nothing to find. The count is simply wrong, and the cyclic collector is not a leak detector, it is a cycle detector. Supplying the missing `Py_DecRef` afterwards frees the object, which is the proof that the count was the only thing keeping it alive.

This is the leak profile that C extensions actually produce, and it is why `tracemalloc` (Chapter 85) shows growing allocations with no Python-level referrer: the referrer is a count, not an object.

---

## 81.2 Owned, borrowed, and who keeps the object alive

**The two contracts, stated as the C-API states them.**

| the C function has | it must | getting it wrong gives |
|---|---|---|
| an **owned** reference (from `Py_BuildValue`, `PyObject_CallObject`, most constructors, or an explicit `Py_INCREF`) | eventually `Py_DECREF` it | a leak |
| a **borrowed** reference (from `PyList_GetItem`, `PyDict_GetItem`, `PyTuple_GetItem`, most arguments) | **not** decref it, and not keep it past the owner's lifetime | a premature free, then a use-after-free |

The asymmetry that catches people is that the two look identical in C. Both are `PyObject *`. Which one you have is documented, not typed, and the documentation is the only thing standing between a working extension and a heap corruption. Modern CPython has added `Py_NewRef` and `Py_XNewRef` to make "I want to own this borrowed thing" an expression rather than a two-line ritual, but the underlying contract is unchanged.

**The senior-engineer contrast.**
This is `shared_ptr` versus a raw pointer, without the type system's help. C++ makes ownership visible in the signature; Rust makes it checkable at compile time. The C-API encodes it in prose. That is a deliberate trade: the C-API is a **C** API, usable from any language with a C FFI, and encoding ownership in types would require a type system it cannot assume. The cost is that every extension author re-implements the discipline by hand, and the tooling that helps most is not a compiler but a debug build with `Py_REF_DEBUG` and a test suite that watches deltas.

**How `ctypes` keeps you out of this.**
The last block of the listing is `ctypes` doing the work. When you `cast` a buffer to a pointer type, or build a ctypes object over someone else's memory with `from_buffer`, `ctypes` records the objects that must stay alive in a private `_objects` attribute on the result. That attribute is the keep-alive graph: as long as the pointer object is reachable, so is the buffer it points into.

This is the same problem `memoryview` solves with the export count (Chapter 79), approached from the other end. The export count stops the *owner* from moving memory while a borrower exists; `_objects` stops the *owner* from being collected while a borrower exists. Both exist because a raw pointer plus a garbage collector is a use-after-free waiting for the right timing, and the listing's final lines show the two mechanisms interacting: the `from_buffer` array is an export, so the `bytearray` refuses to grow until the array is deleted.

**The rule for code you write.**
When you hand an address to C, ask what keeps the target alive for as long as C will hold it. If the answer is "a local variable in the calling frame" and C stores the pointer somewhere, you have a bug that will reproduce only under memory pressure. The three sound answers are: pass a `py_object` so `ctypes` holds a reference, keep an explicit reference in a structure whose lifetime you control, or copy the data so there is nothing to keep alive.

---

## 81.3 Measurement: what a reference costs to hand across

**Methodology.** `code/ch162/bench_refcount_boundary.py`.
`min` of 15 batches, 20,000 calls per batch.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| one crossing | time | vs a Python call |
|---|---|---|
| Python call (no boundary) | 11 ns | 1.0x |
| `ctypes` call, `py_object` argument | 119 ns | 10.8x |
| `ctypes` call, `c_int` argument | 150 ns | 13.5x |
| `py_object` round trip (`Py_IncRef` + `Py_DecRef`) | 236 ns | 21.3x |

**The useful surprise is the ordering.**
Passing a `PyObject*` is **cheaper** than passing a `c_int`, by about 20%. That inverts the intuition that "handing a Python object to C must cost more", and the reason is that passing a `PyObject*` is passing a **pointer**, with no conversion in either direction, while a `c_int` argument must be converted out of a Python `int` and the `c_int` result converted back into one. Chapter 45 reached the same conclusion from the other side: **marshalling, not the C-API, is where the boundary's time goes.**

**What the safety costs.**

| the same C function, two argument spellings | time |
|---|---|
| `c_void_p` from `id(obj)` (you manage the lifetime) | 83 ns |
| `py_object` (ctypes holds a reference for the call) | 117 ns (**1.42x**) |

Both rows call the same `Py_IncRef` through a `PyDLL`, so they differ only in how the argument is spelled and not in whether the GIL is dropped. Spelling it `py_object` makes `ctypes` hold a reference across the call. Spelling it `c_void_p` over `id(obj)` hands the identical address across with no reference management at all, and is 34 nanoseconds faster.

It is also exactly how you produce a dangling pointer: nothing keeps the object alive, so if the C function stores that address anywhere, it outlives its target. **34 nanoseconds is the price of not having that bug**, and it is small enough that taking the trade for speed is never the right call. The `c_void_p` spelling is correct only when you can point at what keeps the object alive independently, which is a design property, not a micro-optimization.

**Book I**'s side of the shared system is where this contract is actually enforced by a type system rather than by prose: the matching engine holds its tick buffer by value or by a smart pointer with a lifetime the compiler checks, and the Python side hands it a `memoryview` whose export count makes the borrow visible to CPython. The seam works because both halves independently guarantee the target outlives the pointer, and neither relies on the other having read the documentation.

---

## 81.4 Edges and failure modes

**Never assert on an absolute refcount.** §81.1.
`sys.getrefcount(x) == 2` broke on 3.14 for locals because of `LOAD_FAST_BORROW`. Deltas across an operation are stable; totals are not.

**`gc.collect()` does not find leaks, it finds cycles.** §81.1.
An over-incremented object is not garbage from the collector's point of view; its count says it is in use. If `tracemalloc` shows growth with no Python referrer, suspect a C-side count, not a cycle.

**Immortal objects hide bugs.** §81.1.
An extension that mishandles references to `None`, `True`, or small integers passes every test, because those counts do not move. The same code corrupts an ordinary object. Test with objects you allocated.

**Borrowed references expire when the container changes.**
`PyList_GetItem` returns a borrowed reference that is valid only while the list still holds the item. Any operation that could remove or replace it, including one that triggers arbitrary Python code through a `__del__` or a comparison, invalidates the pointer. This is the most common real-world premature-free in extension code.

**A `__del__` or weakref callback can run at any `Py_DECREF`.**
Dropping the last reference runs the finalizer, which is arbitrary Python code, which can call back into your extension, re-enter your data structures, and resurrect the object. Decref *after* you have restored your invariants, never in the middle of an update.

**`_objects` is private and not a substitute for design.** §81.2.
It is `ctypes`' internal keep-alive record. Reading it to diagnose a lifetime question is fair; relying on its shape is not. And it only tracks what `ctypes` itself constructed, so an address you computed by hand is not in it.

**Free-threading changes the mechanics but not the contract.**
Under PEP 703 (Deep L) refcounts are atomic and some objects are biased to an owning thread, so a race is far more likely to be detected and far more expensive. The owned-versus-borrowed contract is identical; only the cost and the failure mode change.

**The debug build is the real tool.**
A `--with-pydebug` interpreter carries `Py_REF_DEBUG` totals and asserts on negative counts, and it will find in seconds what a release build hides for months. Neither of this book's verification interpreters is a debug build, which is stated here rather than glossed.

---

## 81.5 Connections

**Backward.**
Holding the GIL when touching Python objects, and why that is a correctness rule, is Chapter 80. The export count, which is the same lifetime problem solved for buffers, is Chapter 79. `ctypes.pythonapi` and the C-API surface reachable from Python is Chapter 45. FFI marshalling cost is Chapter 43. Reference counting as CPython's primary memory-management strategy, and the cyclic collector that supplements it, are Deep B (Chapters 120 and 121). `tracemalloc` for finding the growth is Chapter 85.

**Forward.**
The stable ABI, which constrains which of these functions an extension may call and freezes their semantics across versions, is Chapter 82. Compiled extensions, where you write the `Py_DECREF` yourself, are Chapter 83. Errors and callbacks crossing back into Python are Chapter 84. Immortality's real purpose, and atomic refcounts, are Deep L.

**Across books.**
The contrast with **Book I** is the sharpest in this volume. C++ encodes ownership in the type (`unique_ptr`, `shared_ptr`, a reference, a value) and the compiler enforces it; the CPython C-API encodes it in a documentation table and enforces nothing. Both books' halves of the shared system meet at a `memoryview` precisely because that object makes the borrow explicit on the Python side, where the type system cannot.

---

## 81.6 Exercises

**1. Deltas, not totals.** Reproduce §81.1's first two blocks on 3.13 and 3.14 if you have both. Explain the one line that differs from Chapter 75's `LOAD_FAST_BORROW`, and rewrite an absolute-count assertion as a delta assertion.

**2. Leak on purpose, then find it.** Reproduce the staged leak. Then run the same program under `tracemalloc` and describe what it shows and what it does not: specifically, whether it can name the object's referrer.

**3. Immortality hides a bug.** Write a function that calls `Py_DecRef` once too often. Call it with `None` and with a freshly allocated object. Explain the two outcomes, and say what that implies for how you choose test fixtures for an extension.

**4. Find the keep-alive edge.** Build a ctypes pointer into a buffer, inspect `_objects`, then construct the same address by hand with `id()` and confirm nothing keeps the target alive. Describe the sequence of events that turns the second one into a crash.

**5. Price the safety.** Reproduce §81.3's second table. Then argue, with the number, when `c_void_p` over `id()` is defensible and when it is not.

**6. The design question.** CPython could return owned references uniformly from every C-API accessor, eliminating the borrowed category and the entire class of premature-free bugs. Argue why it does not: what `PyList_GetItem` returning an owned reference would cost in a tight C loop, what it would mean for existing extensions, and why PEP 703's free-threaded build makes the question live again rather than settling it.

---

## 81.7 Summary and cross-references

- Every `PyObject*` that crosses into C is either **owned** (the C code must eventually `Py_DECREF` it) or **borrowed** (it must not, and must not outlive the owner's reference). Too few decrefs **leak**; too many are a **premature free**. Both are silent, and both look identical in C, because both are `PyObject *`.
- **A `PyObject*` is an address**: `ctypes.cast(id(obj), py_object).value is obj`. There is no marshalling layer to check anything.
- **Read deltas, never absolute counts.** `sys.getrefcount(local)` returns one less on 3.14.6 than on 3.13.5, because `LOAD_FAST_BORROW` no longer takes a reference for a local; the global and list-item rows are unchanged. One `Py_IncRef` moves the count by 1 on both.
- **Immortal objects** (PEP 683, 3.12+) have a delta of **0**: `None`, `True`, small ints, interned strings. This makes the most-shared objects contention-free for free-threading, and it hides reference bugs in tests that use them.
- **The cyclic collector is not a leak detector.** A staged over-increment survives `del` and a full `gc.collect()`, because no cycle is involved and the count simply says the object is in use.
- **`ctypes` maintains a keep-alive graph in `_objects`**, so a pointer it constructs cannot outlive its buffer. That is the same lifetime problem `memoryview`'s export count solves from the owner's side.
- **Measured on 3.13.5:** a Python call is 11 ns; a `ctypes` call is 119 ns with a `py_object` argument and 150 ns with a `c_int` one. Passing a `PyObject*` is **cheaper** than passing an `int`, because a pointer needs no conversion and an `int` needs two, which is Chapter 45's conclusion again: marshalling is the cost.
- **The safety has a price and it is small:** `py_object` costs 117 ns against 83 ns for `c_void_p` over `id(obj)` (**1.42x**). The 34 ns difference is the price of not having a dangling pointer, and taking the trade for speed is never right.
- **Edges:** borrowed references expire when the container changes; a `Py_DECREF` can run arbitrary Python through a finalizer, so decref after restoring invariants; a `--with-pydebug` build finds in seconds what a release build hides for months.

**Cross-references.** Holding the GIL for object access → Chapter 80. The export count → Chapter 79. `ctypes.pythonapi` → Chapter 45. Marshalling cost → Chapter 43. Refcounting and the cyclic collector → Deep B. `tracemalloc` → Chapter 85. The stable ABI → Chapter 82. Writing the decrefs yourself → Chapter 83. Errors and callbacks → Chapter 84. Immortality and atomic refcounts → Deep L.
