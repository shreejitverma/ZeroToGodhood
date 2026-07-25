# Chapter 43: Paths with `pathlib`

A code reviewer pushes back on switching a module from `os.path` to `pathlib`: "isn't creating a `Path`
object for every path slower than just joining strings?" It is, measurably, a `Path` join is **3.6x
slower** than `os.path.join`. And it does not matter, because that join, at about **930 nanoseconds**,
costs *less than a single `os.stat`*, the cheapest filesystem syscall there is, at ~1700 ns. Any code that
actually touches the filesystem, opens, reads, walks, stats, does so many times per path, and the join
overhead disappears against even one of those operations. The performance objection is real in the
benchmark and irrelevant in practice, and knowing the difference is the point.

So `pathlib` is chosen on the axis that matters, correctness and readability, not fought over speed. This
chapter continues **Deep R** with the modern path API: paths as objects joined with `/`, parsed by
property, and manipulated without string surgery, and the measurement that puts the "too slow" worry to
rest. It builds on Chapter 40 (the file I/O these paths feed).

## Section index

- **43.1** Paths as objects
- **43.2** Why the object overhead does not matter
- **43.3** Measurement: a join costs less than a `stat`
- **43.4** Edges and failure modes
- **43.5** Connections
- **43.6** Exercises
- **43.7** Summary and cross-references

Listings live under `code/ch043/` and are re-executed by `make verify` on both interpreters.

---

## 43.1 Paths as objects

```python
# code/ch043/l01_pathlib.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- joining: the / operator, not string concatenation ---
  built path          : /srv/app/data/report.tar.gz
--- parsing: parts by property, no manual splitting ---
  .name               : report.tar.gz
  .stem               : report.tar
  .suffix             : .gz
  .suffixes           : ['.tar', '.gz']
  .parent             : /srv/app/data
  .parts              : ('/', 'srv', 'app', 'data', 'report.tar.gz')
--- manipulation: derive new paths without string surgery ---
  with_suffix('.txt') : /srv/app/data/report.tar.txt
  with_name('x.log')  : /srv/app/data/x.log
  relative_to(/srv)   : app/data/report.tar.gz
--- a real round-trip on the filesystem (temp dir) ---
  rglob('*.txt')      : ['notes.txt', 'sub/more.txt']
  read_text           : 'hello\n'
  exists / is_dir     : True / True
```

`pathlib.Path` makes a filesystem path a first-class object. **Joining** uses the `/` operator:
`Path("/srv/app") / "data" / "report.tar.gz"` reads like the path it builds and handles separators
correctly on every OS, no manual `"/".join` or `os.sep` juggling. **Parsing** is by property, not string
slicing: `.name`, `.stem` (name minus the last suffix), `.suffix`/`.suffixes`, `.parent`, and `.parts`
replace the error-prone `os.path.splitext`/`basename`/`dirname` dance. **Manipulation** derives new paths
without surgery: `.with_suffix`, `.with_name`, and `.relative_to` produce correct results where hand-written
string replacement would mishandle edge cases (a `.` in a directory name, a missing suffix, a trailing
separator).

The bottom block shows the I/O side: `Path` methods (`read_text`, `write_text`, `mkdir`, `exists`,
`is_dir`, `rglob`) do filesystem operations directly, so a path and the operations on it live on one object.
`PurePath`/`PurePosixPath` (used in the top blocks) does the pure *manipulation* without touching the
filesystem, which is why those parts of the listing are deterministic and OS-independent.

---

## 43.2 Why the object overhead does not matter

Every `Path` operation constructs a `Path` object, whereas `os.path` functions manipulate plain strings. An
object has a real cost, allocation, attribute setup, so a pure `Path` join is several times a string join.
If path manipulation were the bottleneck, this would matter. It essentially never is.

The reason is arithmetic. A `Path` join is ~930 ns. A single `os.stat`, the cheapest real filesystem
operation, is ~1700 ns, already more than the join. Opening a file, reading it, or walking a directory costs
far more still (microseconds to milliseconds), and involves multiple syscalls. Real path-handling code does
I/O, that is why it has paths at all, so for every path join there are one or more syscalls that each cost
more than the join. The join overhead is a rounding error on the total. The only scenario where it would
show is millions of *pure* path manipulations with *zero* I/O, which is rare and, if you hit it, is exactly
where you would drop to `os.path` strings deliberately. Everywhere else, the readability and correctness of
`pathlib` are free.

---

## 43.3 Measurement: a join costs less than a `stat`

**Methodology.** `code/ch043/bench_pathjoin.py`. `os.path.join` versus `PurePosixPath` `/`-join for the same
three-segment path, plus a single `os.stat` on an existing file as the filesystem yardstick. `min` per call;
ratios relative to `os.path.join`. The `os.stat` case is syscall-bound and noisier (harness may flag it
machine-busy). CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| operation | min per call | ratio |
|---|---|---|
| `os.path.join` (string) | **260 ns** | 1.00x |
| `Path` `/` join (object) | **930 ns** | **3.58x** |
| `os.stat` (1 syscall) | **~1700 ns** | **~6.5x** |

The `Path` join is **3.58x** the string join, the real object overhead. But it is **~0.55x** of a single
`os.stat`: one filesystem syscall costs almost twice a `Path` join. Since any path exists to be used, and
using it means at least one such syscall (usually many), the join's 670 ns of overhead is dominated by the
very next line of real work. The benchmark confirms the objection's premise (Path is slower) and refutes its
conclusion (therefore avoid it): the slower operation is still cheaper than the cheapest thing you will do
with its result.

The rule: **choose `pathlib` for correctness and readability; do not avoid it for speed.** Reach back to
`os.path` strings only in the rare, measured case of a hot loop doing pure path arithmetic with no
filesystem access, and then as a deliberate, documented optimization, not a default. This is the Deep Q/R
discipline again: measure the worry, and let the measurement, not folklore, decide.

---

## 43.4 Edges and failure modes

**Micro-optimizing path joins.** §43.3. Dropping `pathlib` for `os.path` to save ~670 ns per join is a
non-optimization in any code that does I/O. Do not; the overhead is dominated by the first syscall.

**`Path` vs `str` at API boundaries.** Most stdlib functions accept `Path` (via `os.PathLike`), but some
third-party or older APIs want a `str`. Pass `str(path)` at those boundaries; do not assume every function
takes a `Path`.

**`with_suffix` on multi-suffix names.** `.with_suffix` replaces only the *last* suffix:
`Path("a.tar.gz").with_suffix(".txt")` is `a.tar.txt`, not `a.txt`. For the full stem, use `.stem` in a loop
or split on `.suffixes`. This is a common surprise.

**`rglob`/`glob` and symlinks / huge trees.** `rglob("*")` walks the entire subtree eagerly-ish and can
follow symlinks into cycles or descend enormous directories. For large trees prefer `os.scandir`/`os.walk`
with explicit control, or bound the walk; do not `list(path.rglob("*"))` a huge filesystem.

**`resolve()` and non-existent paths.** `Path.resolve()` canonicalizes and (by default) requires the path to
exist for full resolution of symlinks; behavior around missing components has shifted across versions. Know
whether you need `resolve()` (real, symlink-free path) or just `absolute()` (absolute but not resolved).

**Relative-path assumptions.** `relative_to` raises `ValueError` if the path is not actually under the given
base. Guard it, or use `os.path.relpath` when you need a `..`-based relative path between siblings.

---

## 43.5 Connections

**Backward.** The file I/O that `Path.read_text`/`write_text` perform, and the `encoding=` they take, is
Chapter 40. The `str` these paths ultimately are (and the `os.PathLike` protocol bridging them) is Chapter 7.
The `/` operator working on `Path` is operator overloading via `__truediv__`, the data-model theme of
Chapter 4.

**Forward.** Directory walking at scale (`os.scandir`, `os.walk`) and the OS process interface (`os`,
`subprocess`) are the next Deep R material. The `glob` pattern matching `rglob` uses connects to the text-
processing tools of **Deep R**.

**Across books.** `pathlib` is how Book II names files and directories at every seam, and the §43.3 point,
that path-object overhead is negligible against I/O, is why a **Book III** data pipeline can use readable
`Path` code throughout its ingest without a performance thought: the corpus walk is bounded by the millions
of syscalls it makes, not by the `Path` objects it constructs. **Deep U** owns the storage-layout seam.

---

## 43.6 Exercises

**1. Reproduce the overhead and its irrelevance.** Run §43.3's benchmark and confirm the `Path` join is
several times a string join but cheaper than one `os.stat`. Then write a loop that joins a path and stats it,
and show the join is a small fraction of the iteration. Explain why the "pathlib is slow" worry is
misplaced.

**2. Parse by property.** Take a multi-suffix filename and extract the full stem (without any suffix) and the
list of suffixes. Show that `.with_suffix` only replaces the last one. Explain the semantics and why string
splitting on `.` is error-prone.

**3. Walk a tree.** Build a small directory tree and list all `.txt` files with `rglob`. Then reason about
what `rglob` would do on a huge tree with symlinks, and how `os.scandir`/`os.walk` give more control.

**4. Cross the str boundary.** Pass a `Path` to a function that wants a `str`, observe it works or fails
depending on the API, and fix it with `str(path)`. Explain the `os.PathLike` protocol and its limits.

**5. The design question.** `pathlib` trades some speed for an object-oriented, correct-by-construction path
API. Argue why that is the right default despite the measured overhead. Your answer must use the §43.3
numbers (join vs stat), address the rare case where `os.path` strings are justified, and explain why
readability and correctness usually outweigh nanoseconds that I/O dwarfs.

---

## 43.7 Summary and cross-references

- **`pathlib.Path`** makes a path an object: join with **`/`**, parse by **property** (`.name`, `.stem`,
  `.suffix`, `.parent`, `.parts`), and manipulate with `.with_suffix`/`.with_name`/`.relative_to`, no string
  surgery. `Path` methods do I/O; `PurePath` does pure manipulation.
- **Measured:** a `Path` join is **3.58x** an `os.path.join` (930 ns vs 260 ns) but **cheaper than one
  `os.stat`** (~1700 ns). The object overhead is dominated by the first filesystem syscall.
- **Choose `pathlib` for correctness and readability, not against it for speed.** Drop to `os.path` strings
  only for the rare hot loop of pure path arithmetic with no I/O.
- **Edges:** `with_suffix` replaces only the last suffix; pass `str(path)` at APIs that want strings; bound
  `rglob` on huge trees.

**Cross-references.** File I/O and `encoding=` → Chapter 40. Paths as `str`/`os.PathLike` → Chapter 7.
Operator overloading (`/`) → Chapter 4. Directory walking and the OS interface → the rest of Deep R. The
storage-layout seam → Deep U.
