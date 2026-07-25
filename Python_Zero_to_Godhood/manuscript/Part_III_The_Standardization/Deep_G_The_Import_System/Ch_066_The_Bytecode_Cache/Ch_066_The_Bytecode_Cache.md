# Chapter 66: The Bytecode Cache

The first time a Python module is imported, its source is *compiled*, parsed into an AST, then emitted as
bytecode, and that compilation is not cheap: for a chunky module it takes **~1.4 ms**, versus **~30 us** to load
the *already-compiled* bytecode, a **48x** difference. If Python recompiled every module on every run, startup
would be dominated by parsing source it just parsed last time. It does not: after the first compile, CPython
writes the bytecode to a `.pyc` file under `__pycache__`, and every later import in a fresh process *loads the
`.pyc` and skips compilation*, provided the source has not changed. The `.pyc` cache is why a large application's
second startup is faster than its first, and why deleting `__pycache__` makes the next run briefly slower.

This chapter continues **Deep G** with the bytecode cache: what a `.pyc` contains, how its freshness is checked,
and the measured cost of compilation it eliminates. It connects Chapter 63's "the body runs once" (per process)
with the observation that even the *compilation* is cached across processes.

## Section index

- **66.1** What the cache stores
- **66.2** Freshness and invalidation
- **66.3** Measurement: compile vs load
- **66.4** Edges and failure modes
- **66.5** Connections
- **66.6** Exercises
- **66.7** Summary and cross-references

Listings live under `code/ch066/` and are re-executed by `make verify` on both interpreters.

---

## 66.1 What the cache stores

```python
# code/ch066/l01_bytecode_cache.py
```

Verified output (CPython 3.13.5, identical on 3.14.6):

```text
--- compile source to a code object (what the first import does) ---
  compiled a code object : code
--- marshal the code object (what gets written into the .pyc body) ---
  marshaled bytecode     : 246 bytes
--- load it back and run it (what a later import does) ---
  RESULT from cached code: 5
  round-trip reproduces the code exactly: True
--- the cache location and freshness check ---
  cache dir is __pycache__ : True
  cache file ends in .pyc  : True
  a .pyc is valid only while its source is unchanged (mtime+size or hash)
  the version magic number rejects a .pyc from a different Python
```

The listing walks the two halves of the cache mechanism. The **first import** compiles the source into a *code
object* (`compile(source, ...)`), the parse-and-emit-bytecode step. That code object is then **marshaled**
(`marshal.dumps`) into bytes, marshal is CPython's fast serialization for code objects and other built-in types,
and those bytes are the body of the `.pyc`. A **later import** does the reverse: `marshal.loads` reconstructs the
code object from the cached bytes, and executing it reproduces the module exactly (`RESULT` is 5, the round-trip
is faithful). So a `.pyc` is not magic; it is the marshaled code object plus a small header, and loading it is
just `marshal.loads`, which §66.3 shows is far cheaper than compiling.

The cache lives in a **`__pycache__`** directory beside the source, with a filename tagging the interpreter
version (`mod.cpython-313.pyc`), so that multiple Python versions can coexist without clobbering each other's
caches. The listing reports the version-independent structure (the `__pycache__` directory, the `.pyc`
extension); the version tag itself differs by interpreter, which is the point of tagging.

---

## 66.2 Freshness and invalidation

A cache is only useful if it is *invalidated correctly*, using stale bytecode after the source changes would run
old code, a maddening bug. A `.pyc` header carries two things that guard against this.

First, a **magic number** identifying the bytecode format of the interpreter that wrote it. Bytecode is *not*
stable across Python versions (opcodes are added, renumbered, and specialized, Chapters 17 and 50), so a `.pyc`
from 3.12 is meaningless to 3.13. The magic number lets the loader reject a `.pyc` from a different Python and
recompile, which is also why the filename carries the version tag.

Second, a **source-freshness check**, in one of two modes. The default is **timestamp-based**: the header stores
the source file's modification time and size, and the loader recompiles if either differs from the current
source. This is fast (a `stat`) but depends on reliable mtimes, which some build systems and containers do not
provide. The alternative (PEP 552, 3.7+) is **hash-based**: the header stores a hash of the source, and the
loader recompiles if the hash differs, slower to check but reproducible and independent of timestamps, which
matters for deterministic builds. Either way, **edit the source and the `.pyc` is invalidated and recompiled**;
the cache never serves bytecode for source it no longer matches.

The consequence for practice: **you never manage `.pyc` files by hand.** They are regenerated automatically when
stale, safe to delete (the next import recompiles), and should generally not be committed to version control
(they are build artifacts, and `.gitignore` should exclude `__pycache__`). To *precompile* for deployment,
`python -m compileall` builds all the `.pyc` files ahead of time so production does not pay first-import
compilation.

---

## 66.3 Measurement: compile vs load

**Methodology.** `code/ch066/bench_compile_vs_load.py`. `compile(source, ...)` of a chunky module's source versus
`marshal.loads` of the already-compiled code object (what loading a `.pyc` does after its header check). `min`
per call; ratio relative to the load. CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| operation | min per call | ratio |
|---|---|---|
| `marshal.loads` (load `.pyc`) | **29.5 us** | 1.00x |
| `compile` source | **1425 us** | **48x** |

Compiling the module's source takes **1425 us**, parsing the text into an AST and emitting bytecode, while
loading the marshaled bytecode takes **29.5 us**, **48x** less. That 48x is what the `.pyc` cache saves on every
import after the first (and after any source change). For a single small module it is microseconds; across a
large application's hundreds of modules it is the difference between a cold start that recompiles everything and
a warm start that loads cached bytecode, often hundreds of milliseconds.

The rule: **let the bytecode cache work, and precompile for production.** In development the cache is automatic,
edit, run, and only changed modules recompile. For deployment, run `python -m compileall` (or ship the `.pyc`
files) so the first request after a deploy does not pay compilation; this matters most for short-lived processes
(CLIs, serverless cold starts, Chapter 65) where every startup would otherwise recompile. Do not fight the cache
(deleting `__pycache__` in a loop, disabling it with `-B` without reason) and do not commit `.pyc` files, they
are per-version build artifacts. The compilation cost is real (48x a load), which is exactly why the cache exists
and why you should let it, and `compileall`, do their job.

---

## 66.4 Edges and failure modes

**Recompiling on every run (no cache).** §66.3. Running with `-B` (or a read-only directory where `.pyc` cannot
be written) forces recompilation each start, paying the 48x every time. Ensure the cache directory is writable,
or precompile.

**Stale bytecode from unreliable mtimes.** §66.2. Timestamp-based invalidation can miss a change if a build system
resets mtimes (or two files share a timestamp). For reproducible builds and containers, use hash-based `.pyc`
(PEP 552, via `compileall --invalidation-mode`).

**Committing `.pyc` files.** They are per-interpreter-version build artifacts; committing them causes churn and
cross-version breakage. Exclude `__pycache__` in `.gitignore`.

**Editing or trusting a `.pyc` as source of truth.** A `.pyc` is generated *from* source; editing it (or shipping
only `.pyc` to hide source) is fragile, the magic number ties it to one interpreter version, and it is not a
security boundary (bytecode is trivially decompiled). Treat source as canonical.

**Assuming `.pyc` speeds execution.** The cache speeds *loading* (skips compilation); it does *not* make the code
*run* faster, the bytecode executed is identical whether compiled fresh or loaded. It is a startup optimization,
not a runtime one.

**Cross-version cache confusion.** A `__pycache__` populated by one Python version is ignored (by magic number)
by another, which recompiles into its own version-tagged `.pyc`. This is correct but can surprise you with
multiple `.pyc` files per module; it is not a bug.

---

## 66.5 Connections

**Backward.** The compilation this caches, source to code object, is the front of the pipeline whose *back* (the
bytecode `dis` shows) is Chapter 50. The code object being marshaled is the `__code__` of Chapters 5 and 49. The
"body runs once per process" fact this complements (compilation cached *across* processes) is Chapter 63.

**Forward.** The compiler pipeline (tokenizer, parser, AST, bytecode compiler) is a **Deep J** internals topic.
Precompilation for deployment connects to packaging (Deep N, wheels can ship `.pyc`). Startup optimization
(lazy imports plus precompiled bytecode) is Chapter 65's territory.

**Across books.** The bytecode cache is why Book II's tools and services start quickly for **Book III** after the
first run. A **Book III** container image runs `compileall` at build time so the shipped image has warm `.pyc`
files and the service starts without recompiling on the first request, and CLIs benefit on every invocation. The
§66.3 compile cost is the reason production images precompile. **Deep U** owns the build/deploy seam; **Deep J**
owns the compiler.

---

## 66.6 Exercises

**1. See the round trip.** Compile a small module's source to a code object, `marshal.dumps` and `marshal.loads`
it, and `exec` the result. Confirm it reproduces the module. Explain what a `.pyc` stores beyond the marshaled
code.

**2. Measure the saving.** Run §66.3's benchmark and confirm compiling source is far costlier than loading
marshaled bytecode. Scale the module up and show the gap grows with source size. Explain why the cache targets
compilation.

**3. Invalidate the cache.** Import a module (creating its `.pyc`), edit the source, and import again in a fresh
process; confirm it recompiles. Explain the mtime/size (or hash) freshness check.

**4. Precompile.** Run `python -m compileall` on a package and inspect the `__pycache__` directories. Explain how
this helps a production/cold-start scenario and why the version tag is in the filename.

**5. The design question.** CPython caches compiled bytecode across processes but ties each `.pyc` to an
interpreter version and a source-freshness check. Argue why both guards are necessary. Your answer must use the
§66.3 measurement, explain the magic number and mtime/hash checks, and say why `.pyc` files should not be
committed or hand-edited.

---

## 66.7 Summary and cross-references

- The **first import compiles** source to a code object; CPython **marshals** it into a **`.pyc`** under
  **`__pycache__`**, and later imports (fresh processes) **load the `.pyc` and skip compilation** when the source
  is unchanged.
- A `.pyc` header has a **version magic number** (bytecode is not stable across versions) and a **source-freshness
  check** (timestamp+size by default, or hash-based per PEP 552).
- **Measured:** loading marshaled bytecode is **48x** cheaper than compiling source (29.5 us vs 1425 us); the
  cache saves this on every import after the first.
- **Let the cache work; precompile for production** (`python -m compileall`). The cache speeds *loading*, not
  execution. Never commit or hand-edit `.pyc` files.

**Cross-references.** Bytecode and `dis` → Chapter 50. Code objects → Chapters 5, 49. Import caching (per process)
→ Chapter 63. Startup and lazy imports → Chapter 65. The compiler pipeline → Deep J. Packaging/precompilation →
Deep N. The build/deploy seam → Deep U.
