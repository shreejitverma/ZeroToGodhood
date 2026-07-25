# Chapter 103: Memory-Mapped Arrays

Every array so far has lived in RAM.
`np.load`, `np.fromfile`, `np.array([...])`, all of them read the data into memory before you can touch it, so the largest array you can hold is bounded by how much RAM you have.
But the reflex "load the file, then work on it" breaks the moment the file is bigger than memory: a 50 GB array on a 16 GB machine simply will not load.
`np.memmap` removes that bound.
It *maps* an array file into your address space (the `mmap` of Chapter 44, wearing an ndarray's clothes) instead of loading it, so **opening** a 191 MB array file peaks at a few hundred **bytes**, not 191 MB, over **300,000x** less, and you index, slice, and compute on it as a normal array while the OS pages in only the regions you actually touch.
This is how you process arrays *larger than RAM*.

This chapter continues **Deep T** with `np.memmap`: an array whose storage is a file, opened in O(1) memory, with only the accessed pages resident.
It closes the loop from Chapter 44 (`mmap` on raw bytes) to Chapters 96-102 (arrays), an array on disk you compute on a slice at a time.

## Section index

- **103.1** An array whose storage is a file
- **103.2** Why opening is nearly free, and when to load instead
- **103.3** Measurement: open cost, memmap vs full load
- **103.4** Edges and failure modes
- **103.5** Connections
- **103.6** Exercises
- **103.7** Summary and cross-references

Listings live under `code/ch103/` and are re-executed by `make verify` on both interpreters (both with NumPy 2.1.3).

---

## 103.1 An array whose storage is a file

```python
# code/ch103/l01_memmap.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- create an array file on disk (mode='w+') and fill it ---
--- open it read-only: no load, it IS the file's bytes ---
  is an ndarray        : True
  m[0], m[-1]          : 0, 999   (read from disk on access)
  m[100:105]           : [100, 101, 102, 103, 104]
  m[:10].sum()         : 45   (only these pages paged in)
--- compute on a slice (only the touched region loads) ---
  m[500:600].mean()    : 549.5
--- open writable (mode='r+') and update in place; changes hit the file ---
  after w[0]=999, reopened m[0] : 999   (persisted to disk)
--- the rule ---
  np.memmap: work with an array on disk, larger than RAM, paged in on
  demand; only touched pages are resident. np.load/fromfile loads it all.
```

`np.memmap(path, dtype, mode, shape)` returns an object that **is an `ndarray`** (`isinstance(m, np.ndarray)` is `True`), so every array operation from Deep T works on it: indexing (`m[0]`, `m[-1]`), slicing (`m[100:105]`), reductions (`m[:10].sum()`, `m[500:600].mean()`), masking, broadcasting, all of it.
The difference is *where the bytes live*.
An ordinary array owns a block of RAM; a memmap's bytes **are the file**.
Reading `m[0]` reads that offset from the file (via the page cache); writing to a writable memmap writes back to the file.

The `mode` argument mirrors file modes:

- **`'w+'`** creates (or truncates) the file to `shape` and opens it read/write, the "make a new on-disk array" mode.
  The listing fills it with `arange(1000)`, `flush()`es to force the bytes to disk, and `del`s to close the mapping.
- **`'r'`** opens an existing file read-only.
  This is the "I have a big array file, let me work with it" mode: no load, just a mapping.
- **`'r+'`** opens read/write, so updates (`w[0] = 999`) persist, reopening the file confirms the write reached disk.

The `flush()` calls matter: like any buffered write, changes are not guaranteed on disk until flushed (Chapter 44).
And nothing here loaded the whole array, each access touched only its own bytes.

---

## 103.2 Why opening is nearly free, and when to load instead

Opening a memmap costs almost nothing because it does almost nothing: it calls `mmap` to map the file's bytes into the process address space and wraps that mapping in an ndarray header (shape, dtype, strides).
No bytes are read.
The array's contents are *the pages of the file*, and the OS pages them in lazily, the first time you touch a region, that page faults in from disk; regions you never touch never load.
So a 191 MB file, or a 191 GB file, opens in the same few hundred bytes (the ndarray object plus the mapping bookkeeping); the benchmark below measures it.
This is exactly the Chapter 44 `mmap` mechanism, now presenting typed array elements instead of raw bytes.

That is the whole point: you can open an array **larger than RAM** and compute on it a slice at a time.
Process a 100 GB dataset in 1 GB windows (`for i in range(0, n, step): work(m[i:i+step])`) and only the current window's pages are resident; earlier pages are evicted under memory pressure.
The array file becomes the source of truth, and RAM is just a cache of the parts you are using.

When should you *not* use memmap, and load fully instead?
When the array fits in RAM **and you touch most of it repeatedly**.
A memmap pays a page fault (a disk read) the first time each page is accessed, and if the OS evicts pages under pressure, re-access faults again.
A full load pays one big sequential read up front, then every access is a fast RAM hit.
So for a "fits in memory, used heavily, many passes" workload, load it (`np.load`/`np.fromfile`); for a "too big, or touched partially, or used once" workload, memmap it.
The rule: **memmap decouples array size from RAM, at the cost of paging; load when the array fits and you reuse it.**

---

## 103.3 Measurement: open cost, memmap vs full load

**Methodology.** `code/ch103/bench_memmap.py`.
A 191 MB array file (25,000,000 `float64`), opened two ways: `np.memmap(path, mode='r')` (touch one element) versus `np.fromfile(path)` (read the whole file).
Peak memory of each open via `tracemalloc`.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64, NumPy 2.1.3.

| Open a 191 MB array file | peak memory | vs memmap |
|---|---|---|
| `np.memmap(path, mode='r')` | **~630 bytes** | 1x |
| `np.fromfile(path)` (full load) | **191 MB** | **~300,000x more** |

The memmap opens at a few hundred bytes (the exact count wobbles by a handful of bytes run to run, tracemalloc's own bookkeeping); the full load allocates the entire 191 MB.
That is over **300,000x** less memory to *open* the same data, and the ratio grows without bound as the file grows: a 100 GB file's memmap still opens in a few hundred bytes, while `np.fromfile` would need 100 GB of RAM (or fail).

The measured fact is not "memmap is faster", it is "memmap's open cost is independent of file size".
It trades the one-time full-load allocation for on-demand paging: you pay memory (and a disk read) only for the pages you touch, when you touch them.
For a partial or streaming access pattern over a huge file, that is the difference between "runs on a laptop" and "does not fit".
As throughout Deep T, the right tool is chosen by the access pattern: whole-array-in-RAM-reused favors a load; larger-than-RAM-or-partial favors a memmap.

---

## 103.4 Edges and failure modes

**`flush()` before you rely on writes.**
Writes to a writable memmap go through the OS page cache and are not guaranteed on disk until `m.flush()` (or the mapping is closed and synced).
A crash before flush can lose the writes.
Flush at meaningful checkpoints, exactly as with `mmap` (Chapter 44).

**`shape`/`dtype`/`offset` must match the file's actual layout.**
A memmap is *raw bytes* with a shape and dtype laid over them, there is no header describing the data (unlike `.npy`).
Open a `float64` file as `float32`, or with the wrong `shape`, and you get garbage or a size error, silently misinterpreted numbers, not an exception.
You must know (or store separately) the dtype and shape.
`np.load(path, mmap_mode='r')` memmaps a `.npy` file *and* reads its header, so it gets dtype/shape right, prefer it when the file is a `.npy`.

**It is still bounded by address space and disk, not RAM.**
Memmap removes the *RAM* bound, but the mapping must fit in the process's virtual address space (huge on 64-bit, a non-issue) and the file must fit on disk.
And touching the *whole* array still reads the whole file, memmap helps *partial* or *streaming* access, not "load everything anyway".

**Random access thrashes; sequential access streams.**
Paging is efficient for sequential or localized access (adjacent elements share a page).
Scattered random access across a huge memmap faults a new page per access and can thrash (constant eviction and reload).
Access memmapped data in contiguous chunks where you can.

**A memmap is not a copy.**
Two memmaps of the same file (or a memmap and another process) see the *same bytes*; a write through one is visible to the other.
This is shared, file-backed memory, useful for inter-process sharing (Chapter 48's `shared_memory` is the anonymous cousin), but a source of aliasing bugs if you expected independence.

**Slicing a memmap returns a memmap (a view).**
`m[100:200]` is a *view* into the mapping (Chapter 99), not a loaded copy; it still pages in on access.
To get an in-RAM copy of a region, `np.array(m[100:200])` or `m[100:200].copy()` forces the read.

---

## 103.5 Connections

**Backward.**
Memmap *is* Chapter 44's `mmap` presenting typed array elements, same lazy paging, same `flush` discipline, same file-backed sharing.
That it returns an `ndarray` means all of Chapters 96-102 (vectorization, broadcasting, dtypes, views, reductions, masking) apply unchanged.
Slicing returning a view is Chapter 99.
The "bytes reinterpreted as a dtype" hazard is Chapter 98 (dtypes) and Chapter 45 (`struct`/binary layout).

**Forward.**
`np.load(mmap_mode=...)` for `.npy`/`.npz`, structured-dtype memmaps for on-disk record arrays, and out-of-core computation (Dask, Zarr, HDF5 via h5py) that generalize "array bigger than RAM, computed in chunks" are Deep T and Deep U topics.
`shared_memory` for cross-process arrays (Chapter 48) is the anonymous, RAM-backed sibling.

**Across books.**
Larger-than-RAM arrays are how **Book III** touches datasets that do not fit in memory, memory-mapped weight files, tokenized corpora streamed a shard at a time, feature matrices computed in windows.
A **Book III** training or inference pipeline memmaps a multi-gigabyte tensor file and pages in the batch it needs, so a model or dataset far larger than RAM still runs.
The Chapter 44 seam (mapping a file instead of reading it) becomes, at the array level, the mechanism that decouples data size from machine size, which **Deep U** builds on for data pipelines that scale past a single machine's memory.

---

## 103.6 Exercises

**1. Make and reopen an on-disk array.**
Reproduce §103.1: create a `w+` memmap, fill it, `flush`, `del`; reopen `'r'` and index/slice/reduce; reopen `'r+'`, write an element, and confirm the change persists on reopen.
Explain each `mode`.

**2. Measure the open cost.**
Run §103.3's benchmark.
Confirm the memmap opens in a few hundred bytes while `np.fromfile` allocates the whole file.
Then double `N` and confirm the memmap's open cost does *not* change while the load's does.
Explain why.

**3. Larger than a slice.**
Memmap a large file and compute a reduction (say the mean) over it in fixed-size windows (`m[i:i+step]`) without ever holding the whole array in RAM.
Compare the result to loading it fully.
Explain what was resident at peak.

**4. The dtype trap.**
Write a `float64` memmap, then reopen the *same file* as `float32` with a matching byte-`shape`.
Observe the garbage values.
Explain why memmap cannot detect the mismatch, and how `np.load(mmap_mode=...)` avoids it for `.npy`.

**5. The design question.**
`np.memmap` opens in memory independent of file size (§103.3).
Argue when to memmap versus load fully, using the paging-vs-one-big-read trade-off (§103.2), and connect it to Chapter 44's `mmap`.

---

## 103.7 Summary and cross-references

- **`np.memmap` is an `ndarray` whose storage is a file.**
  It maps the file (Chapter 44's `mmap`) instead of loading it, so all Deep T operations work on it while the OS pages in only the regions you touch.
- **Opening is O(1) in memory.**
  Measured: opening a 191 MB array file peaks at ~630 bytes via memmap versus 191 MB via `np.fromfile`, over **300,000x** less, and the ratio grows without bound with file size.
- **This is how you handle arrays larger than RAM**, computing on them a slice at a time.
  Use a full load instead when the array fits in memory and you reuse it (paging costs a fault per page).
- **`mode`**: `'w+'` create, `'r'` read-only, `'r+'` read/write; **`flush()`** before relying on writes; **`shape`/`dtype` must match the file's raw layout** (or use `np.load(mmap_mode=...)` for `.npy`).
- **Edges:** slicing returns a view/memmap (not a load); random access thrashes while sequential streams; two memmaps of one file share bytes; it is bounded by disk and address space, not RAM.

**Cross-references.** `mmap` and file-backed memory → Chapter 44; the ndarray operations that apply → Chapters 96-102; views vs copies → Chapter 99; dtype/byte-layout hazards → Chapters 98, 45; cross-process arrays → Chapter 48. Out-of-core arrays (`.npy` mmap, Zarr/HDF5/Dask) → the rest of Deep T and Deep U.
