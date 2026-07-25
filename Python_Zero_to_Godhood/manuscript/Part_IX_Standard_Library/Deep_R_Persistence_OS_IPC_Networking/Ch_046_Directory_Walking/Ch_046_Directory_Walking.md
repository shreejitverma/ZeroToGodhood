# Chapter 46: Directory Walking

A backup tool walks a directory of 5,200 entries, classifying each as a file or a subdirectory, and it is
slow out of proportion to the work. The loop is `for name in os.listdir(d): if os.path.isdir(...)`, and the
problem is `isdir`: it does a `stat()` syscall for *every* entry, 5,200 kernel crossings just to learn what
the directory listing could have told it. Rewritten with `os.scandir`, whose entries carry their type
cached from the single directory read, the same classification runs **7x faster** (403 ns/entry versus 2,677
ns/entry), because the type check is now a memory read, not a syscall. The directory read already knew which
entries were directories; `listdir` threw that information away and `isdir` bought it back one expensive
syscall at a time.

That is the directory-walking lesson, and it is why `os.scandir` (and `os.walk`, which is built on it)
exists. This chapter continues **Deep R** with efficient directory traversal: the `DirEntry` cache that makes
type checks free, and the discipline of stat-only-what-you-need. It is the same "avoid the per-item syscall"
theme as Chapter 40 (buffering) and Chapter 44 (`mmap`), applied to filesystem metadata.

## Section index

- **46.1** `scandir` and the cached `DirEntry`
- **46.2** Why `listdir` + `stat` is slower
- **46.3** Measurement: classifying entries by type
- **46.4** Edges and failure modes
- **46.5** Connections
- **46.6** Exercises
- **46.7** Summary and cross-references

Listings live under `code/ch046/` and are re-executed by `make verify` on both interpreters.

---

## 46.1 `scandir` and the cached `DirEntry`

```python
# code/ch046/l01_scandir.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- scandir: each entry knows its name, type, and (cached) stat ---
    file  a.txt    size=1
    file  b.log    size=2
    dir   sub      size=0
--- os.walk: built on scandir, yields (dirpath, dirnames, filenames) ---
    .      dirs=['sub'] files=['a.txt', 'b.log']
    sub    dirs=[] files=['c.txt']
--- the type is available without a separate stat() ---
    files only (is_file, cached): ['a.txt', 'b.log']
```

`os.scandir(path)` returns an iterator of `DirEntry` objects, and each entry carries information the OS
provided *during the directory read*: its `name`, and, on most systems, its type (file/directory/symlink).
So `entry.is_dir()` and `entry.is_file()` usually answer from that cached type with no additional syscall,
and `entry.stat()` caches its result too (one `stat` per entry at most, reused on repeat access). Use
`scandir` as a context manager (`with os.scandir(d) as it:`) so the underlying directory handle is closed
promptly.

`os.walk` is built on `scandir` and yields `(dirpath, dirnames, filenames)` for each directory in a tree,
already separated into subdirectories and files, inheriting the cached-type benefit. For a recursive walk it
is the standard tool. The bottom block makes the key point explicit: filtering entries by type
(`e.is_file()`) reads the cached type and does not stat each entry, which §46.3 measures.

---

## 46.2 Why `listdir` + `stat` is slower

`os.listdir` returns only *names*. The underlying directory read on modern filesystems provides more, on
Linux the `readdir` result includes a `d_type` field with the entry's type, but `listdir` discards it. So to
recover the type, code calls `os.path.isdir(os.path.join(d, name))`, which does a full `stat()` syscall:
join the path, cross into the kernel, fetch the inode metadata, all to answer one bit (is it a directory?).
Over N entries that is N `stat` syscalls, and a syscall is hundreds of nanoseconds to microseconds of pure
overhead.

`os.scandir` keeps what the directory read already provided. The type comes back with the listing, so a
type check is a field access on the `DirEntry`, a memory read. The saving is exactly the N `stat` syscalls,
which is why the gap widens with the number of entries and with how syscall-expensive the platform is. (The
size of the win varies by OS and filesystem: where the directory read supplies `d_type`, `is_dir`/`is_file`
are free; where it does not, `scandir` still saves by caching the one `stat` it must do. The type-check
pattern this chapter measures is where the benefit is largest.)

This is the same structural move as the rest of Deep R: the expensive thing is the kernel crossing, and the
fast path avoids doing it per item by using information already batched into one operation.

---

## 46.3 Measurement: classifying entries by type

**Methodology.** `code/ch046/bench_scandir.py`. Walking a directory of 5,200 entries (5,000 files, 200
subdirectories) and counting files versus directories, with `os.scandir` (cached type) versus `os.listdir` +
`os.path.isdir` (a `stat` per entry). `min` per run. Directory I/O is OS-bound and noisy (the harness flags
runs machine-busy), so the ratio is the finding. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| classify 5,200 entries | min per run | per entry | ratio |
|---|---|---|---|
| `os.scandir` (cached type) | **~2.1 ms** | **~403 ns** | 1.00x |
| `os.listdir` + `os.path.isdir` | **~15 ms** | **~2677 ns** | **~7x** |

`scandir` classifies each entry in ~403 ns (a `DirEntry` field access); `listdir` + `isdir` spends ~2677 ns,
dominated by the per-entry `stat` syscall. The **~7x** is those saved syscalls. As with the other I/O
benchmarks the exact figure moves with the machine and filesystem, but the direction is structural: one
directory read plus cached types beats one directory read plus N stats.

The rule: **use `os.scandir` (or `os.walk`) for directory traversal, and call `entry.stat()` only for the
entries whose full metadata you actually need.** A tool that walks a tree to find files matching a pattern,
or to separate files from directories, should never `listdir` + `isdir`; it should `scandir` and read the
cached type. Reserve `stat` for when you genuinely need size, mtime, or permissions, and then call it once
per relevant entry, letting the `DirEntry` cache it.

---

## 46.4 Edges and failure modes

**`listdir` + `isdir`/`isfile` in a walk.** §46.1. A `stat` per entry. Use `scandir`'s cached type instead.
This is the chapter-opening slowdown.

**`entry.is_dir()` follows symlinks by default.** `is_dir()` reports whether the *target* is a directory,
following symlinks; pass `follow_symlinks=False` to test the link itself. For a walk that must not traverse
symlinks (to avoid cycles), check `entry.is_symlink()` and control descent explicitly.

**`os.walk` and symlink loops.** `os.walk` does *not* follow directory symlinks by default (`followlinks=False`),
which prevents infinite loops; enabling `followlinks=True` can loop forever on a cyclic symlink. Leave it off
unless you need it and can guarantee no cycles.

**Stale `DirEntry` cache.** A `DirEntry`'s cached type and stat reflect the moment of the directory read. If
the filesystem changes during a long walk, the cached values can be stale. For a consistent snapshot of a
volatile directory, re-stat the specific entries you act on.

**Mutating `dirnames` during `os.walk`.** You *can* prune the walk by modifying the `dirnames` list in place
(e.g. `dirnames[:] = [x for x in dirnames if x != '.git']`), and this is the intended way to skip subtrees.
Replacing the list with a new object (`dirnames = [...]`) does *not* prune, it must be an in-place edit.

**Not closing the iterator.** `os.scandir` holds an open directory handle. Use it in a `with` block (or
exhaust and close it) so the handle is released promptly, especially in long-running processes that walk many
directories.

---

## 46.5 Connections

**Backward.** The per-item-syscall-avoidance theme is Chapter 40 (buffering batches `write` syscalls) and
Chapter 44 (`mmap` avoids per-access `read`). The `pathlib` paths a walk produces, and its `rglob` built on
this machinery, are Chapter 43. The `stat` metadata (`st_size`, `st_mtime`) is the filesystem side of the OS
interface.

**Forward.** Higher-level tree operations (`shutil.copytree`, `rmtree`) and the file-metadata/permissions
model are further **Deep R** material. Watching a directory for changes (inotify/FSEvents) is an OS-specific
topic flagged in **Deep R**. The `glob` pattern matching over these entries connects to text processing.

**Across books.** Efficient directory walking is how Book II ingests a corpus into **Book III** without the
walk itself becoming the bottleneck. A **Book III** pipeline scanning millions of files to build an index
uses `os.scandir`/`os.walk` and reads cached types, so the scan is bounded by one directory read per
directory plus the stats it truly needs, not by a stat per file. The §46.3 saving is what keeps corpus
enumeration cheap at scale. **Deep U** owns the ingest seam.

---

## 46.6 Exercises

**1. Reproduce the walk gap.** Run §46.3's benchmark and confirm `scandir` is several times faster than
`listdir` + `isdir` for a type-classification walk. Explain, in terms of syscalls, where the time goes and
why the gap grows with the entry count.

**2. Stat only what you need.** Walk a directory, filter to files by cached type (no stat), then stat only the
files larger than some threshold. Show that you stat far fewer entries than a naive walk would. Explain the
`DirEntry` stat cache.

**3. Handle symlinks.** Create a symlink to a directory and show how `is_dir()` and `is_dir(follow_symlinks=
False)` differ. Explain why a recursive walk must control symlink following to avoid cycles.

**4. Prune a walk.** Use `os.walk` and prune a subdirectory (e.g. `.git`) by editing `dirnames` in place.
Show that an in-place edit prunes but reassigning the variable does not. Explain why.

**5. The design question.** `os.scandir` returns rich `DirEntry` objects while `os.listdir` returns bare
names. Argue why both exist. Your answer must use the §46.3 measurement, explain what information the
directory read provides that `listdir` discards, and identify when the simplicity of `listdir` (just names)
is still the right choice.

---

## 46.7 Summary and cross-references

- **`os.scandir`** yields `DirEntry` objects carrying the entry's type (and cached `stat`) from the single
  directory read, so `is_dir()`/`is_file()` usually cost no extra syscall. **`os.walk`** is built on it.
- **`os.listdir` returns names only,** so recovering the type needs `os.path.isdir`, a `stat` syscall per
  entry.
- **Measured:** classifying 5,200 entries by type is **~7x faster** with `scandir` (~403 ns/entry) than
  `listdir` + `isdir` (~2677 ns/entry), the saved per-entry `stat` syscalls.
- **Use `scandir`/`os.walk` for traversal;** read the cached type, and call `entry.stat()` only for entries
  whose full metadata you need. Mind symlink following, `os.walk` pruning (in-place edit), and closing the
  iterator.

**Cross-references.** Per-item syscall avoidance → Chapters 40 and 44. `pathlib` and `rglob` → Chapter 43.
Higher-level tree ops (`shutil`) and directory watching → the rest of Deep R. The ingest seam → Deep U.
