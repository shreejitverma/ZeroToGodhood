# Chapter 99: Views and Copies

Two NumPy operations that *look* interchangeable, `arr[1000:9000000]` (a slice) and `arr[arr > 0]` (a boolean
mask), differ by a factor of a *million* in memory and by a subtle correctness rule. A **slice** returns a
**view**: it shares the parent array's memory, recording only an *offset* and per-axis *strides*, so it costs a
few dozen bytes regardless of how many elements it spans, **128 bytes** measured for a 5-million-element window,
and *writing to it changes the parent*. A **boolean mask** (or an index list) returns a **copy**: it cannot be
expressed with strides, so it allocates a new array holding the selected elements, **47.7 MB** for the same
selection. Knowing which you have is a *memory* decision (a view is free, a copy is the size of the selection)
*and* a *correctness* one (mutating a view is spooky action on the original; mutating a copy is not).

This chapter continues **Deep T** with views and copies: how strides make slices zero-copy, why fancy indexing
copies, and the mutation semantics that catch everyone once. It is the NumPy-specific face of the buffer/
zero-copy theme (Chapters 37, 44).

## Section index

- **99.1** Slice is a view; fancy index is a copy
- **99.2** Strides, and the mutation gotcha
- **99.3** Measurement: view vs copy memory
- **99.4** Edges and failure modes
- **99.5** Connections
- **99.6** Exercises
- **99.7** Summary and cross-references

Listings live under `code/ch099/` and are re-executed by `make verify` on both interpreters (both with NumPy
2.1.3).

---

## 99.1 Slice is a view; fancy index is a copy

```python
# code/ch099/l01_views.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- a slice is a VIEW (shares memory) ---
  arr[2:7]           : [2, 3, 4, 5, 6]
  shares arr's data  : True
  owns its data      : False  (False = a view)
--- writing to a view CHANGES the parent (spooky action) ---
  after sl[0] = 999, arr : [0, 1, 999, 3, 4, 5, 6, 7, 8, 9]  (arr[2] changed!)
--- fancy/boolean indexing is a COPY (independent) ---
  arr[arr % 2 == 0]  : [0, 2, 4, 6, 8]
  owns its data      : True  (True = a copy)
  after evens[0]=-100, arr[0] : 0  (unchanged)
--- strides make views work (even non-contiguous ones) ---
  arr[::2]           : [0, 2, 4, 6, 8]  (view, owndata=False)
  arr itemsize 8, arr[::2] stride 16 (skips one element)
  m.T is a view (transpose, no copy) : True
--- the rule ---
  slice -> view (shared memory, O(1), writes through); .copy() to detach
  fancy/boolean index -> copy (independent, O(n))
```

A basic **slice** `arr[2:7]` is a **view**: `sl.base is arr` (it shares the parent's data) and
`sl.flags.owndata` is `False` (it owns no memory of its own). Because it *shares* memory, writing `sl[0] = 999`
changes `arr[2]` to 999, the view and the parent are the *same bytes*. **Fancy indexing**, a boolean mask
`arr[arr % 2 == 0]` or an integer index list, is a **copy**: `owndata` is `True`, and mutating the result
(`evens[0] = -100`) leaves `arr` unchanged, because the copy is *independent* memory.

The bottom block shows *why* slices can be views: **strides**. `arr[::2]` (every other element) is *still a
view*, with a stride of 16 bytes (two `int64`s) instead of 8, it reads every other element of the parent's
buffer without copying. Even `m.T` (transpose) is a view: transposing just *swaps the strides*, no data moves. A
view is any selection expressible as "start here, step by these strides"; a copy is any selection that is not.

---

## 99.2 Strides, and the mutation gotcha

A NumPy array is a *buffer* plus *metadata*: a pointer to the start, a `shape`, and `strides` (bytes to step per
dimension). A **view** is a *new array object* pointing at the *same buffer* with *different* metadata, a
different offset, shape, or strides. So `arr[2:7]` points 2 elements into `arr`'s buffer with the same stride;
`arr[::2]` doubles the stride; `m.T` swaps the strides; `m.reshape(...)` (when compatible) reinterprets the same
buffer. All of these are *O(1)*, they allocate only a small array-object header (a few dozen bytes), *never* the
data. This is the same zero-copy trick as broadcasting's zero stride (Chapter 97) and `memoryview` (Chapter 37).

**Fancy indexing cannot be a view** because the selected elements are not a regular strided pattern: `arr[mask]`
picks an arbitrary subset, `arr[[0, 5, 2]]` picks elements in arbitrary order, neither is "offset + strides", so
NumPy must *copy* the chosen elements into a new contiguous buffer.

The correctness consequence is the **mutation gotcha**: because a view shares the parent's memory, *modifying a
view modifies the parent*, and *modifying the parent modifies the view*. A function that receives a slice and
"cleans it up in place" silently mutates the caller's array; a slice held across a modification of the parent
sees the change. This is *spooky action at a distance*, and it is a frequent NumPy bug. The rule: **slices are
views (shared, mutating), so use `.copy()` when you need an independent array**, and be aware that a function
receiving an array slice can mutate the original unless it copies. Conversely, fancy indexing *always* copies, so
it is *safe* to mutate but *costs* the copy, use a mask/index list when you *want* an independent selection, and a
slice when you want a cheap shared window.

---

## 99.3 Measurement: view vs copy memory

**Methodology.** `code/ch099/bench_views.py`. Selecting ~half of a 10,000,000-element `int64` array via a slice
(`arr[:N//2]`, a view) versus a boolean mask (`arr[arr < N//2]`, a copy). Peak memory via `tracemalloc`
(deterministic). CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64, NumPy 2.1.3.

| select ~5,000,000 elements | peak memory |
|---|---|
| slice (view) | **128 bytes** |
| boolean index (copy) | **47.7 MB** |

The slice allocates **128 bytes**, a small array-object header pointing into the parent's buffer, *regardless* of
selecting 5 million elements. The boolean index allocates **47.7 MB**: the mask array plus a new array holding
the ~5 million selected `int64`s. The difference is the difference between *referencing* memory and *copying* it,
a view is O(1), a copy is O(n).

The rule: **slice for cheap O(1) windows (subarrays, strided reads, transposes); fancy-index only when you need a
copy, and know it costs the selection's size.** For walking a large array in windows (a moving average, a tiled
computation, a rolling operation), *slices* keep it O(1) memory, exactly Chapter 44's `mmap` random-access
principle applied to array subranges. Reaching for a boolean mask or index list to select a contiguous range you
could *slice* wastes memory equal to the selection. And when you *do* need an independent copy (to mutate without
touching the parent, or to detach a small slice from a huge array you want freed), call `.copy()` explicitly, a
view *pins* the parent's entire buffer in memory (§99.4). As throughout Deep T, the zero-copy operation is the
efficient default; materialize only when you must.

---

## 99.4 Edges and failure modes

**Mutating a view unintentionally.** §99.2. Writing to a slice changes the parent (and vice versa). Use `.copy()`
for an independent array; document whether a function mutates its array argument.

**A small view pinning a huge parent.** A view keeps the *entire* parent buffer alive (it references it), so
slicing a 1 GB array and keeping only the small view still holds the 1 GB. To free the parent, `.copy()` the
slice you need and let the parent be collected.

**Assuming fancy indexing is a view.** `arr[mask]`, `arr[[i, j, k]]` are *copies*, so mutating them does *not*
change the parent, a bug if you expected in-place modification. Use `arr[mask] = value` (fancy *assignment*,
which does write through) to modify in place, or slice.

**`.reshape` copy vs view.** `reshape` returns a view *when the memory layout allows*, and a *copy* otherwise (a
non-contiguous array reshaped incompatibly). `arr.shape = (...)` forces a view or errors. Do not assume reshape is
free; check `owndata` if it matters.

**`np.ascontiguousarray` copies a non-contiguous view.** A strided view (`arr[::2]`, `m.T`) is non-contiguous;
passing it to code that needs contiguous memory (some C functions, `.tobytes()`) may trigger a hidden copy or
error. Force it with `np.ascontiguousarray` (a copy) deliberately.

**Checking view-ness by `.base`.** `.base` points to the *ultimate* owner, not the immediate parent, so
`view.base is parent` can be `False` even for a view (as `m.T.base is m` is). Use `flags.owndata` (False = view)
to test, or `np.shares_memory(a, b)`.

---

## 99.5 Connections

**Backward.** The zero-copy-via-metadata idea is `memoryview` (Chapter 37) and `mmap` (Chapter 44); NumPy views
are the array version. The strides/broadcasting zero-stride trick is Chapter 97. The mutation-shares-memory
gotcha is the aliasing theme of Chapters 4 and 14.

**Forward.** Contiguity (C vs Fortran order), `as_strided` (advanced stride tricks, e.g. rolling windows), and the
copy behavior of ufuncs are the rest of **Deep T**. `np.shares_memory`/`may_share_memory` for detecting aliasing
are Deep T tooling. Structured arrays and record views are the next Deep T topic.

**Across books.** View/copy awareness is how Book II moves **Book III**'s large arrays without doubling memory. A
**Book III** pipeline slices batches, windows, and channels out of large tensors as *views* (O(1), no copy),
mutating in place where intended and `.copy()`-ing where a stage must not touch upstream data, and it reaches for
fancy indexing (a copy) only when it genuinely needs an independent selection. The §99.2 mutation gotcha is
exactly the silent cross-stage corruption that view-sharing invites, which **Deep T** and **Deep U** guard
against with explicit copies at stage boundaries.

---

## 99.6 Exercises

**1. View vs copy.** Reproduce §99.1: show a slice shares memory (mutating it changes the parent) and a boolean
mask copies (mutating it does not). Check `owndata` for each. Explain the difference.

**2. Measure the memory.** Run §99.3's benchmark and confirm the view is bytes and the copy is the selection size.
Explain why strides make the view O(1).

**3. Strided views.** Show `arr[::2]` and `m.T` are views (via `owndata`), and inspect their strides. Explain how
a stride swap transposes without copying.

**4. Pin a big array.** Slice a large array, keep only the small view, and reason about why the whole parent stays
in memory. Fix it with `.copy()`. Explain the pinning.

**5. The design question.** Slices are views (shared, O(1)) and fancy indexing copies (independent, O(n)). Argue
why NumPy makes this distinction and what discipline it demands. Your answer must use the §99.3 measurement, the
mutation gotcha, and the strides mechanism.

---

## 99.7 Summary and cross-references

- A **slice** (`arr[1:9]`, `arr[::2]`, `arr.T`, often `reshape`) is a **view**: it shares the parent's memory via
  offset and **strides**, costs **O(1)** memory, and **writing to it changes the parent** (and vice versa).
- **Fancy indexing** (boolean mask `arr[mask]`, index list `arr[[i,j]]`) is a **copy**: it allocates a new array
  (**O(n)**), independent of the parent.
- **Measured:** a view of ~5,000,000 elements is **128 bytes**; the boolean-index copy is **47.7 MB**, referencing
  vs copying memory.
- **Slice for cheap O(1) windows; `.copy()` for an independent array** (and to free a huge pinned parent); fancy-
  index when you want a copy. Test view-ness with `flags.owndata`/`np.shares_memory`, not `.base`.

**Cross-references.** `memoryview`/buffer protocol → Chapter 37; `mmap` → Chapter 44; broadcasting zero-stride →
Chapter 97. Aliasing/mutation → Chapters 4, 14. Contiguity, `as_strided`, structured arrays → the rest of Deep T.
The array-stage seam → Deep U.
