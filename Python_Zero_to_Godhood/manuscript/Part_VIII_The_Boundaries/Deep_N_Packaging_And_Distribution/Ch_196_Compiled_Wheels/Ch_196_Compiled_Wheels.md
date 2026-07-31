# Chapter 115: Compiled Wheels

Chapter 110 decoded the hard tags; this chapter compiles against them. The listing builds **real C extensions** with the system compiler against each verification interpreter's own headers, and the matrix itself performs the chapter: `EXT_SUFFIX` prints `.cpython-313-darwin.so`, `-314`, and **`-314t`**, the wheel-tag ABI applied per file; a module that *declares* free-threading support (`Py_mod_gil = Py_MOD_GIL_NOT_USED`, multi-phase init) loads on 3.14t **with the GIL still off**, while a legacy module without the slot **re-enables the GIL for the whole process**, caught in the act with its `RuntimeWarning`; and a `Py_LIMITED_API` compile succeeds on both GIL builds and is **refused outright by the free-threaded headers**, Chapter 110's REJECT row enforced at compile time instead of install time.

The benchmark then prices the native path end to end: compiling the twelve-line module costs ~60 ms (limited API no slower to *make*, only narrower in what it may call); importing the `.so` costs 218 us against the `.py`'s 76 (a `dlopen` on top of the finder walk); and the call itself, 13.4 ns against 14.7 for an identical Python function, is *cheaper than not compiling*. The expensive part of native code is never calling it; it is **building, tagging, and shipping it compatibly**, which is why the build matrix, `manylinux`, and abi3 exist.

**This is a Deep N chapter.**
Deep M owns writing extensions and the C-API; Chapter 82 owns the ABI and limited API as mechanisms; Chapter 110 owns the tag grammar. This chapter owns the *distribution* problem compiled code creates, and the three tools that tame it: declared slots, the stable ABI, and matrix automation.

## Section index

- **115.1** The matrix performs the chapter
- **115.2** The model: suffixes, slots, floors, and the matrix
- **115.3** Measurement: build, load, call
- **115.4** Edges and failure modes
- **115.5** Connections
- **115.6** Exercises
- **115.7** Summary and cross-references

Listings live under `code/ch196/` and are re-executed by `make verify` on the full matrix; they require a C compiler, and their per-build differences are the subject.

---

## 115.1 The matrix performs the chapter

```python
# code/ch196/l01_compiled_for_this_abi.py
```

Each matrix divergence is quoted after this block, which is Verified output (CPython 3.13.5):

```text
--- the ABI in the filename, at module level ---
  EXT_SUFFIX : .cpython-313-darwin.so
  the suffix is the wheel tag's abi field applied per FILE, so one
  directory can hold builds for several interpreters side by side
--- a well-behaved citizen: declares its GIL position ---
  compiled and imported : True, answer() = 43
  import warned          : False
  GIL enabled afterwards : True
  Py_mod_gil = Py_MOD_GIL_NOT_USED (multi-phase init): on the
  free-threaded build this module loads WITHOUT re-arming the
  GIL; on GIL builds the slot is an inert declaration
--- a legacy module: no declaration ---
  compiled and imported : True, answer() = 42
  import warned          : False
  GIL enabled afterwards : True
  on 3.14t this import RE-ENABLES the GIL for the whole
  process (with a RuntimeWarning): one undeclared wheel and
  Chapter 93's scaling is gone - which is why cp314t wheels
  are a separate, opt-in universe (Chapter 110)
--- the limited API, tried against these headers ---
  Py_LIMITED_API compile succeeded : True
```

On 3.14 only the suffix and wheel-name lines change (`cp314`). On the free-threaded build, five lines change, and each is a mechanism. Verified output (CPython 3.14t):

```text
  EXT_SUFFIX : .cpython-314t-darwin.so
```

the declared module's `GIL enabled afterwards : False`; the legacy module's `import warned : True` and `GIL enabled afterwards : True` (it re-armed the lock); and `Py_LIMITED_API compile succeeded : False`.

**The declared/legacy pair is Chapter 93's deployment edge, executed.**
Both modules compile and both import everywhere. On 3.14t, the one with the `Py_mod_gil` slot loads into a still-free-threaded process; the one without it flips `sys._is_gil_enabled()` to `True` *for the whole process*, with a warning as the only witness. The listing imports the declared module first deliberately, order matters, because the re-arming is one-way. This is the entire cp314t wheel-ecosystem story in eight printed lines: compatibility is not "does it import" but "does it import *without demoting the build*".

**And the limited-API refusal is the abi3 boundary from the compiler's side.**
Chapter 110's selector rejected `cp311-abi3` wheels on 3.14t at install time; here the *headers* reject the `#define` at compile time, `#error` before any object file exists. Same boundary, enforced at both ends, and the two listings verifying against each other across chapters is the volume's machinery composing.

---

## 115.2 The model: suffixes, slots, floors, and the matrix

**`EXT_SUFFIX` is the tag system at file granularity.**
The import system (Deep G) probes for `name` + `EXT_SUFFIX` before `name.py`, so an extension built for another ABI is simply *not found* rather than wrongly loaded, the same cheap-rejection design as Chapter 110's filenames, one directory level down. (The historic crash mode, loading a wrong-ABI `.so` on Windows or via renamed files, is what the suffix discipline retired.)

**Multi-phase init and its slots are the extension's metadata channel.**
`PyModuleDef_Init` + slots (PEP 489) is how a module *declares* properties the runtime must know before running it: per-interpreter readiness (Chapter 98's subinterpreter gate) and, since 3.13, `Py_mod_gil`. The declaration is compiled into the artifact, which is why the fix for the legacy module is a rebuild, not a flag, and why the cp314t universe's growth rate is set by upstream release cadences.

**Platform floors come from the build, not the source.**
The macOS deployment target, glibc version linked against, and CPU baseline are properties of the *toolchain invocation*, and they become the wheel's platform tag (Chapter 110's floors). `manylinux` is this idea institutionalised: build inside an old-glibc container so the floor is low, audit the result (`auditwheel`) so the claim is honest, and vendor any external libraries into the wheel so the claim is *complete*. macOS's `delocate` plays the same role; both are why a compiled wheel is bigger than its `.so`.

**The matrix is the product of independent axes, and automation is how it ships.**
Interpreter minors x GIL flavours x OS x architectures: a real project's release is dozens of builds, each on the right toolchain with the right floor. `cibuildwheel`-style automation enumerates the matrix in CI; **abi3 collapses the minor-version axis** (one build from the floor upward, GIL builds only, for now); and pure Python collapses everything, which is why "do we actually need the C?" (Chapter 92's escape discipline, run in reverse) is a *distribution* question as much as a performance one.

---

## 115.3 Measurement: build, load, call

**Methodology.** `code/ch196/bench_extension_costs.py`.
`min` of 5 (9 for import subprocesses); 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| stage | cost |
|---|---|
| compile, full ABI | 61.4 ms |
| compile, limited API | 52.2 ms |
| first import, `.py` module | 76 us |
| first import, `.so` module | 218 us |
| call, Python function | 14.7 ns |
| call, C extension function | **13.4 ns** |

**Each row locates a different chapter's cost.**
Compilation: toy-sized here, hours at matrix scale, and the limited API costs nothing extra to *build* (its price is API surface and some runtime speed, Chapter 82). Loading: the `.so` pays a `dlopen` plus relocation on top of Chapter 109's finder walk, ~3x the `.py`, once per process. Calling: *cheaper than Python*, no frame, no bytecode, `METH_NOARGS` straight to C, Chapter 76's boundary certified on an artifact this volume built from source in front of the reader.

**The table's conclusion is the chapter's thesis inverted.**
Everything cheap is at runtime; everything expensive is upstream of it, in building and shipping. That asymmetry is why the ecosystem tolerates the tag matrix's complexity: the payoff (native speed, free at call time) is permanent, and the cost (the matrix) is paid once per release by machines. **Book I** lives entirely on the left side of this table and its build chapters are correspondingly this chapter's longest cousins: same compilers, same floors, same audit tools, with Python's tags swapped for SONAMEs and triplets.

---

## 115.4 Edges and failure modes

**One undeclared import demotes the whole process.** §115.1.
On 3.14t, the *first* legacy extension re-arms the GIL for everyone, and later declarations cannot undo it. Deployment on the t-build therefore audits transitively: `sys._is_gil_enabled()` *after* full import of the application (Chapter 93's check), not per package.

**The slot declares intent; it does not create safety.**
`Py_MOD_GIL_NOT_USED` is a promise that the module's C code follows Chapter 96's rules (no unlocked global state, refcount discipline per Chapter 94). A false declaration trades the warning for data races. The declaration migrates the *audit obligation* into the extension's authorship, where Deep M's chapters take over.

**abi3 narrows twice.**
API: only the limited API's functions exist under `Py_LIMITED_API`, no fast-path macros, no internal structs (Chapter 82's list). And build-flavour: no free-threaded target at all, today. Projects choose per module: hot inner modules on the full ABI (rebuilt per minor), cold glue on abi3 (built once), a split the tag system happily expresses.

**`-undefined dynamic_lookup` is the macOS spelling of a real contract.**
Extensions resolve interpreter symbols at load time from the hosting process; Linux spells it differently, Windows links against `pythonXY.dll` explicitly. Hand-rolled build commands (like the listing's) encode platform lore that build backends exist to own, the listing compiles by hand to *show* the mechanism, and §115.2's tooling paragraph is why nobody ships this way.

**Vendored libraries are part of the ABI claim.**
A wheel whose `.so` links a system `libssl` has an undeclared dependency the tags cannot express; `auditwheel`/`delocate` vendor and rewrite install names precisely so the platform tag tells the whole truth. The failure mode, works-on-builder, `ImportError: dlopen ... not found` elsewhere, is always a vendoring gap.

**And cross-compilation inherits every edge at once.**
Building `arm64` wheels on `x86_64` CI (or vice versa) means the *running* interpreter's `EXT_SUFFIX` and `sysconfig` describe the wrong target; backends grow `_PYTHON_HOST_PLATFORM`-style overrides, and the tag on the filename must describe the *artifact*, not the builder. When a wheel's tag and its contents disagree, this is where it happened.

---

## 115.5 Connections

**Backward.**
The tag grammar and the abi3 selector this chapter's compiles enforce, Chapter 110. The ABI mechanics and limited-API trade, Chapter 82. The GIL re-arming edge in deployment terms, Chapter 93; the refcount and locking rules a truthful `Py_mod_gil` promises, Chapters 94 and 96. The finder probe order that makes suffixes safe, Deep G; writing the C itself, Deep M.

**Forward.**
Chapter 116 closes the volume with where these artifacts go: the index's role in serving a dozen wheels per release, and the trust chain (hashes from Chapter 114, provenance, and the supply-chain reality that compiled artifacts are the hardest to audit and thus lean hardest on reproducible builds).

**Across books.**
This chapter is the seam where the two books share a toolchain: the same `cc`, the same deployment floors, the same audit tools. **Book I**'s shared-library chapter and this one can be read as one text with two vocabularies, and the shared system's release pipeline literally interleaves them, C++ builds emitting `.so`s that Python wheels then vendor.

---

## 115.6 Exercises

**1. Reproduce the demotion.** On 3.14t, import the declared and legacy modules in both orders; capture `sys._is_gil_enabled()` after each step and the warning text. Write the three-line deployment check your findings dictate.

**2. Split a package.** Take (or invent) a two-module extension package; ship the hot module full-ABI and the glue module abi3. Enumerate the wheels one release needs for {3.12, 3.13, 3.14} x {macOS arm64, manylinux x86_64}, with and without the split.

**3. Audit a vendored wheel.** Unzip a real numpy or cryptography wheel; list the vendored libraries and the install-name rewrites (`otool -L` / `readelf -d`). Map each to the edge it prevents.

**4. Break a floor knowingly.** Build the listing's module with a deployment target newer than your OS claims, tag it honestly, and document the installer's rejection; then tag it dishonestly and document the runtime failure. State which failure you would rather debug.

**5. Measure a real matrix.** Clone a small compiled project with cibuildwheel config; count its release artifacts and total CI minutes from a recent run. Compute the abi3 counterfactual.

**6. The design question.** `Py_mod_gil` is an opt-in *declaration* with a warning fallback; the alternative was refusing undeclared modules on 3.14t outright (as subinterpreters do, Chapter 98). Argue both sides with this volume's evidence: the ecosystem-migration argument for the warning (Chapter 93's bottleneck), the silent-demotion cost the listing demonstrated, and the precedent of the suffix system (hard incompatibility, zero migrations ever needed). Then decide what 3.16 should do, and what evidence would change your mind.

---

## 115.7 Summary and cross-references

- **The matrix performs the chapter**: `EXT_SUFFIX` per build (`.cpython-313/-314/-314t`), the `Py_mod_gil`-declared module keeping 3.14t free-threaded while the legacy module **re-arms the GIL process-wide** (warning as witness), and `Py_LIMITED_API` **refused by the free-threaded headers**, Chapter 110's boundary enforced at compile time.
- **Multi-phase slots are the artifact's metadata channel** (per-interpreter readiness, GIL position), compiled in, fixable only by rebuild; floors (deployment targets, glibc) come from the toolchain and become platform tags; `manylinux`/`auditwheel`/`delocate` make the claims honest and complete by vendoring.
- **Priced**: compile ~60 ms toy-scale (matrix scale is the real bill; abi3 collapses the minor axis, automation enumerates the rest); `.so` first import 218 us vs 76 (`dlopen`); and the call **13.4 ns vs 14.7**, cheaper than not compiling, everything expensive is upstream of runtime.
- **Edges**: one undeclared import demotes the process (audit after full import); false declarations trade warnings for races; abi3 narrows API and flavour; vendoring gaps and cross-compilation are where tags learn to lie.

**Cross-references.** Tags and the selector → Chapter 110. ABI and limited API → Chapter 82. Deployment detection → Chapter 93. The promises behind `Py_mod_gil` → Chapters 94, 96. Finder probing → Deep G. Writing extensions → Deep M. The index and trust → Chapter 116.
