# Canonical Structure — *Python Zero to Godhood* (Book II)

**Status:** Stage B proposal. Supersedes `00_Preface.md`'s TOC, `MASTER_COVERAGE_MATRIX.md`'s
volume map, the root-draft filename numbering, the internal `# Chapter NN` numbering, and the
`# Phase XIV–XXV` groupings. Those five maps are rewritten as pointers to this file.

**Spine:** Python's complete evolutionary history, 1989 to the current release.
**Terminal release:** CPython 3.14. **Verification interpreters:** 3.13.5 and 3.14.6 (dual-target).

---

## The two-track rule (binding; amends STYLE.md §7)

Every topic has exactly one **Deep Volume** that owns it and teaches it completely, once.
Every **Timeline Volume** is narrative and owns no mechanism.

> A release chapter may **use** a mechanism in one paragraph and must **cross-reference** its
> owning chapter. It may not **derive** it. If a release chapter needs three pages to explain how
> something works, that mechanism belongs in a Deep Volume and the release chapter is over-reaching.

Deep Volumes are **interleaved**, not appended: each sits at the point in the timeline where its
mechanism first becomes load-bearing, so a front-to-back reader always meets the mechanism before
the releases that depend on it.

## The anti-changelog rule (binding)

Every release chapter opens with **the constraint the release was operating under** — something
true of the world in that window that the core developers could not change. Every section must be
an answer to that constraint.

A change that does not answer the constraint does **not** get forced into the chapter. It goes to
its owning Deep Volume, and the release chapter carries a one-line *"also landed in 3.x"* note.
This is the escape valve that prevents the Ch 8 §8.3 / Ch 16 §16.3 failure from recurring.

## Naming convention (governs chapters that do not yet exist)

```
Part_NN_<Part_Name>/
  Vol_NN_<Volume_Name>/                  timeline volume
  Deep_NN_<Topic_Name>/                  deep volume
    Ch_NNN_<Chapter_Title>/
      Ch_NNN_<Chapter_Title>.md          source of truth
      Ch_NNN_<Chapter_Title>.tex         generated, never hand-edited
      _archive/                          provenance for merged sources
```

Chapter numbers are **global and three-digit**, assigned once and never reused. Volume membership
may change during editing; chapter numbers may not. This is the fix for the five-map problem: the
number is the identity, the path is just where it currently lives.

---

## Part I — Origins (1989–1995)

**Thesis:** Python's earliest decisions — objects all the way down, exceptions as control flow,
indentation as syntax — were made before there was a community to argue with, and they are still
load-bearing.

| Vol | Title | Range | Ch | Boundary rationale |
|---|---|---|---|---|
| 1 | Before Python | ABC → Dec 1989 | 4 | Ends where the prototype becomes a language |
| 2 | The 1.x Language | 0.9.0 – 1.5.2 | 6 | Ends at the last pre-licence-rupture release |
| **Deep A** | **The Object Model** | — | 9 | Placed after 1.x: `PyObject` is the oldest invariant |
| **Deep B** | **Memory: Allocator and GC** | — | 7 | Follows the object model; needs refcounting first |

## Part II — The 2.x Ascent (1995–2010)

**Thesis:** Python became an industrial language by absorbing features it had rejected, and the
2.x line is the record of which rejections were reversed and why.

| Vol | Title | Range | Ch | Boundary rationale |
|---|---|---|---|---|
| 3 | The Licence Rupture and 2.0 | 1.6 – 2.0 | 5 | CNRI/BeOpen/PSF is one story with 2.0's release |
| 4 | Unification | 2.1 – 2.3 | 7 | Type/class unification is the era's single argument |
| **Deep C** | **Types, Descriptors, Metaclasses** | — | 8 | Immediately after 2.2 makes it necessary |
| 5 | Syntax for Control | 2.4 – 2.6 | 7 | Decorators and `with` are one idea: delegated control |
| 6 | The 2.7 Twilight | 2.7 – EOL 2020 | 5 | Linear, not parallel: closes 2.x before 3.0 opens |

## Part III — The Break (2008–2012)

**Thesis:** Python 3 was a bet that a decade of migration pain was cheaper than carrying the
text/bytes confusion forever, and the bet's terms are visible in every release since.

| Vol | Title | Range | Ch | Boundary rationale |
|---|---|---|---|---|
| 7 | The Schism | 3.0 | 5 | 3.0 alone; it did enough |
| **Deep D** | **Text, Bytes, Encodings** | — | 7 | The break's actual subject |
| 8 | Consolidation | 3.1 – 3.2 | 5 | Two quiet releases, one through-line: making 3.x usable |
| **Deep E** | **Concurrency I: GIL, Threads, Processes** | — | 8 | Follows the 3.2 GIL rewrite |

## Part IV — Iteration and Async (2012–2015)

**Thesis:** `asyncio` was not designed; it was discovered, by following generators to their
conclusion across four releases.

| Vol | Title | Range | Ch | Boundary rationale |
|---|---|---|---|---|
| 9 | Delegation | 3.3 | 5 | `yield from` + PEP 393 + namespace packages |
| **Deep F** | **Iteration, Generators, Coroutines** | — | 7 | The mechanism `yield from` completes |
| **Deep G** | **The Import System** | — | 6 | Follows 3.3's namespace packages and `importlib` |
| 10 | Provisional | 3.4 | 5 | `asyncio` shipped provisional; that is the story |
| 11 | Native Syntax | 3.5 | 5 | `async`/`await` + `typing` both land |
| **Deep H** | **Concurrency II: asyncio and Structured Concurrency** | — | 8 | Needs both generators and native syntax first |

## Part V — Ergonomics and Typing (2016–2021)

**Thesis:** Once the runtime stabilised, the arguments moved to the surface: what code should
look like, and whether a checker should be allowed to have opinions about it.

| Vol | Title | Range | Ch | Boundary rationale |
|---|---|---|---|---|
| 12 | Expression | 3.6 – 3.7 | 7 | f-strings and dataclasses: declaring intent, not steps |
| **Deep I** | **The Type System** | — | 10 | After 3.5 introduced it, before 3.8 expands it |
| 13 | Binding and Debt | 3.8 – 3.9 | 7 | 3.9 pays down what 3.5's typing and the LL(1) parser cost |
| 14 | Structure | 3.10 | 5 | Pattern matching alone; the PEG parser made it possible |

## Part VI — Performance (2022–2023)

**Thesis:** CPython got fast by giving up on being simple, and every 3.11–3.12 change is a
specific trade of interpreter complexity for cycles.

| Vol | Title | Range | Ch | Boundary rationale |
|---|---|---|---|---|
| 15 | The Specializing Interpreter | 3.11 | 6 | Performance work; exception groups split out |
| 16 | Scopes and Observation | 3.12 | 7 | PEP 695, per-interpreter GIL, `sys.monitoring` |
| **Deep J** | **The Interpreter: ceval, Bytecode, JIT** | — | 9 | After the specializer gives it something to explain |
| **Deep K** | **Performance Engineering** | — | 8 | Profiling, benchmarking, measurement discipline |

## Part VII — The Concurrency Reckoning (2024– )

**Thesis:** The GIL's removal is the largest change in CPython's history, and it is being done
incrementally, in public, with the failure modes visible.

| Vol | Title | Range | Ch | Boundary rationale |
|---|---|---|---|---|
| 17 | Free-Threading Arrives | 3.13 | 6 | Experimental free-threading + the JIT |
| 18 | Deferred and Supported | 3.14 | 7 | PEP 649, t-strings, PEP 734, PEP 779 |
| **Deep L** | **Free-Threading and Subinterpreters** | — | 8 | After both releases that built it |
| 19 | The Frontier | 3.15+ | 4 | Designed to extend; see versioning policy |

## Part VIII — The Boundaries

**Thesis:** Python's real power is that it is a good neighbour, and every boundary — C, the OS,
the package index, the test harness — has a cost model worth knowing.

| Vol | Title | Ch | Note |
|---|---|---|---|
| **Deep M** | **The C-API, ABI, and FFI** | 9 | **Book I seam.** Evolves along the timeline, not one point |
| **Deep N** | **Packaging and Distribution** | 8 | PEP 517/518/621/751, wheels, `uv` |
| **Deep O** | **Testing, Debugging, Observability, Security** | 10 | Includes `pdb`, `sys.monitoring`, `pickle` as RCE |

## Part IX — The Standard Library

**Thesis:** The stdlib is a museum of solved problems, and knowing which exhibits are still load-
bearing is most of what separates a senior Python engineer from a fluent one.

| Vol | Title | Ch |
|---|---|---|
| **Deep P** | Text, Binary, Crypto | 8 |
| **Deep Q** | Data, Time, Numerics, Functional | 8 |
| **Deep R** | Persistence, OS, IPC, Networking | 9 |
| **Deep S** | Runtime Services, Introspection, Tooling | 7 |

## Part X — Applied Python

**Thesis:** Every domain that adopted Python did so for the same reason and paid the same tax;
the interesting engineering is in how each one bought its way out.

| Vol | Title | Ch | Note |
|---|---|---|---|
| **Deep T** | Numerical and Scientific | 9 | NumPy, SciPy, Arrow, SIMD, GPU |
| **Deep U** | Data Engineering and Distributed | 8 | **Book III seam** |
| **Deep V** | Web, Services, and the Trading Capstone | 8 | The carried-through system lands here |
| **Deep W** | Quant Finance, ML, and Frontier Domains | 8 | Absorbs the Phase XVII–XXV material |

---

## Scale and the series split (decided)

Chapter counts summed from the volume tables above:

| Part | Chapters | | Part | Chapters |
|---|---|---|---|---|
| I — Origins | 26 | | VI — Performance | 30 |
| II — The 2.x Ascent | 32 | | VII — Concurrency Reckoning | 25 |
| III — The Break | 25 | | VIII — The Boundaries | 27 |
| IV — Iteration and Async | 36 | | IX — The Standard Library | 32 |
| V — Ergonomics and Typing | 29 | | X — Applied Python | 33 |

**The series ships as two books.**

| | Parts | Volumes | Chapters | Est. words | Est. pages |
|---|---|---|---|---|---|
| **Book II — The Evolution** | I–VII | 30 | **203** | ~1.22 M | ~3,800 |
| **Book IIb — The Reference** | VIII–X | 12 | **92** | ~0.55 M | ~1,700 |
| **Total** | 10 | 42 | **295** | ~1.77 M | ~5,500 |

Book II is the timeline argument and is independently publishable. Book IIb is the topical
reference the timeline cites; it can ship second without leaving Book II incomplete, because the
two-track rule means every Book II cross-reference names a chapter that Book IIb owns.

For calibration, *The Art of Computer Programming* is roughly 3,000 pages across four volumes.
Book II alone exceeds a single TAOCP volume. This figure is recorded without trimming because the
brief asked for complete coverage at extreme detail, and this is what that costs.

**Consequence for the writing order:** Book IIb's Deep Volumes A, B, C, and I are cited by 54 of
the 100 dangling references inherited from the old draft and by most Book II timeline chapters.
They are written **first**, despite shipping second.
