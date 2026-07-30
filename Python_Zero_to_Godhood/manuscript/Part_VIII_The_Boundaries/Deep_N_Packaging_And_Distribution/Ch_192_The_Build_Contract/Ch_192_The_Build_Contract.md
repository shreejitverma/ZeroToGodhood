# Chapter 111: The Build Contract

For its first two decades, building a Python package meant *executing* `setup.py`: metadata you could only learn by running arbitrary code, with whatever happened to be installed on the machine as the build's environment. Three PEPs replaced that with a contract, and this chapter does not describe the contract, it **implements** it. The listing contains a complete PEP 517 build backend in about thirty lines, drives it over a source tree whose `pyproject.toml` names it, and imports the result.

The three PEPs are three separations. **PEP 518**: the project *declares* its builder (`[build-system] requires`, `build-backend`), so the frontend can install the build tool into an isolated environment before importing it, builds stop depending on the machine. **PEP 517**: the builder is a module exposing hooks (`build_wheel`, `build_sdist`), so any frontend (pip, uv, `build`) can drive any backend (setuptools, hatchling, flit, or the listing's thirty lines). **PEP 621**: the metadata lives statically in `[project]`, and the listing shows it translating *mechanically* into Chapter 109's `METADATA`, `dependencies = ["tinypkg>=1.0"]` in, `Requires-Dist: tinypkg>=1.0` out, readable by resolvers without running anything.

The benchmark locates the time honestly: the mechanical floor of a pure build, read, hash, deflate, zip, is **25.7 ms for a thousand modules**. When an install takes seconds, the seconds are elsewhere: resolution, network, and environment setup, which is where the rest of the volume goes.

**This is a Deep N chapter.**
Chapter 109 owns the artifact this contract produces; Chapter 115 owns backends that compile. This chapter owns the contract itself: the tables, the hooks, and the isolation rule.

## Section index

- **111.1** The contract, implemented and driven
- **111.2** The model: three separations and one isolation rule
- **111.3** Measurement: where build time is not
- **111.4** Edges and failure modes
- **111.5** Connections
- **111.6** Exercises
- **111.7** Summary and cross-references

Listings live under `code/ch192/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 111.1 The contract, implemented and driven

```python
# code/ch192/l01_the_build_contract.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- PEP 518: the project declares its builder ---
  requires      : ['deepn_backend']
  build-backend : deepn_backend
  the frontend reads THIS before anything else, installs the
  requirements into an isolated environment (Chapter 113), and
  only then imports the named backend - so building never
  depends on what happens to be installed on the machine
--- PEP 517: the frontend calls the hook ---
  build_wheel() returned : contractpkg-2.0.0-py3-none-any.whl
    contractpkg-2.0.0.dist-info/METADATA
    contractpkg-2.0.0.dist-info/RECORD
    contractpkg-2.0.0.dist-info/WHEEL
    contractpkg-2.0.0.dist-info/entry_points.txt
    contractpkg.py
--- PEP 621: [project] became METADATA, mechanically ---
  Metadata-Version: 2.4
  Name: contractpkg
  Version: 2.0.0
  Summary: Built by the chapter's own backend
  Requires-Python: >=3.11
  Requires-Dist: tinypkg>=1.0
  static table in, static file out: resolvers (Chapter 112) can
  read dependencies WITHOUT running the build, which the old
  executable setup.py made impossible by construction
--- and the artifact is real: install and run it ---
  contractpkg.main() : 'built-by-contract'
```

**`tomllib` reading `[build-system]` is the whole of PEP 518 in two lines.**
The table names *what to install* (`requires`) and *what to import* (`build-backend`), and the frontend honours it before touching the project. That ordering is the fix for a decade of "install numpy before you can even *read* this package's metadata" bootstrap knots, and `tomllib` landing in the stdlib (3.11) made the config format parseable everywhere without a dependency, which is why this listing runs offline.

**The backend is thirty lines because the contract carries the complexity.**
`build_wheel(wheel_directory, ...)` receives a destination, reads `pyproject.toml`, writes Chapter 109's four-file wheel (reusing that chapter's `record_line` for the hashes, the volume's code composes like its concepts), and returns the filename. That *is* the interface; `build_sdist` deliberately raises as this chapter's exercise. Real backends layer discovery (which files belong?), configuration, C compilation (Chapter 115), and editable-install hooks on the same signatures, which is precisely what "contract" means: the frontend cannot tell the listing's backend from hatchling.

**The PEP 621 block is metadata with the execution removed.**
Every `[project]` key maps to a `METADATA` field by rule, not by code: `dependencies` to `Requires-Dist`, `requires-python` to `Requires-Python`, `[project.scripts]` to the `entry_points.txt` Chapter 109 introspected. Static in, static out, and the consequence is architectural: resolvers (Chapter 112) and indexes can know a package's dependencies *without building it*, impossible by construction when metadata was a `setup()` call's arguments.

**And the wheel installs and runs**, `'built-by-contract'`, closing the loop the way this volume insists on: every artifact demystified is an artifact executed.

---

## 111.2 The model: three separations and one isolation rule

**Frontend from backend (PEP 517).**
The frontend owns the user interaction, environment, and orchestration; the backend owns turning a source tree into artifacts. The optional hooks fill out the lifecycle, `prepare_metadata_for_build_wheel` (metadata without a full build, for resolvers), `build_editable` (PEP 660, the shims Chapter 109's edge met), and `get_requires_for_build_wheel` (dynamic build dependencies), but the two mandatory hooks are the contract's whole spine, and the listing proves the spine suffices.

**Declaration from execution (PEP 621).**
`[project]` is data. The escape hatch is explicit: a field listed in `dynamic = [...]` is deferred to the backend (version-from-git being the common case), and *only* those fields may vary from the table. The design principle is the volume's recurring one: **static where possible, executable only where declared**, the same principle that made wheels beat sdists (Chapter 109) and will make lockfiles auditable (Chapter 114).

**Build environment from user environment (PEP 518's isolation rule).**
The frontend installs `requires` into a *fresh, isolated* environment (Chapter 113's machinery) and runs the backend there. Consequences worth spelling out: the build cannot see the user's installed packages (goodbye "works because numpy happened to be there"); two projects can require conflicting *build* tools without conflict; and the build's determinism reduces to the determinism of resolving `requires`, which is why serious setups pin their build requirements too (Chapter 114's lockfiles reach into `[build-system]`).

**What the contract deliberately does not cover** completes the picture: no standard for *invoking* builds (that is the frontends' UX), none for compilers or toolchains (Chapter 115's per-backend reality), and none for publishing (Chapter 116). The contract is exactly one seam, source tree to artifacts, standardised, and its narrowness is why the whole competing ecosystem of backends could bloom behind one interface.

---

## 111.3 Measurement: where build time is not

**Methodology.** `code/ch192/bench_build_scaling.py`.
The listing's backend mechanics over synthetic trees of ~4 KB modules; `min` of 5; 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| modules | deflated | stored |
|---|---|---|
| 10 | 0.4 ms | 0.3 ms |
| 100 | 2.7 ms | 1.7 ms |
| 1,000 | 25.7 ms | 15.5 ms |

**The mechanical floor is milliseconds, and mostly compression.**
Read, sha256 (Chapter 109's RECORD), deflate, zip: linear in bytes, 25.7 ms for a thousand-module package, with the stored column showing the hash-and-zip floor beneath deflate. A pure-Python build is, mechanically, *nothing*, and the benchmark's role in the volume is elimination: when `pip install` of a pure package takes fifteen seconds, **none of them are here**. They are in resolution's exploration (Chapter 112), the network, and build-environment setup, an isolated env with `requires` installed is itself a small install, recursively, which is why frontends cache build environments and why uv's speed story is mostly Chapters 112 to 114, not this table.

**The table also prices a policy question**: wheels ship deflated; the ~40% time premium over stored buys smaller downloads, the right trade at index scale and a matter of indifference locally. Backends expose no knob because the trade is settled, one of many small decisions the contract's implementations have quietly standardised.

**Book I**'s build chapter measures the same shape with three more orders of magnitude: compilation dominates, linking is the zip step, and its conclusion mirrors this one, build *systems* (dependency discovery, caching, sandboxing) cost more than build *mechanics*, so that is where the engineering goes.

---

## 111.4 Edges and failure modes

**`setup.py` is not dead; it is demoted.**
setuptools remains a PEP 517 backend, and `setup.py` survives as *its configuration file* (increasingly replaced by `[project]`). What died is `python setup.py install` as a protocol: frontends now reach setuptools only through the hooks, and a repo whose README still says `setup.py install` is advertising its age, not an alternative.

**Missing `[build-system]` triggers the legacy fallback.**
A `pyproject.toml`-less (or table-less) tree gets the implied setuptools backend for compatibility. It works and it re-imports the old world's ambiguity, which build tool version? what does it see?, so the table is mandatory in practice even where optional in spec.

**Build isolation surprises the two extremes.**
Projects that *relied* on the ambient environment (a compiled dependency's headers, a plugin registering itself) break under isolation and need their needs declared in `requires`; CI setups that pre-install build tools for speed defeat isolation with `--no-build-isolation` and take back the determinism risk knowingly. Both are the rule working: the build sees what is declared, nothing else.

**`dynamic` is a scoped escape, not a loophole.**
Version-from-VCS is legitimate `dynamic = ["version"]`; computing *dependencies* dynamically resurrects the unreadable-metadata problem for exactly the field resolvers need most, and tools rightly treat it as a smell. Declare, and let the 1% that cannot, say so explicitly.

**The backend runs with the frontend's interpreter.**
Hooks execute under whatever Python the frontend chose, including 3.14t, where the *backend* inherits Deep L's world. Pure backends never notice; backends spawning compilers or threads should read Chapter 93's detection listing. (This chapter's backend verifying identically across the matrix is the base case.)

**And `entry_points.txt`'s cost was measured two chapters ago.**
`[project.scripts]` becomes the file Chapter 109's benchmark showed `entry_points()` scanning environment-wide. Ship entry points for real CLIs and plugins; resist decorative ones; the bill arrives at every process start in fat environments.

---

## 111.5 Connections

**Backward.**
The artifact grammar and `record_line` the backend reuses are Chapter 109; the tag it stamps (`py3-none-any`) is Chapter 110; `tomllib` is Deep P's parsing family in stdlib residence. The executable-config era this contract ended is part of Volume 6's 2.x history.

**Forward.**
The resolver that reads `Requires-Dist` without building, Chapter 112. The isolated environments builds run in, Chapter 113. Pinning `requires` for reproducible builds, Chapter 114. Backends that compile, and the hooks under `cibuildwheel`, Chapter 115. What happens to the built artifacts, Chapter 116.

**Across books.**
PEP 517 is Python discovering the build-system boundary CMake standardised for C++ (configure/generate/build as interface, toolchains as implementations), and **Book I**'s chapter on build systems tells the same story with `FetchContent` where `requires` sits and generator expressions where `dynamic` sits. Both ecosystems learned the same lesson at the same seam: standardise the *interface* to building, never the builder.

---

## 111.6 Exercises

**1. Drive it with a real frontend.** Package the listing's backend properly (a `deepn_backend` module with a wheel of its own), point a real `[build-system]` at it, and run `python -m build`. Diff the artifacts against the listing's.

**2. Add the metadata hook.** Implement `prepare_metadata_for_build_wheel` and demonstrate a frontend obtaining `Requires-Dist` without a wheel ever being built. Measure the saving on the 1,000-module tree.

**3. Implement `build_sdist`.** Tar the source tree with `PKG-INFO`, then close the loop: build the wheel *from your sdist* and verify it matches the tree-built wheel byte-for-byte (or explain each difference).

**4. Break isolation, observe, repent.** Make a package whose build imports a library it does not declare; show it building with `--no-build-isolation` and failing without; fix the declaration. Keep the failure message as documentation.

**5. Price a real backend.** Time hatchling or setuptools building the 1,000-module tree against §111.3's floor; attribute the difference (discovery? config? plugins?) with a profiler. Report the ratio of ceremony to mechanics.

**6. The design question.** PEP 517 hooks are Python functions in-process, not a CLI protocol: a frontend must *run Python* to build Python. Argue the choice against a subprocess/JSON protocol (language-independent, sandboxable, crash-isolated): what in-process buys (no serialisation of config, shared interpreter cost, trivial backend authorship, thirty lines, as proven), what it costs (backend crashes take the frontend, sandboxing needs subprocesses anyway, Chapter 116's supply-chain lens), and which side history has drifted toward, given that every serious frontend now runs hooks in a subprocess regardless.

---

## 111.7 Summary and cross-references

- **Three separations**: PEP 518 declares the builder (`[build-system]`), PEP 517 makes building an interface (`build_wheel`/`build_sdist` hooks), PEP 621 makes metadata static data (`[project]`). The listing implements the full contract in ~30 lines and installs its own output, identically across the matrix.
- **Static where possible, executable only where declared**: `[project]` maps mechanically to `METADATA` (resolvers read dependencies without running builds); `dynamic` scopes the exceptions; the executable-`setup.py` era is a compatibility fallback, not a peer.
- **Isolation is the rule**: `requires` installs into a fresh environment, so builds see declarations, not machines, determinism bought at the price of declaring honestly, and pinned via Chapter 114 when it matters.
- **Measured**: the mechanical floor is **25.7 ms per thousand modules** (mostly deflate; 15.5 stored). Slow installs are never the build mechanics; they are resolution, network, and environment setup, the volume's next chapters.
- **Edges**: the legacy fallback re-imports ambiguity; isolation breaks the undeclaring and is defeated knowingly in CI; backends inherit the frontend's interpreter, 3.14t included; entry points bill at every startup (Chapter 109's scan).

**Cross-references.** The artifact and RECORD → Chapter 109. Tags → Chapter 110. Resolution → Chapter 112. Environments and isolation machinery → Chapter 113. Pinning builds → Chapter 114. Compiling backends → Chapter 115. Publishing → Chapter 116. `tomllib` → Deep P.
