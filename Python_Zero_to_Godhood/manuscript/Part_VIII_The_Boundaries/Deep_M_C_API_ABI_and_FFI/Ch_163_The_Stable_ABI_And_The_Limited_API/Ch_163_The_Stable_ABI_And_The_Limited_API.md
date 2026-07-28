# Chapter 82: The Stable ABI and the Limited API

A compiled extension is a shared library that was built against CPython's **headers**, and those headers describe struct **layouts**: how many bytes into a `PyObject` the reference count sits, how large a `PyTypeObject` is, where `ob_item` lives inside a list. CPython changes those layouts between feature releases, so a library compiled against 3.13's headers would read the wrong offsets inside 3.14. The import machinery does not attempt it: the filename carries the version, and only the matching interpreter looks for the file.

That is the default contract, and it is the reason a project shipping compiled wheels builds **one per Python version per platform**, and re-cuts the whole matrix every October.

The **limited API** (PEP 384) is the opt-out. Compiling with `Py_LIMITED_API` restricts the extension to a subset of the C-API whose layouts and signatures are frozen, and in exchange the result is a single binary, tagged `.abi3.so`, that loads into every version from the one you targeted onward. The **stable ABI** is the guarantee; the **limited API** is the subset you must stay inside to earn it.

The cost of that subset is precise and can be shown rather than asserted: **every ALL-CAPS accessor in the C-API is a macro, not a symbol**, so none of them can be in any ABI, and the limited API replaces each of them with a function call.

**This is a Deep M boundary chapter.**
It is about what a compiled extension promises, what the stable ABI freezes, and what you give up to stop rebuilding.

## Section index

- **82.1** Why a filename carries a version number
- **82.2** Symbols can be stable; macros cannot
- **82.3** Measurement: the tax, and a null result reported as one
- **82.4** Edges and failure modes
- **82.5** Connections
- **82.6** Exercises
- **82.7** Summary and cross-references

Listings live under `code/ch163/` and are re-executed by `make verify` on both verification interpreters.

---

## 82.1 Why a filename carries a version number

```python
# code/ch163/l01_stable_abi.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- the import machinery accepts three shapes of extension filename ---
  how many suffixes are searched : 3
  one is version-tagged          : True
  one is the stable-ABI tag      : True
  one is the bare extension      : True
  the version-tagged one is tried first : True
--- the version tag is this interpreter's version, spelled into the filename ---
  EXT_SUFFIX names this version : True
  SOABI names this version      : True
  the abi3 tag names NO version : True
--- build variants get their own tag, so they cannot load each other's .so ---
  this is a debug build          : False
  this is a free-threaded build  : False
  abiflags (empty on a release, GIL-enabled build) : ''
--- Py_LIMITED_API is a packed hex minimum: does this interpreter satisfy it? ---
  declares >= 3.2   (0x03020000) : satisfied here = True
  declares >= 3.10  (0x030A0000) : satisfied here = True
  declares >= 3.13  (0x030D0000) : satisfied here = True
  declares >= 3.20  (0x03140000) : satisfied here = False
--- the trade, stated as a table ---
  default C-API : full API, struct layouts visible, one wheel PER VERSION
  limited API   : frozen subset, layouts opaque, ONE wheel for 3.x and later
```

The listing deliberately reports the *structure* of the contract rather than its values. `EXT_SUFFIX` is `.cpython-313-darwin.so` on one interpreter and `.cpython-314-darwin.so` on the other; printing them would prove only that they differ, which is the premise. What is worth verifying is that the tag **names this interpreter's version**, that the `abi3` tag names **no** version, and that the version-tagged suffix is tried **first**, which is the search order that lets a project ship a fast version-specific build alongside a slower portable one and have the fast one win.

**The tag is a compatibility key, not a label.**
It encodes more than the version. A debug build (`Py_DEBUG`) and a free-threaded build (`Py_GIL_DISABLED`) each get their own marker, because each changes the object layout: a debug build adds fields to `PyObject`, and a free-threaded build changes the reference-count representation entirely. Loading the wrong one is not a slow program, it is a corrupted heap, so the naming scheme makes the mismatch an import failure instead. Both verification interpreters here report `False` for both flags and an empty `abiflags`, which is the ordinary release configuration.

**`Py_LIMITED_API` is a floor, not a version.**
It is a packed hex constant, `0x030A0000` meaning "3.10 and later". Setting it does two things at compile time: it hides everything outside the frozen subset from the headers, so using an excluded function becomes a compile error rather than a runtime crash, and it records the minimum version the resulting binary claims. The listing decodes a few and checks them against the running interpreter. Note what this check is *not*: the import machinery will load any `.abi3.so` it finds. The minimum is enforced by the **packaging** layer, through the wheel's compatibility tag, which is Deep N's subject.

**The senior-engineer contrast.**
Every language with a C-compatible extension mechanism faces this, and the answers differ. Java's JNI freezes an ABI and pays for it with a permanently awkward API. .NET pins a runtime version per assembly. C++ has no stable ABI at all between compilers, which is why every C++ library ships headers. CPython's position is the unusual one: it offers **both**, a fast unstable API and a slower frozen one, and lets each extension pick. The version-tagged filename is what makes that choice safe rather than a crash.

---

## 82.2 Symbols can be stable; macros cannot

```python
# code/ch163/l02_symbols_and_macros.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- is the name a symbol the dynamic linker can find? ---
  PyList_GetItem           function  exported: True
  PyList_GET_ITEM          macro     exported: False
  PyTuple_GetItem          function  exported: True
  PyTuple_GET_ITEM         macro     exported: False
  PyBytes_AsString         function  exported: True
  PyBytes_AS_STRING        macro     exported: False
  Py_IncRef                function  exported: True
  Py_INCREF                macro     exported: False
  PyObject_Size            function  exported: True
  Py_SIZE                  macro     exported: False
  PyLong_FromLong          function  exported: True
  PyLong_AsLong            function  exported: True
  PyObject_GetAttrString   function  exported: True
  PyUnicode_AsUTF8String   function  exported: True
  PyType_GetSlot           function  exported: True
  PyFrame_GetBack          function  exported: True
--- the split is total, not a tendency ---
  documented functions in the sample : 11
  of those, exported                 : 11
  documented macros in the sample    : 5
  of those, exported                 : 0
```

**This is the whole argument of the chapter, made checkable.**
An ABI can only contain things that exist in the shared library: exported symbols, reached through the dynamic linker at a fixed calling convention. A **macro** is not one of those. It is expanded at compile time into the caller's own code, and what it expands to, "read the field at offset 16", is precisely the struct layout the stable ABI exists to hide.

CPython's naming makes the distinction legible without documentation. Mixed case (`PyList_GetItem`) is a function; ALL CAPS (`PyList_GET_ITEM`) is a macro. The listing checks each name against the running interpreter's exported symbols by asking `ctypes.pythonapi` for it, and the split is **total**: 11 of 11 functions resolve, 0 of 5 macros do. Not a tendency, not mostly. Macros are not there to be found.

**So the limited API's cost can be stated exactly.**
Under `Py_LIMITED_API`, every ALL-CAPS accessor becomes a real call, and every struct field you used to read directly becomes an accessor function. `Py_INCREF`, which is normally an increment on a field the compiler can keep in a register, becomes `Py_IncRef`, a call through the PLT. In a loop over a million list elements that is a million calls that were previously a million indexed loads.

Whether that matters is a per-project question with a clear shape: it matters when the extension's inner loop touches Python objects per element, and it does not matter when the extension crosses once with a whole buffer and does its work in C, which is the design Chapters 44 and 79 argue for anyway. **An extension built the way this volume recommends pays almost nothing for the limited API**, because it barely touches `PyObject` fields in its hot path. An extension that walks Python containers element by element pays a great deal. The limited API is therefore cheap for the designs that were already fast and expensive for the designs that were already slow, which is a happy alignment and not a coincidence: both properties follow from how often you cross.

---

## 82.3 Measurement: the tax, and a null result reported as one

**Methodology.** `code/ch163/bench_stable_abi.py`.
`min` of 15 batches, 20,000 calls per batch.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**What cannot be measured here, stated before the table.**
The cost this chapter is really about, a macro inlining a field read against the function call that replaces it, lives entirely inside a compiled extension. This book's harness has no extension build, so that figure is cited from the design of the mechanism (§82.2) and is not measured. Saying so is more useful than substituting a proxy and letting it read as the real thing.

| one attribute read | time | vs the interpreter |
|---|---|---|
| `target.attribute` (interpreter) | 4.5 ns | 1.0x |
| `PyObject_GetAttr` (built name) | 218 ns | **48.8x** |
| `PyObject_GetAttrString` (C string) | 218 ns | 48.8x |

| one list index | time | vs the interpreter |
|---|---|---|
| `items[7]` (interpreter) | 4.9 ns | 1.0x |
| `PyList_GetItem` (borrowed ref) | 217 ns | **44.0x** |
| `PySequence_GetItem` (new ref) | 216 ns | 43.9x |

**The null result, reported as one.**
Each table contains two C-API entry points chosen to differ in exactly the way limited-API code cares about: a name passed as a C string against one passed as an already-built object, and a list-specific borrowed-reference accessor against a generic protocol accessor that returns a new reference. They come out **within a few percent of each other**, which is to say indistinguishable at this resolution. The measurement cannot separate them, and the honest conclusion is that it cannot, not that they are equal.

**The figure that does survive is the tax.**
About 4 to 5 nanoseconds inside the interpreter against about 218 through `ctypes`: roughly **45x**. That is the frame every limited-API performance argument belongs in. Choosing between two C-API entry points is worth a few nanoseconds *inside* a compiled extension, where there is no crossing to pay for. From `ctypes` it is worth nothing, because the crossing costs fifty times the difference. Chapters 43 and 45 reached this conclusion from two other directions; this is the third.

**And the practical consequence for shipping.**
The decision to use the limited API is almost never a performance decision. It is a **release-engineering** decision: one wheel instead of one per version, no re-cut every October, no gap between a Python release and your users being able to upgrade. The performance question is real only for extensions whose hot path walks Python objects, and those extensions have a bigger problem than the ABI.
**Book I**'s side of the shared system is the case where none of this bites: the matching engine is entered once per batch with a buffer, so the C-API surface it touches is small, and a limited-API build of that seam would be indistinguishable in throughput while shipping as a single wheel.

---

## 82.4 Edges and failure modes

**The abi3 tag does not enforce the minimum version; the wheel tag does.** §82.1.
`import` will load any `.abi3.so` it finds on the path. The check that an `abi3` wheel built for 3.10 is not installed into 3.9 happens in the installer, through the wheel's compatibility tag. Copying a `.so` around by hand skips that check entirely.

**Debug and free-threaded builds are different ABIs, not variants.** §82.1.
`Py_DEBUG` changes `PyObject`'s layout; `Py_GIL_DISABLED` changes the reference-count representation. Each gets its own tag so the mismatch is an import error. This is also why a free-threaded build needs its own wheels, which is one of the practical obstacles to free-threading adoption (Deep L).

**`Py_LIMITED_API` is enforced at compile time, and only for what the headers hide.**
Setting it makes an excluded function a compile error, which is the point. It cannot stop you from casting a `PyObject *` to a struct you declared yourself and reading offsets. Code that does that compiles clean, ships as `abi3`, and corrupts memory on the next release.

**Not everything is in the limited API, and some of the gaps matter.**
Static type objects declared with `PyTypeObject` are excluded; the limited API requires heap types built through `PyType_FromSpec`. For an extension with many types this is a substantial rewrite, not a compiler flag, and it is the most common reason a project looks at `abi3` and decides against it.

**A stable ABI is not a stable API.**
`abi3` promises that a *compiled* binary keeps working. It does not promise that your *source* still compiles, that deprecated functions stay, or that behaviour is unchanged. Those are separate promises with separate deprecation cycles.

**Version-tagged and abi3 builds can coexist, and the order matters.** §82.1.
The version-tagged suffix is searched first, so a project may ship both and have the optimised build win where it exists. This is a real distribution strategy and it depends on the search order, which is why the listing checks it.

**The bare `.so` suffix is a trap on the path.**
It is searched last and matches any extension, including one built for a different Python. It exists for compatibility with hand-built modules and is a good reason not to put arbitrary directories on `sys.path`.

---

## 82.5 Connections

**Backward.**
What an extension does with the references it receives, and why layout stability matters for them, is Chapter 81. Holding the GIL while touching those objects is Chapter 80. `ctypes.pythonapi`, which can only ever reach exported symbols and is therefore an accidental stable-ABI detector, is Chapter 45. The one-crossing design that makes the limited API cheap is Chapters 44 and 79.

**Forward.**
Writing a compiled extension, where these flags become a build system, is Chapter 83. Errors and callbacks crossing back is Chapter 84. Wheels, tags, and how an installer decides that an `abi3` wheel is compatible are Deep N. The free-threaded build's separate ABI, and the wheel-availability problem it creates, are Deep L. The import machinery's suffix search is Deep G.

**Across books.**
The contrast is instructive rather than flattering to either side. **Book I** has no stable ABI at all: two C++ compilers, or two versions of one compiler, may disagree on name mangling and layout, so C++ libraries ship headers and are rebuilt. CPython offers a frozen subset precisely because its extension ecosystem is distributed as binaries to users who do not have compilers. The shared order-book system sits on the good side of both: its seam is narrow, its data crosses as a buffer, and narrow seams are what make either ABI question tractable.

---

## 82.6 Exercises

**1. Read your own tags.** Print `EXT_SUFFIX`, `SOABI`, and `sys.abiflags` on every Python you have. Explain what each component encodes and predict which pairs of interpreters could share an extension binary.

**2. Find the macros.** Extend Listing 163.2 with ten more C-API names you use or have read about. Predict which are exported before checking. Explain any that surprise you.

**3. The wheel does the enforcing.** Find an installed `.abi3.so` on your system (or build one). Confirm that `import` loads it without consulting any minimum version, and describe where the minimum is actually checked.

**4. Price your own boundary.** Reproduce §82.3 and compute the crossing tax on your machine. Then argue, using that number, whether the difference between two C-API entry points could ever be visible through `ctypes`.

**5. The heap-type gap.** Read what `PyType_FromSpec` requires against a static `PyTypeObject` declaration. Describe, for an extension with five types, what adopting the limited API would actually cost in work.

**6. The design question.** CPython could freeze all struct layouts and make the entire C-API stable, eliminating version-tagged wheels. Argue why it does not: what `PyObject`'s layout has changed to enable since 3.11 (specialization caches, immortality, free-threading), what those changes bought, and whether the wheel matrix is a fair price for them.

---

## 82.7 Summary and cross-references

- A compiled extension is built against CPython's **headers**, which describe **struct layouts** that change between feature releases. The filename therefore carries a version tag (`.cpython-313-darwin.so`), and only the matching interpreter looks for it. That is why binary wheels are cut per version per platform.
- **The limited API (PEP 384) is the opt-out**: compile with `Py_LIMITED_API` and stay inside a frozen subset, and the result is a single `.abi3.so` that loads into that version and later. The **stable ABI** is the guarantee; the **limited API** is the subset.
- **The import machinery searches three suffixes**, version-tagged first, then `abi3`, then bare `.so`, so a project can ship both and have the optimised build win.
- **Build variants are separate ABIs.** `Py_DEBUG` and `Py_GIL_DISABLED` change object layout and get their own tags, which is why free-threading needs its own wheels.
- **Macros cannot be in an ABI, and this is checkable:** of a sampled 16 C-API names, **11 of 11 functions are exported symbols and 0 of 5 macros are**. A macro expands into the caller's code as a field read at a fixed offset, which is exactly the layout the stable ABI hides. So the limited API's real cost is that every ALL-CAPS accessor becomes a call.
- **That cost lands on the designs that were already slow.** An extension that crosses once with a whole buffer barely touches `PyObject` fields and pays almost nothing; one that walks Python containers per element pays a lot.
- **Measured on 3.13.5:** an attribute read is 4.5 ns in the interpreter and 218 ns through `ctypes` (**48.8x**); a list index is 4.9 ns against 217 ns (**44x**). The two C-API entry points in each table came out within a few percent of each other, a **null result reported as one**: this measurement cannot separate them. The macro-versus-function cost is inside a compiled extension and is cited, not measured.
- **The decision is release engineering, not performance:** one wheel instead of one per version, and no gap between a Python release and your users upgrading.
- **Edges:** the minimum version is enforced by the wheel tag, not by `import`; `Py_LIMITED_API` cannot stop you casting to a struct you declared yourself; static `PyTypeObject` declarations are excluded, so heap types via `PyType_FromSpec` are required; a stable ABI is not a stable API.

**Cross-references.** References across the boundary → Chapter 81. Holding the GIL → Chapter 80. `ctypes.pythonapi` → Chapter 45. One-crossing design → Chapters 44 and 79. Writing an extension → Chapter 83. Errors and callbacks → Chapter 84. Wheels and tags → Deep N. The free-threaded ABI → Deep L. Suffix search → Deep G.
