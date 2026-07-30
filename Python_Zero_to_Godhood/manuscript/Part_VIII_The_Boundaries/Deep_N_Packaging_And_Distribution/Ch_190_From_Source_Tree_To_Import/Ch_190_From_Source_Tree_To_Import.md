# Chapter 109: From Source Tree to Import

Packaging is the part of Python with the most tooling, the most history, and the least mechanism actually shown. Deep N opens by correcting that ratio: the listing builds a real, spec-valid **wheel** with nothing but `zipfile`, "installs" it by extraction into a temporary directory, imports it, and reads its own metadata back through `importlib.metadata`, the entire lifecycle, offline, deterministic, verified on all three interpreters.

The demystification is the point. A wheel is **a zip file with a naming convention**, `tinypkg-1.0.0-py3-none-any.whl`, where the filename is the compatibility claim (Chapter 110 decodes it). Installing is **extracting onto the import path**, no registry, no compilation, no magic, which is why the freshly extracted module imports and returns `42`. And everything an installer knows afterwards lives in one `*.dist-info/` directory: `METADATA` for humans and resolvers, `RECORD` with a **sha256 per file** for uninstall and integrity, the same content-addressing that anchors lockfiles (Chapter 114) and uploads.

The benchmark adds the two numbers worth carrying: a wheel is *itself* importable (zipimport), at ~7.6x the first-import cost of extracted files, and `entry_points()` reads **every** dist-info on the path, scaling with the environment's size (13 to 32 ms across 10 to 500 distributions) where `distribution(name)` stays near-flat, the measured reason plugin startup drags in fat environments and a small environment is a performance feature.

**This is a Deep N chapter, and it opens Deep N.**
Deep G owns how `import` *finds* things; this volume owns how things *get there*: the artifacts, the metadata contracts, the build system, the resolver, the environments, the locks, and the compiled-code and supply-chain endgames.

## Section index

- **109.1** The lifecycle, by hand
- **109.2** The model: artifacts, metadata, and the installer's contract
- **109.3** Measurement: install shapes and metadata scans
- **109.4** Edges and failure modes
- **109.5** Connections
- **109.6** Exercises
- **109.7** Summary and cross-references

Listings live under `code/ch190/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build. Everything in this volume runs offline, by design: the mechanisms are local even when the ecosystem is not.

---

## 109.1 The lifecycle, by hand

```python
# code/ch190/l01_anatomy_of_an_installed_package.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- a wheel is a zip with a naming convention ---
  built  : tinypkg-1.0.0-py3-none-any.whl
  parsed : name=tinypkg, version=1.0.0, tag=py3-none-any
    tinypkg-1.0.0.dist-info/METADATA
    tinypkg-1.0.0.dist-info/RECORD
    tinypkg-1.0.0.dist-info/WHEEL
    tinypkg.py
  the filename IS the compatibility claim (Chapter 110 decodes
  the tag); the payload is code plus one .dist-info directory
--- installing is extracting onto the import path ---
  import tinypkg; tinypkg.answer() : 42
  no registry, no compilation step, no magic: files in a
  directory that sys.path reaches (Deep G owns the finding)
--- .dist-info is the installer's memory ---
  metadata Name    : tinypkg
  metadata Version : 1.0.0
  Requires-Python  : >=3.9
  RECORD lists     : ['tinypkg-1.0.0.dist-info/METADATA', 'tinypkg-1.0.0.dist-info/RECORD', 'tinypkg-1.0.0.dist-info/WHEEL', 'tinypkg.py']
  importlib.metadata reads the SAME dist-info any installer
  writes: metadata for humans and resolvers, RECORD (with a
  sha256 per file) for uninstall and integrity
--- RECORD's hashes verify, because we can check ---
  recorded hash matches installed file : True
```

**Four files are the entire artifact.**
The module, `METADATA` (name, version, `Requires-Python`, and in real packages the dependency list Chapter 112 resolves), `WHEEL` (format version and the tag, repeated from the filename), and `RECORD` (every installed path with its digest and size). The listing wrote them with `zipfile.writestr` and correct sha256 lines, and every installer on earth would accept the result, the spec is that small, and knowing it *is* the demystification.

**`import tinypkg` succeeding is the chapter's thesis.**
Between "wheel on disk" and "module in `sys.modules`" there was exactly one operation: `extractall` into a directory on `sys.path`. Everything else installers do, resolving (112), environment selection (113), script generation, bytecode compilation, is service around that extraction, and separating the essence from the services is what makes the rest of the volume legible.

**`importlib.metadata` closes the loop from the inside.**
The running program reads the same `dist-info` the installer wrote: version lookups, `Requires-Python`, the file list. This is the API that replaced `pkg_resources` (whose import-time scan cost a generation of CLI startup time), and §109.3 measures where its own costs live.

**And the hash check is the volume's trust model in miniature.**
`RECORD`'s digest recomputed from the installed file matches. The same urlsafe-base64 sha256 format secures lockfile pins (114) and index uploads (116): packaging's one trust anchor, end to end, is content addressing, and it is checkable with twelve lines of stdlib.

---

## 109.2 The model: artifacts, metadata, and the installer's contract

**Two artifact kinds, one asymmetry.**
An **sdist** is the source tree plus `pyproject.toml`: installing it means *running a build* on the user's machine, with the build backend and its dependencies (Chapter 111's contract) and arbitrary code execution as the price. A **wheel** is built, tagged, and extract-only: installing it cannot run project code at all. Every installer prefers wheels for speed *and* for that security property, and the ecosystem's history (Chapter 116) is largely the campaign to make wheels exist for everything, everywhere, which for compiled code is Chapter 115's whole subject.

**The metadata is layered by consumer.**
The *filename* is for the index and the installer's candidate filter (cheap rejection before download, Chapter 110). `METADATA` is for the resolver (dependencies, markers, `Requires-Python`) and for humans. `RECORD` is for the installer's own bookkeeping: uninstall is "delete what RECORD lists", upgrade is uninstall-then-install, and integrity checking is re-hashing. Each layer answers one question without opening the layers below it, which is what lets an index serve millions of packages on filename alone.

**`site-packages` is a convention, not a mechanism.**
The interpreter imports from `sys.path` (Deep G); `site-packages` is merely the directory the `site` module appends and installers target. The listing's temporary directory served identically. This deflation matters practically: editable installs (a `.pth` file pointing at your tree), virtual environments (Chapter 113's redirected prefix), and vend-in strategies are all just path arrangements, and debugging any packaging mystery starts with `sys.path`, not with the installer.

**The installer's whole contract, then**: pick a compatible wheel (110), or build one from an sdist (111), after choosing versions (112); extract into the environment's site directory (113); write `RECORD`; generate entry-point scripts. Six verbs, each a chapter, and none of them magic.

---

## 109.3 Measurement: install shapes and metadata scans

**Methodology.** `code/ch190/bench_install_shapes.py`.
Fresh subprocess per import measurement (imports cache, Deep G), `min` of 9; metadata scans against synthesised sites of 10/100/500 distributions, `min` of 5. 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**a. First import, by installation shape.**

| shape | first import |
|---|---|
| extracted directory | 79 us |
| the wheel itself on `sys.path` (zipimport) | 602 us |

**b. Metadata lookups vs environment size.**

| installed distributions | `distribution('pkg000')` | `entry_points()` |
|---|---|---|
| 10 | 0.13 ms | 13.4 ms |
| 100 | 0.24 ms | 17.1 ms |
| 500 | 0.89 ms | **31.7 ms** |

**Zipimport works, and costs its convenience.**
A wheel on `sys.path` is importable directly, zipimport has shipped since 2.3, and pays ~7.6x on first import here: open the archive, read its directory, decompress the module. Amortised over a many-module `zipapp` it is a fine deployment shape; per-package it is why extraction is the norm, along with the harder constraints (C extensions must be real files for `dlopen`, `mmap` wants files, `__file__`-relative data wants directories, Chapter 115).

**The `entry_points()` row is the one that bites real programs.**
`distribution(name)` probes for one directory and stays near-flat. `entry_points()` must read *every* dist-info on the path, there is no index of who provides what, and scales with the environment: 32 ms at 500 distributions, paid at import time by any plugin framework that scans at startup, per process, forever. The mitigations are all boring and effective: query one group, cache the result, and keep environments small, which converts Chapter 113's hygiene argument into a measured performance argument.

**Book I**'s cousin numbers are `dlopen` costs and symbol-table scans, and its packaging chapter draws the same two morals with different nouns: loaders are cheap next to lookups that scan the world, and the size of "the world" is a deployment decision.

---

## 109.4 Edges and failure modes

**A wheel that imports is not necessarily a wheel that installs.**
Real installers validate more than the listing wrote: consistent `RECORD`, normalised names (PEP 503: case and `-`/`_` fold together), and tag syntax. Hand-built wheels are for understanding and for tests; production wheels come from build backends (111), and the difference is exactly the validation you did not know existed.

**Two distributions can own one import name, and the loser is silent.**
Install `foo` from two differently-named projects and the second extraction overwrites the first's module while both dist-infos remain. `importlib.metadata` then reports both; imports serve one. The `packages_distributions()` mapping is the diagnostic; the disease is usually a rename (`PIL`/`Pillow`) or a hostile package (116).

**`RECORD` is trusted, not enforced.**
Nothing re-hashes at import time, integrity checking is an *audit* operation (`pip check` does not even do it; `pip install --require-hashes` guards the download, not the disk). A mutated site-packages runs mutated code; the hash chain protects the supply line (114, 116), and host integrity is the OS's job.

**Metadata and reality can drift.**
`METADATA`'s dependency list is a claim compiled at build time; the code's actual imports are facts. Optional imports, vendored code, and conditional dependencies all produce drift in both directions, which is why resolvers (112) work on declared metadata and why "it resolved" and "it runs" are different certificates.

**Editable installs bend the model.**
`pip install -e` writes a dist-info whose RECORD points at a `.pth`/loader shim, not at your files; `dist.files` then describes the shim, uninstall leaves your tree alone, and hashes are meaningless. Correct behaviour, surprising introspection, and the reason editable-install bugs feel supernatural until you read the shim.

**`importlib.metadata` answers for the *path*, not for "the environment".**
Its view is `sys.path`-relative: activate a different venv, or insert paths (as the listing did), and the answers change accordingly. That is a feature, it is how the listing works offline, and a trap when tools cache metadata across environment switches.

**And `__pycache__` appears on first import, not at install.**
Installers may precompile (`pip` does by default); extraction-by-hand does not, so the first import also compiles (Chapter 54). The listing's timing subprocesses measure exactly that shape; production cold-start measurements should decide *which* shape they are measuring.

---

## 109.5 Connections

**Backward.**
How the extracted directory's module is *found* and loaded, finders, loaders, `sys.path`, `__pycache__`, is Deep G, this volume's inseparable sibling. Hashing is Deep P's territory used as a tool; zip files are Deep R's. The C-extension constraint that keeps extraction dominant is Deep M's `dlopen` reality.

**Forward.**
The tag grammar the filename carries, and how an installer chooses among candidate wheels, Chapter 110. The build contract that turns source into wheels, `pyproject.toml`, PEP 517/518/621, Chapter 111. Choosing versions before choosing wheels, Chapter 112. Where extraction lands and why environments isolate, Chapter 113. Pinning the whole graph by hash, PEP 751, Chapter 114. Wheels containing compiled code, tags at full complexity, Chapter 115. Publishing, indexes, and trust, Chapter 116, which closes the volume.

**Across books.**
**Book I**'s deployment chapter builds a `.deb` by hand for the same reason this chapter builds a wheel: the format demystified is the ecosystem demystified. Its `RECORD` is `md5sums`, its tags are `Architecture:` fields, its site-packages is `/usr/lib`, and the convergence is total because the problem, ship files, name compatibility, remember what you did, predates both languages.

---

## 109.6 Exercises

**1. Break the wheel, observe the failures.** Corrupt the listing's wheel four ways, wrong RECORD hash, misnamed dist-info, bad tag syntax, name mismatch with METADATA, and try each with a real installer. Catalogue which layer rejects which corruption.

**2. Case-fold collision.** Build `My-Package` and `my_package` wheels with different payloads; install both with a real installer and explain the outcome via PEP 503 normalisation.

**3. Zipapp the trade.** Package a 30-module tool as extracted files and as a single `.pyz` (`zipapp`); measure cold start of each and reconcile with §109.3a's per-archive cost.

**4. The entry-points bill.** Measure `entry_points()` in your own largest environment; then measure a plugin host you use (pytest counts) with `-X importtime` and attribute its share. Cache it and re-measure.

**5. Editable forensics.** Make an editable install of a toy project; read every file its dist-info contains, find the shim, and document the exact mechanism your tool used (`.pth`? finder? symlink?). Then explain one supernatural-seeming editable bug you have met.

**6. The design question.** `RECORD` hashes are written and almost never re-checked; a design that verified on import would catch on-disk tampering at the cost of hashing every file on every cold start (price it with §109.3a's numbers and Chapter 89's throughput tables). Argue both sides, then propose the middle design (verify-on-first-import-per-boot with an OS-cache witness?) and identify which existing layer, installer, `site`, import system, or OS, should own it, and why every candidate has declined so far.

---

## 109.7 Summary and cross-references

- **A wheel is a zip with a naming convention; installing is extraction onto `sys.path`; the installer's memory is one `dist-info` directory** (`METADATA` for resolvers, `WHEEL` for format, `RECORD` for uninstall and integrity). Built by hand, installed by hand, imported, and introspected, deterministically, on all three interpreters.
- **Content addressing is the trust anchor**: RECORD's sha256 verified by recomputation, the same digest discipline that secures lockfiles and uploads.
- **sdist runs a build on the user's machine; a wheel cannot run code at install**, the asymmetry that drives the whole ecosystem toward wheels, and this volume's later chapters.
- **Measured**: zipimport works at ~7.6x extracted first-import cost (602 vs 79 us); `distribution(name)` stays near-flat while **`entry_points()` scans every dist-info**, 13 to 32 ms across 10 to 500 distributions, plugin startup's tax, and the measured case for small environments.
- **The edges**: name normalisation collisions, metadata-vs-reality drift, editable installs' shims, path-relative metadata answers, and hashes that audit rather than enforce.

**Cross-references.** Finding and loading → Deep G. Tags → Chapter 110. The build contract → Chapter 111. Resolution → Chapter 112. Environments → Chapter 113. Lockfiles → Chapter 114. Compiled wheels → Chapter 115. Publishing and trust → Chapter 116. Hashes → Deep P. `dlopen` reality → Deep M.
