# Chapter 68: Packages and Namespace Packages

Two teams ship plugins for the same application under a shared import name, `acme.plugins.billing` and
`acme.plugins.reporting`, installed independently into different directories. This should be impossible with a
*regular* package: a regular package is a directory with an `__init__.py`, rooted in *one* place, and two
installs would clobber each other's `acme/`. It works because `acme.plugins` is a **namespace package** (PEP
420): a directory *without* `__init__.py` that Python assembles from *every* matching directory on `sys.path`,
merging them into one package whose `__path__` spans all the roots. The listing shows a namespace package
`nspkg` whose two submodules live in two different `sys.path` directories, imported as if they were one package.
The trade is a small resolution cost, measured, resolving a namespace-package submodule is **1.5x** a regular
one, because the finder must consider all the contributing directories.

This chapter closes **Deep G** with packages: the regular package (`__init__.py`, single root, runs setup) and
the namespace package (no `__init__.py`, split across roots, no setup), and when each is right. It ties together
the search mechanism (Chapter 67) and the import machinery (Chapters 63-66) into how a *package* is found and
assembled.

## Section index

- **68.1** Regular vs namespace packages
- **68.2** When to use each
- **68.3** Measurement: the cost of a split package
- **68.4** Edges and failure modes
- **68.5** Connections
- **68.6** Exercises
- **68.7** Summary and cross-references

Listings live under `code/ch068/` and are re-executed by `make verify` on both interpreters.

---

## 68.1 Regular vs namespace packages

```python
# code/ch068/l01_packages.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- namespace package: one name, split across two sys.path roots ---
  part from rootA        : A
  part from rootB        : B
  __path__ spans N roots : 2
  no __init__.py (__file__ is None): True
--- regular package: single root, __init__.py runs on import ---
  __init__ ran           : True
  __file__ is the __init__.py : True
  __path__ is a plain list    : True
--- the difference ---
  namespace: no __init__, spans roots (plugins/split distributions)
  regular:   __init__ runs setup, single root (the normal default)
```

A **regular package** is a directory with an `__init__.py`. On import, its `__init__.py` *runs* (the counter
confirms it), so it is the place for package-level setup (defining the public API, `__all__`, package-wide
constants). Its `__file__` is that `__init__.py`, and its `__path__` is a plain one-element `list`, the single
directory it lives in.

A **namespace package** (PEP 420) is a directory *without* `__init__.py`. The listing's `nspkg` exists in *two*
`sys.path` roots (`rootA/nspkg` and `rootB/nspkg`), and Python assembles them into *one* package: importing
`nspkg.part_a` (from rootA) and `nspkg.part_b` (from rootB) both work, and `nspkg.__path__` spans **2** roots. A
namespace package has **no `__init__.py`** (its `__file__` is `None`), so there is no package-level code and no
single owner, exactly what lets independently-installed pieces share one import name. Its `__path__` is a special
`_NamespacePath` (not a plain list) that is recomputed as `sys.path` changes.

---

## 68.2 When to use each

The choice is about *ownership and structure*, and the default is clear.

**Use a regular package (with `__init__.py`) for almost everything.** It is a single, owned unit: one directory,
one place for setup, an explicit `__init__` where you can define the package's public surface and run
initialization. It is unambiguous (`__path__` is one directory), slightly faster to resolve (§68.3), and the
form every packaging tool and reader expects. When you create a package, add an `__init__.py`, even an empty one,
unless you have a specific reason not to.

**Use a namespace package only when you genuinely need one import name assembled from independently-distributed
pieces.** The canonical cases are *plugin namespaces* (a shared `company.plugins` under which third parties drop
their own subpackages, each installed separately) and *split distributions* (a large project shipped as several
installable pieces that share a top-level name). Here the absence of `__init__.py` is essential: if any piece
shipped an `__init__.py`, it would claim the namespace and prevent the others from contributing. Namespace
packages exist to make a name *shareable*, not to save typing an empty `__init__.py`.

The anti-pattern is an *accidental* namespace package: forgetting the `__init__.py` in a directory you intended
as a regular package. It often still *works* (namespace packages are importable), which hides the mistake, until
it interacts badly with tooling, or a stray same-named directory elsewhere on `sys.path` silently merges in. The
rule: **add `__init__.py` deliberately for regular packages; omit it deliberately for namespace packages; never
omit it by accident.**

---

## 68.3 Measurement: the cost of a split package

**Methodology.** `code/ch068/bench_pkg_resolve.py`. `find_spec` for a submodule of a namespace package (split
across two roots) versus a submodule of a regular package (single root). `min` per call; ratio relative to the
regular package. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| resolve a submodule | min per call | ratio |
|---|---|---|
| regular package (single root) | **6,036 ns** | 1.00x |
| namespace package (two roots) | **9,249 ns** | **1.5x** |

Resolving a namespace-package submodule costs **1.5x** a regular one. The reason is structural: a regular
package has a single `__path__` directory, so resolving `regpkg.sub` checks one place; a namespace package's
`__path__` can span several roots (and is recomputed rather than cached the same way), so resolving `nspkg.part_a`
must consider all contributing directories. The overhead grows with how many roots contribute to the namespace.

The rule reinforces §68.2: **prefer regular packages by default**, they are slightly cheaper to resolve *and*
give you an `__init__.py` for setup and a single clear owner. The namespace package's resolution cost is small in
absolute terms and worth paying *when you need the shareable-name semantics*, but it is not a free or preferable
alternative to a regular package. Reach for a namespace package for its *structural* property (a name assembled
from independent pieces), not casually, and accept the modest resolution cost as the price of that flexibility.

---

## 68.4 Edges and failure modes

**Accidental namespace package.** §68.2. A missing `__init__.py` makes a directory a namespace package that
often still imports, hiding the mistake and risking silent merges with same-named directories elsewhere. Add
`__init__.py` deliberately for regular packages.

**A stray same-named directory merging in.** Because a namespace package merges *all* matching directories on
`sys.path`, an unrelated directory with the same name (a leftover, a shadow, Chapter 67) silently becomes part of
the package. Namespace packages are more exposed to this than regular packages (which stop at the first
`__init__.py`).

**Putting an `__init__.py` in one piece of a namespace.** If any distribution contributing to a namespace package
ships an `__init__.py`, it turns the directory into a *regular* package and *prevents* the other pieces from
contributing. Every piece of a namespace package must omit `__init__.py`.

**Relying on namespace-package `__file__`.** A namespace package's `__file__` is `None` (there is no single
file). Code that assumes `package.__file__` is a path (to locate data files, for instance) breaks on namespace
packages. Use `importlib.resources` for package data, not `__file__`.

**Slower resolution at scale.** §68.3. A namespace split across many roots costs more to resolve per submodule.
For a large, single-owner package, a regular package is both faster and simpler; do not split a package into a
namespace without the sharing need.

**Confusing packages with directories on `PYTHONPATH`.** A directory is only a package if it is reachable *as* a
package name (its parent on `sys.path`), and only a *regular* package if it has `__init__.py`. Mis-set
`PYTHONPATH` produces surprising namespace packages; keep the path deliberate (Chapter 67).

---

## 68.5 Connections

**Backward.** The `sys.path` search that finds the package's contributing directories is Chapter 67 (and its
shadowing hazard applies doubly to namespace merges). The `__init__.py` body that runs on import is Chapter 63's
"body runs once". The `.pyc` cache for `__init__.py` and submodules is Chapter 66.

**Forward.** The finder/loader protocol (`sys.meta_path`, path hooks) that implements this assembly is a deeper
**Deep G** topic. `importlib.resources` (accessing package data without `__file__`) and packaging metadata are
Deep N. The plugin-discovery patterns namespace packages enable (entry points, `pkgutil`) are a Deep N/Deep O
topic.

**Across books.** Package structure is how Book II organizes code for **Book III**. A **Book III** application is
a regular package with a clear `__init__` public API, while its *plugin* system, third-party retrievers, model
backends, tool integrations, uses a namespace package so independently-installed plugins share one import
namespace without a central registry. The §68.3 cost is negligible against the flexibility that buys, and the
§68.2 default (regular unless you need sharing) keeps the core unambiguous. **Deep U** owns the project- and
plugin-structure seam; **Deep N** owns packaging.

---

## 68.6 Exercises

**1. Build a namespace package.** Create a package name split across two `sys.path` roots (no `__init__.py`) and
import a submodule from each. Confirm `__path__` spans both roots and `__file__` is `None`. Explain how Python
assembled them.

**2. Build a regular package.** Create a package with an `__init__.py` that runs setup, and confirm the `__init__`
runs on import and `__path__` is a single-element list. Explain what the `__init__` is for.

**3. Break a namespace.** Add an `__init__.py` to one contributing directory of a namespace package and show the
other pieces can no longer contribute. Explain why namespace pieces must omit `__init__.py`.

**4. Measure the resolution cost.** Run §68.3's benchmark and confirm namespace-submodule resolution costs more
than a regular one. Explain the multi-root `__path__` and why it is slower.

**5. The design question.** Python supports both regular packages (single-rooted, with setup) and namespace
packages (shareable, split, no setup). Argue when each is right. Your answer must use the §68.3 measurement,
identify the plugin/split-distribution cases that need namespace packages, and explain why a regular package is
the correct default and an accidental namespace package is a bug.

---

## 68.7 Summary and cross-references

- A **regular package** has an **`__init__.py`** (which runs setup on import), a **single root**, and a list
  `__path__`. It is the **default** for an owned unit of code.
- A **namespace package** (PEP 420) has **no `__init__.py`**, can be **split across multiple `sys.path` roots**
  (merged into one package whose `__path__` spans them), and has `__file__ = None`. Use it only to share one
  import name across **independently-installed pieces** (plugins, split distributions).
- **Measured:** resolving a namespace-package submodule is **1.5x** a regular one (9,249 ns vs 6,036 ns), because
  the finder considers all contributing roots. **Prefer regular packages by default.**
- **Edges:** an accidental missing `__init__.py` makes a silent namespace package; a stray same-named directory
  can merge in; namespace `__file__` is `None` (use `importlib.resources` for data).

**Cross-references.** `sys.path` search and shadowing → Chapter 67. `__init__` body runs once → Chapter 63.
`.pyc` cache → Chapter 66. Finders/loaders → Deep G. `importlib.resources`, packaging, plugin discovery → Deep N.
The project/plugin-structure seam → Deep U.
