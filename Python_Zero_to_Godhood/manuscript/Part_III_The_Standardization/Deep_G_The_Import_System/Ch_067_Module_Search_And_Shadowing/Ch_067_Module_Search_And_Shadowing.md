# Chapter 67: Module Search and Shadowing

A beginner writes a script that uses `import random`, saves it as `random.py`, runs it, and gets
`AttributeError: module 'random' has no attribute 'randint'`. The standard library's `random` is fine; the
problem is that the script *is named* `random.py`, and Python imported *it* instead of the stdlib module. This
is the shadowing trap, and it follows from one rule: to import `X`, Python searches `sys.path` **in order** and
imports the **first** directory that has an `X`. Because `sys.path[0]` is the directory of the running script,
a local file named like a stdlib module wins. The search order also has a cost dimension, measured, a module
found at the back of a 60-directory `sys.path` costs **8.4x** one found at the front (227 us vs 27 us), because
the finder walks the path linearly until it hits a match.

This chapter continues **Deep G** with module search: how `sys.path` and the finders resolve an import, why
first-match-wins causes shadowing, and the position cost of a long path. It is the "how a module is *located*"
counterpart to Chapter 63's "what happens once it is found."

## Section index

- **67.1** First match wins
- **67.2** Why local files shadow the standard library
- **67.3** Measurement: position on `sys.path`
- **67.4** Edges and failure modes
- **67.5** Connections
- **67.6** Exercises
- **67.7** Summary and cross-references

Listings live under `code/ch067/` and are re-executed by `make verify` on both interpreters.

---

## 67.1 First match wins

```python
# code/ch067/l01_shadowing.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- first match wins: a directory earlier on sys.path shadows a later one ---
  imported mymath from shadowdir : True
--- the trap: a local file named like a stdlib module (shown via find_spec) ---
  with shadowdir first, 'queue' is local : True
--- remove the shadow directory: 'queue' resolves to the stdlib again ---
  without shadowdir, 'queue' is stdlib   : True
  lesson: never name your file after a stdlib module (random, queue, email, string, ...)
```

Importing a module runs the *import machinery*: Python asks each finder on `sys.meta_path`, and the path-based
finder walks `sys.path` in order, returning the **first** directory that contains the module. The listing puts a
`shadowdir` at the front of `sys.path` and imports `mymath` from it (first-match-wins). Then, *safely* via
`importlib.util.find_spec` (which *locates* a module without *importing* it, so nothing breaks), it shows the
trap: with `shadowdir` first, the name `queue` resolves to the *local* `queue.py`, not the standard library's
`queue`; remove `shadowdir` and `queue` resolves to the stdlib again. The local file shadowed the stdlib purely
because its directory came first.

`find_spec` is the right tool for *inspecting* resolution: it returns a `ModuleSpec` with the `origin` (the file
that *would* be imported) without executing anything, so you can diagnose "which module does this name actually
resolve to?" without the side effects of importing.

---

## 67.2 Why local files shadow the standard library

The shadowing bug is not random bad luck; it is the *guaranteed* consequence of two facts. First, **first match
wins**: the finder stops at the earliest `sys.path` directory that has the name. Second, **`sys.path[0]` is the
script's own directory** (or `''`, meaning the current directory, in the REPL and with `-c`). Put those
together: a file next to your script, or in your working directory, is checked *before* the standard library and
site-packages. So `random.py`, `queue.py`, `email.py`, `string.py`, `test.py`, any file named like a stdlib
module, will be imported *instead* of the real one whenever your directory is on the path first, which it almost
always is.

The failure is especially confusing because the *error* appears far from the *cause*: `import random` succeeds
(it found your file), and the crash comes later when the code accesses `random.randint`, which your file does not
define, yielding `AttributeError: module 'random' has no attribute 'randint'`. The stdlib module was never
loaded; your file masqueraded as it. Worse, the shadowing file might be one you forgot about, or a leftover
`test.py`, making the bug appear and disappear with the working directory.

The rule is simple and absolute: **never name a module (or a top-level script) after a standard-library or
third-party module you import.** When you hit a baffling `AttributeError` on a stdlib module, `find_spec` the
name (or check `module.__file__`) to see *which* file was actually imported, the fix is to rename your file and
delete its `__pycache__`. More broadly, prefer **packages and absolute imports** over loose scripts in a
directory full of modules, so the namespace is explicit and the script directory is not a minefield.

---

## 67.3 Measurement: position on `sys.path`

**Methodology.** `code/ch067/bench_search_order.py`. `find_spec` for a module in the *first* directory of a
`sys.path` with 60 extra directories versus one in the *last*, and a missing module (which scans all). `min` per
call. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| `find_spec` on a 60-dir path | min per call | ratio |
|---|---|---|
| found near the front | **27,063 ns** | 1.00x |
| found at the back | **226,961 ns** | **8.4x** |
| missing (scan all 60) | **231,913 ns** | 8.6x |

A module at the *front* resolves in ~27 us; one at the *back* of the 60-directory path takes ~227 us, **8.4x**
more, because the finder checks each directory in turn until it matches. A *missing* module is the worst case:
it pays the full scan (~232 us) before concluding the module does not exist. The cost is roughly linear in how
many directories are checked before the match (the import system caches directory *listings*, so this is scan-
order overhead, not raw `stat` per lookup, but the order still dominates).

The rule: **keep `sys.path` short and put the most-used locations first.** A bloated `sys.path` (dozens of
egg/dev-install entries, redundant paths) makes *every* import, and especially every *failed* import attempt
during resolution, slower. This matters most at startup, where many modules are resolved, and it compounds with
the shadowing hazard: a long path is both slower to search and more likely to contain an accidental shadow. The
measurement reinforces §67.2's correctness point with a performance one: `sys.path` order is not just *which*
module wins, but *how fast* resolution is, so a clean, short, well-ordered path is both correct and quick.

---

## 67.4 Edges and failure modes

**Naming a file after a stdlib/third-party module.** §67.2. It shadows the real one (first-match-wins,
`sys.path[0]` is your directory), producing a baffling `AttributeError` at *use* time. Rename the file and delete
its `__pycache__`.

**Diagnosing with `__file__`/`find_spec`.** When an import behaves wrongly, check `module.__file__` (where it
came from) or `importlib.util.find_spec(name).origin` (where it *would* come from) to find the shadow. Do not
guess.

**A bloated `sys.path`.** §67.3. Long paths slow every import and every failed-resolution scan. Prune dead
entries; do not `sys.path.append` casually in library code.

**Mutating `sys.path` at runtime.** Inserting a directory at the front to "make imports work" changes resolution
globally and can introduce shadows or non-determinism. Prefer proper packaging (installed packages, `-m`,
`PYTHONPATH` set deliberately) over runtime `sys.path` hacks.

**`''` vs the script directory.** In the REPL and `-c`, `sys.path[0]` is `''` (the *current* working directory),
so imports depend on *where you launched Python*, a source of "works here, not there" bugs. Run modules with
`python -m pkg.module` (which puts the package root on the path, not the cwd) for stable resolution.

**Stale `__pycache__` after renaming.** After renaming a shadowing file, its `.pyc` may linger; a stale
`__pycache__` can keep serving the old module. Delete `__pycache__` when resolving shadowing bugs.

---

## 67.5 Connections

**Backward.** Once a module is *found*, the "run its body once and cache in `sys.modules`" step is Chapter 63,
this chapter is the *find* that precedes it. The `AttributeError` the shadow produces is Chapter 6. The
`.pyc`/`__pycache__` that can linger after a rename is Chapter 66.

**Forward.** Packages and namespace packages (how a *package* is found across multiple directories) are the next
Deep G chapter. The finder/loader protocol (`sys.meta_path`, `MetaPathFinder`, `PathEntryFinder`) and import
hooks are a deeper **Deep G** topic. `PYTHONPATH`, `-m`, and installed-package resolution connect to packaging
(Deep N).

**Across books.** Clean import resolution is how Book II keeps its own and **Book III**'s codebases predictable.
A **Book III** project structured as installed packages with absolute imports, run via `-m`, has no
script-directory shadowing and a short, deliberate `sys.path`, so imports are both correct and fast, and no
stray `queue.py` can masquerade as the stdlib. The §67.2 trap is a classic beginner-and-expert bug that proper
packaging (Deep N) eliminates. **Deep U** owns the project-structure seam.

---

## 67.6 Exercises

**1. Reproduce shadowing.** Create a file named after a stdlib module you use, import that module, and observe the
`AttributeError` at use time. Use `find_spec`/`__file__` to confirm which file was imported. Explain first-match-
wins and `sys.path[0]`.

**2. Diagnose safely.** Use `importlib.util.find_spec` to inspect where a name *would* resolve with and without a
shadow directory on the path, without importing. Explain why `find_spec` is the right diagnostic tool.

**3. Measure the position cost.** Run §67.3's benchmark and confirm a module at the back of a long path costs
several times one at the front. Explain the linear scan and why a missing module is the worst case.

**4. Fix with packaging.** Restructure a directory of loose scripts into a package and run a module with `python
-m`. Show that the script-directory shadow risk is gone. Explain how `-m` changes `sys.path`.

**5. The design question.** Import resolution is first-match-wins over an ordered `sys.path` whose first entry is
the script's directory. Argue the trade-offs of this design. Your answer must use the §67.3 measurement, explain
why it makes local files shadow the stdlib, and say how packaging and `-m` mitigate it.

---

## 67.7 Summary and cross-references

- Importing `X` searches **`sys.path` in order** and takes the **first** directory with an `X`. **`sys.path[0]`
  is the script's directory** (or `''` = cwd in the REPL/`-c`), so a **local file named like a stdlib module
  shadows it**, a baffling `AttributeError` at use time.
- Diagnose with **`find_spec`** (locates without importing) or `module.__file__`; fix by **renaming the file and
  deleting `__pycache__`**. Never name a file after a module you import.
- **Measured:** a module at the back of a 60-directory `sys.path` costs **8.4x** one at the front (227 us vs 27
  us); a missing module pays the full scan. **Keep `sys.path` short and ordered.**
- Prefer **packages, absolute imports, and `python -m`** over loose scripts and runtime `sys.path` hacks.

**Cross-references.** Import caching and `sys.modules` → Chapter 63. `AttributeError` → Chapter 6.
`__pycache__` → Chapter 66. Packages and namespace packages, finders/loaders → the rest of Deep G. `PYTHONPATH`/
packaging → Deep N. The project-structure seam → Deep U.
