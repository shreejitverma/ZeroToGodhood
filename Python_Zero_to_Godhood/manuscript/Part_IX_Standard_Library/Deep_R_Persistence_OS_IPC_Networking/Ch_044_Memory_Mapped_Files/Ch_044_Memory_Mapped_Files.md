# Chapter 44: Memory-Mapped Files

A search tool needs to read one byte at each of fifty thousand scattered offsets in a 64 MB index file.
Written with `seek` and `read`, it makes fifty thousand `read()` syscalls, one user/kernel crossing per
byte, and takes ~76 ms. Mapped with `mmap`, the same fifty thousand accesses become plain memory reads,
the file is paged in on demand and served from the OS page cache, and the work drops to ~13 ms, **several
times faster** (measured ~6x under load, ~9x on a quiet machine). The bytes are identical; what changed is
that random access no longer pays a syscall per access. That is what `mmap` buys: a file that behaves like
memory.

This chapter continues **Deep R** with memory-mapped files, the mechanism that maps a file into the process
address space so it can be indexed, sliced, searched, and written *as memory*, with the operating system
handling the transfers. It ties together Chapter 37's buffer protocol (an `mmap` is a buffer) and Chapter
40's syscall model (an `mmap` access avoids the `read()` syscall), and it is the bridge to the shared-memory
IPC later in Deep R.

## Section index

- **44.1** A file as memory
- **44.2** Why random access is cheaper than `seek`+`read`
- **44.3** Measurement: scattered reads
- **44.4** Edges and failure modes
- **44.5** Connections
- **44.6** Exercises
- **44.7** Summary and cross-references

Listings live under `code/ch044/` and are re-executed by `make verify` on both interpreters.

---

## 44.1 A file as memory

```python
# code/ch044/l01_mmap.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- map the file read-only; it behaves like bytes ---
  length              : 47
  mm[0:3]  (slice)    : b'GET'
  mm[4]    (index)    : 47 ('/')
  find(b'Host:')      : offset 26
  slice at match      : b'Host: example.com\r'
--- map read-write; assigning to a slice writes through to the file ---
  file after write     : b'PUT' (was b'GET')
```

`mmap.mmap(fileno, 0, access=...)` maps the file into the process's address space and returns an object
that *is* the file's bytes. You index it (`mm[4]` is an `int`), slice it (`mm[0:3]` is `b'GET'`), take its
length, and search it (`mm.find(b"Host:")` returns an offset), all as memory operations. There is no
`read()` per access; touching a byte reads it from the mapping, which the OS has paged in (or will fault in
on first touch). Because an `mmap` exposes the buffer protocol (Chapter 37), you can also wrap it in a
`memoryview`, hand it to `struct`, or pass it to code expecting a bytes-like object, all zero-copy.

On a *writable* map (the default `access`, or `ACCESS_WRITE`), assigning to a slice **writes through to the
file**: `mm[0:3] = b"PUT"` changes the file's first three bytes (after `flush`, or when the map is closed and
the OS writes the dirty pages back). This is in-place file editing without reading the whole file into
memory and writing it back, the OS moves only the pages you touched.

---

## 44.2 Why random access is cheaper than `seek`+`read`

The `seek`+`read` pattern makes a syscall per access: `f.seek(off)` positions the descriptor and
`f.read(1)` crosses into the kernel to copy one byte out. For scattered access that defeats the file
object's read-ahead buffer (each seek to a distant offset discards it), so it is genuinely one `read()`
syscall per byte, and a syscall is hundreds of nanoseconds of pure overhead before any data moves.

`mmap` removes the per-access syscall entirely. The mapping is set up once; thereafter each access is a
memory load. The first touch of a given 4 KB page triggers a *page fault* that the OS services by reading
that page from the file into the page cache, but every subsequent access to that page (and to nearby bytes
on it) is a plain memory read with no kernel crossing. For access patterns with any locality, or any reuse,
the amortized cost per access is far below a syscall. This is the same "batch the boundary crossing" theme
as Chapter 40, achieved structurally: instead of you batching reads, the OS's paging does it, at page
granularity, transparently.

The corollary bounds the win: for purely *sequential* streaming, the file object's read-ahead buffer
already amortizes the syscalls (one `read()` fills 8 KB), so `mmap` offers little there. `mmap` wins on
*random* access and on *sharing* (below), not on sequential reads.

---

## 44.3 Measurement: scattered reads

**Methodology.** `code/ch044/bench_random_access.py`. 50,000 one-byte reads at random offsets in a 64 MB
file, via `mmap` indexing versus `seek`+`read`. `min` per run. This is I/O- and page-cache-bound and
therefore noisy (the harness flags runs machine-busy), so the ratio, not the absolute time, is the finding.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| 50,000 random 1-byte reads | min per run | per access | ratio |
|---|---|---|---|
| `mmap` (memory read) | **~13 ms** | **~260 ns** | 1.00x |
| `seek`+`read` (syscall each) | **~76 ms** | **~1520 ns** | **~6x** (up to ~9x quiet) |

`mmap` serves each access in ~260 ns amortized (a memory read plus the occasional page fault); `seek`+`read`
spends ~1520 ns, dominated by the `read()` syscall per access. The **~6x** (and up to ~9x on a quiet
machine) is the cost of the per-access kernel crossing that `mmap` eliminates. As with the other I/O
benchmarks, the exact multiple moves with machine load and cache state; the order of magnitude, several-
fold, is the durable finding.

The rule: **use `mmap` for random access to large files, and for sharing a file between processes; use plain
buffered reads for sequential streaming.** A search index, a database file, a large binary format read at
scattered offsets, all favor `mmap`. A log you read top to bottom does not. And because a writable `mmap`
can be shared between processes (below), it is also the foundation for zero-copy inter-process shared memory,
the Deep R material this chapter sets up.

---

## 44.4 Edges and failure modes

**`mmap` on sequential streaming.** §44.3. No real gain over a buffered read for top-to-bottom access, and
more complexity. Use `mmap` for random access, not sequential.

**Length changes invalidate the mapping.** An `mmap` is a fixed-size window over the file at map time. If
another process truncates or shrinks the file, accessing beyond the new end can raise `SIGBUS` (a crash, not
a Python exception). Do not `mmap` a file whose size another party may shrink underneath you.

**Empty files.** `mmap(fileno, 0, ...)` maps the whole file, but you cannot map a *zero-length* file
(`ValueError`). Guard for empty files before mapping.

**Dirty pages need `flush` for durability.** §44.1. Writes through a map hit the page cache; like Chapter
40's `flush`/`fsync` distinction, the data is durable only after `mm.flush()` (and the OS writing pages
back). Do not assume a write-through is on disk immediately.

**The mapping pins the file.** While an `mmap` is open it holds the underlying resource; close the `mmap`
(or use it in a `with` block) before operations that need the file unmapped. On Windows especially, an open
mapping can block deletion or resizing.

**Address space, not RAM, is the limit.** Mapping a 100 GB file does not use 100 GB of RAM, only the pages
you touch are resident, but it does consume 100 GB of *virtual address space*, which is effectively
unlimited on 64-bit and exhausted quickly on 32-bit. `mmap` is a 64-bit-friendly technique.

---

## 44.5 Connections

**Backward.** The buffer protocol an `mmap` exposes (so it works with `memoryview`, `struct`, and bytes-like
APIs zero-copy) is Chapter 37. The `read()` syscall and `flush`/`fsync` durability model `mmap` avoids and
inherits are Chapter 40. The `bytes`-like indexing and slicing semantics are Chapter 37's binary types.

**Forward.** Shared-memory IPC (`multiprocessing.shared_memory`, and `mmap` with `MAP_SHARED`) that lets
processes share a buffer without copying is the IPC material later in **Deep R**. The page cache and virtual
memory system `mmap` rides on are an OS-internals topic in **Deep R**. NumPy's `memmap`, arrays backed by a
memory-mapped file, is **Deep T**.

**Across books.** `mmap` is how Book II gives **Book III** random access to large on-disk structures without
loading them. A **Book III** retrieval system memory-maps a large vector index or a document store and
accesses records at scattered offsets at memory speed, and (with a shared mapping) lets worker processes
share one copy of the index instead of each loading its own. The §44.3 random-access property and the
shared-memory property are what make a multi-gigabyte index usable across a process pool in bounded RAM.
**Deep U** owns the large-file seam.

---

## 44.6 Exercises

**1. Reproduce the random-access win.** Run §44.3's benchmark and confirm `mmap` is several times faster
than `seek`+`read` for scattered access. Then change the access pattern to sequential and show the gap
narrows. Explain why locality and read-ahead change the picture.

**2. Edit in place.** Map a file read-write, change some bytes through the mapping, `flush`, and confirm the
file changed on disk without ever reading the whole file into Python. Explain what the OS moved and when.

**3. Search a large file.** Use `mm.find` to locate a pattern in a mapped file and slice out the surrounding
bytes, without reading the file into a `bytes`. Explain why this is memory-efficient for a large file.

**4. Break it safely.** Map a file, then (in another handle) truncate it, and reason about why accessing the
mapped region beyond the new end is dangerous (`SIGBUS`). Explain why `mmap` requires a stable file size.

**5. The design question.** `mmap` trades a fixed-size, size-stable, pin-the-file mapping for syscall-free
random access and shareability. Argue when that trade is worth it. Your answer must use the §44.3 numbers,
address why sequential reads do not benefit, and explain how the shared-memory property makes `mmap` the
basis for zero-copy IPC.

---

## 44.7 Summary and cross-references

- **`mmap`** maps a file into the address space so it behaves like `bytes`: index, slice, `find`, and (on a
  writable map) assign to write through to the file. It exposes the buffer protocol (Chapter 37).
- **Random access is cheaper** because there is no `read()` syscall per access: the OS pages data in on
  first touch and serves the rest from the page cache.
- **Measured:** 50,000 random 1-byte reads in a 64 MB file are **~6x faster** with `mmap` than `seek`+`read`
  (~260 ns vs ~1520 ns per access), up to ~9x on a quiet machine. The order of magnitude is the finding.
- **Use `mmap`** for random access to large files and for sharing between processes; **use buffered reads**
  for sequential streaming. Mind size stability (`SIGBUS`), empty files, `flush` durability, and virtual
  address space.

**Cross-references.** Buffer protocol → Chapter 37. `read()` syscalls and `flush`/`fsync` → Chapter 40.
Binary types → Chapter 37. Shared-memory IPC → the rest of Deep R. NumPy `memmap` → Deep T. The large-file
seam → Deep U.
