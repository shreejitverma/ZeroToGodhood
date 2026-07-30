# Chapter 112: Dependency Resolution

Chapter 111 ended with resolvers reading `Requires-Dist` without running builds. This chapter is what they do with it, and, in the volume's style, the mechanism is shown by building it: a version-specifier evaluator, an environment-marker evaluator, and a **complete backtracking resolver in forty lines**, run twice against a tiny universe. Once to a solution, and the trace shows the algorithm's character: `web==3.0.0` is tried first (newest), descends two levels, hits `codec`'s contradiction, and is *dropped*, the solver backtracks to `web==2.5.0` and completes. Once into a provable conflict, and the trace shows what a conflict *is*: the space exhausted, `codec>=2.0` against `codec<2.0`, which is why real resolvers print chains of requirements, **the chain is the proof**.

The benchmark then gives resolution its cost model, and it is Chapter 87's lesson wearing an installer's clothes. A happy chain of 1,000 mutually-compatible packages resolves in **6.8 ms, 1,000 steps, linear**. An adversarial universe where only the oldest version of everything survives explodes exactly as K^N predicts: 23 thousand steps at 6 packages, 372 thousand at 8, **5.9 million steps and 6.2 seconds at 10 packages of 4 versions**. Resolver runtime is a property of the *constraint graph*, not the tool, why the same pip is instant on one project and hangs on another, and why the real fixes are the user's: honest constraints, shallow trees, and lockfiles that run the search once (Chapter 114).

**This is a Deep N chapter.**
Chapter 111 produced the metadata; Chapter 114 will freeze this chapter's output. This chapter owns the middle: specifiers, markers, and the search.

## Section index

- **112.1** The resolver, built and traced
- **112.2** The model: specifiers, markers, and the search space
- **112.3** Measurement: linear when lucky, exponential when not
- **112.4** Edges and failure modes
- **112.5** Connections
- **112.6** Exercises
- **112.7** Summary and cross-references

Listings live under `code/ch193/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 112.1 The resolver, built and traced

```python
# code/ch193/l01_a_resolver_from_scratch.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- specifiers, evaluated ---
  1.9.0 satisfies '>=1.5,<2.0'   : True
  2.0.0 satisfies '>=1.5,<2.0'   : False
  1.4.2 satisfies '!=1.4.2'      : False
--- markers, evaluated against THIS environment ---
  python_version >= "3.11"     : True
  sys_platform == "darwin"     : True
  markers make one metadata file serve every environment: the
  dependency exists only where its marker is true (and the same
  mechanism guards python_version floors and OS-specific deps)
--- the solve, traced: newest first, backtrack on contradiction ---
    try app==1.0.0
    try web==3.0.0
    try db==1.2.0
    try codec==2.1.0
    conflict: codec==2.1.0 fails '<2.0'
    backtrack from codec==2.1.0
    backtrack from db==1.2.0
    backtrack from web==3.0.0
    try web==2.5.0
    try db==1.2.0
    try codec==1.8.0
  solution : {'app': '1.0.0', 'codec': '1.8.0', 'db': '1.2.0', 'web': '2.5.0'}
```

and the second run, with `web 2.5` removed from the universe, exhausts every branch and returns `solution : None`, the conflict *proved* rather than suspected.

**The specifier block is comparisons over parsed tuples, and that near-triviality is the point.**
PEP 440's full grammar adds epochs, pre-releases, local versions, and `~=`, but its working core is what the listing shows: parse dotted versions, compare per clause, AND the clauses. The design property worth naming: specifiers are *cheap to evaluate* (the volume's cheap-filter pattern again, Chapter 110), so the expensive thing about resolution is never checking a constraint, it is *choosing which world of constraints to check*.

**The marker block makes one metadata file serve every environment.**
`python_version >= "3.11"`, `sys_platform == "darwin"`: evaluated against the running environment at resolve time, so a dependency simply does not exist where its marker is false. This is how a single wheel's `Requires-Dist` list handles Windows-only dependencies and version-conditional backports, and the listing's resolver applies markers exactly where real ones do, when expanding a chosen version's dependencies.

**And the trace is the chapter.**
Eleven lines show the entire algorithm: newest-first optimism, depth-first descent, contradiction at the leaf, backtracking that *undoes a pin two levels up*. The solution's `web==2.5.0` was nobody's preference; it is what survived. That reframing, **a pin is a survivor, not a choice**, is the correct mental model for reading any lockfile, and the failed run completes it: `None` means the space is empty, and the chain of requirements in a real error message is the resolver showing its proof.

---

## 112.2 The model: specifiers, markers, and the search space

**Resolution is search over an implicit graph.**
Nodes are (package, version) pairs; a version's edges are its marker-filtered dependencies; a *solution* is one version per reachable package satisfying every incoming specifier. The graph is implicit, discovered by reading metadata per candidate (Chapter 111's static files; for sdists, a build, which is why sdist-heavy resolution is slow twice over), and the search must handle the discovery cost as well as the combinatorics.

**Newest-first is policy, not necessity, and it shapes everything.**
Users want fresh versions, so resolvers try them first, which means a *conflict among fresh versions* costs maximal exploration before older survivors are found (§112.3's adversarial construction is exactly this). The alternative policies, oldest-first (minimal versions, Go's choice), or SAT-style global optimisation (conda), trade user expectations against worst-case behaviour, and the listing's forty lines make the policy visible as a single `sorted(..., reverse=True)`.

**Real resolvers differ from the listing in pruning, not in shape.**
pip's resolvelib and uv's PubGrub remember *why* branches failed, conflict-driven clause learning, so a contradiction discovered once prunes whole families of siblings. That converts many practical graphs from exponential to fast, and changes nothing about the worst case (the problem is NP-complete); §112.3's reading states the honest version: cleverness lowers the base, never the exponent.

**Two constraints do not enter the search**: `Requires-Python` filters candidates *before* resolution (a version gate, checked like a tag), and hashes (Chapter 114) verify *after* selection. The search space is bounded on both sides by cheap checks, the volume's pipeline shape once more.

---

## 112.3 Measurement: linear when lucky, exponential when not

**Methodology.** `code/ch193/bench_resolution_shape.py`.
The listing's resolver over synthetic universes; single solve per cell (the algorithm is deterministic); 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

**The happy chain** (every newest compatible):

| packages | time | steps |
|---|---|---|
| 10 | 0.05 ms | 10 |
| 100 | 0.44 ms | 100 |
| 1,000 | 6.76 ms | 1,000 |

**The adversarial universe** (only the oldest of everything survives; K = 4 versions each):

| packages | time | steps |
|---|---|---|
| 6 | 22.9 ms | 23,327 |
| 8 | 378.6 ms | 371,533 |
| 10 | **6,221.5 ms** | **5,942,139** |

**The two tables are the same code and different graphs.**
Happy: visit, pin, descend, one step per package, and a thousand-package tree resolves in the time of a single disk read. Adversarial: each added pair of packages multiplies steps by ~16, K squared, because every newest-first path must be individually disproved before the all-oldest solution is reached. Six seconds at *ten* packages of *four* versions; real indexes offer hundreds of versions of thousands of packages, and the only reason installation works at all is that real graphs are mostly happy and real resolvers prune with learned conflicts.

**The engineering conclusions all live outside the resolver.**
Constrain honestly: every unconstrained requirement is frontier the solver may have to walk (a floor like `>=2,<3` is a gift to the search, not just to compatibility). Keep trees shallow: depth multiplies. Cache metadata: discovery cost gates the search's inner loop. And above all **lock** (Chapter 114): a lockfile is this chapter's output, memoised, the search run once per dependency *change* instead of once per install, which is the single largest speed difference between classic workflows and modern ones.

**Book I**'s package chapter tells the same story about SAT-based system package managers, and its symbol-resolution chapter tells it about the *linker*, both searches over version-constrained graphs, both linear until they are not, both saved in practice by locks (pinned distros, fixed sonames). The exponent, as Deep K taught, is the portable part.

---

## 112.4 Edges and failure modes

**Pre-releases are excluded until something asks.**
PEP 440 hides `2.0.0rc1` from ordinary resolution unless a specifier mentions pre-releases or the user opts in. The classic surprise, "it resolved differently after the final release shipped", is this rule working; the listing's tuple-compare core deliberately omits it, and exercise 1 adds it.

**Extras multiply the graph quietly.**
`package[extra]` grafts optional dependency sets onto the same version nodes; two dependents requesting different extras of one package must agree on its *version* while unioning its edges. Resolvers model this as virtual packages, and extras-heavy ecosystems (web frameworks) pay for it in exactly §112.3's currency.

**Yanked releases resolve only when pinned.**
A yanked version is invisible to ranges but honoured by `==` pins, the index's mechanism for "do not choose this newly, do not break those who chose it". Lockfiles (Chapter 114) interact correctly by construction; hand-written `==` pins inherit the responsibility.

**Backtracking can be *externally* unbounded.**
Each candidate visited may mean a metadata fetch; for sdists, a build (Chapter 111). A resolver exploring 5.9 million steps against a network is not slow, it is *hung*, which is why real tools cap backtracking and why their "resolution too deep" errors are §112.3's table speaking.

**Markers evaluate where the resolve runs.**
A lock computed on macOS with `sys_platform` markers folds in *this* platform's answers (the listing's block prints them live). Cross-platform lockfiles must therefore keep markers *unevaluated* in the lock, PEP 751's design does (Chapter 114), and single-platform tools that evaluate eagerly produce locks that lie elsewhere.

**And "resolvable" still does not mean "runs".**
Chapter 109's drift edge applies at graph scale: the solver certifies declared metadata's consistency, nothing more. The certificates stack, resolved (here), hashed (114), imported (Deep G), tested (Deep O), and each chapter of this volume adds one.

---

## 112.5 Connections

**Backward.**
The static metadata the search reads is Chapter 111; the candidate filtering that precedes it is Chapter 110; the artifacts it selects are Chapter 109. The exponential-vs-linear discipline, and measuring the exponent rather than the constant, is Chapter 87 (Deep K), of which §112.3 is a worked instance.

**Forward.**
Environments give the resolved set somewhere consistent to land, Chapter 113. Lockfiles memoise the search and carry its hashes, Chapter 114, this chapter's direct sequel. Compiled wheels multiply candidates per version (the tag matrix), Chapter 115, and the index serving the metadata is Chapter 116.

**Across books.**
Version solving is NP-complete in every ecosystem; the interesting variation is policy. Go chose *minimal* version selection (deterministic without locks, at the price of freshness); Rust's cargo and uv chose PubGrub (newest-first with clause learning and good proofs); conda chose SAT. **Book I** lives mostly under system package managers and the linker, where the same search hides behind `apt`'s solver and `ld`'s first-match rules, and its chapter draws this volume's exact moral: the search is fine; unconstrained graphs are not.

---

## 112.6 Exercises

**1. Add pre-releases.** Extend `parse`/`satisfies` with `rc`/`b` suffixes and the exclusion rule; demonstrate a range that resolves differently with and without opt-in, reproducing the classic surprise deterministically.

**2. Learn from conflicts.** Add memoisation of failed (package, version, cause) triples to the listing's resolver and re-run §112.3's adversarial table. Report the new growth rate and identify which real resolver's strategy you have reinvented.

**3. Model extras.** Add `pkg[fast]`-style extras as virtual nodes; construct a universe where two extras of one package force a backtrack that the extras-free graph avoids.

**4. Trace a real solve.** Run `uv`'s or pip's verbose resolution on a project you know; map five lines of its output onto the listing's trace vocabulary (try/conflict/backtrack) and find the survivor pin that was nobody's preference.

**5. Bound the frontier.** Take a real project's requirements and count the candidate frontier (versions per unconstrained dependency, from the index's file list). Add honest floors and re-count; report the shrinkage as your Chapter 112 dividend.

**6. The design question.** Newest-first optimism serves users and invites §112.3's worst case; minimal-version selection (Go) is deterministic and lock-free but ships old code by default. Argue Python's position given its ecosystem's release culture, then design the hybrid: where would you apply newest-first (roots? leaves? direct deps only?) and what invariant would make it lockfile-compatible? Check your design against what uv actually does before calling it novel.

---

## 112.7 Summary and cross-references

- **Resolution is backtracking search over an implicit constraint graph**, forty lines when honest: newest-first, depth-first, undo on contradiction. A **pin is a survivor**, not a preference, and a conflict is a *proof* (the space exhausted), which is what real error chains are showing you.
- **Specifiers are cheap comparisons; markers evaluate per environment** (one metadata file serves all platforms); both are the cheap gates around the expensive search, and cross-platform locks must keep markers unevaluated.
- **Measured**: happy graphs are linear (1,000 packages in 6.8 ms); adversarial graphs are **K^N** (5.9 M steps, 6.2 s, at 10 packages x 4 versions). Pruning lowers the base; nothing lowers the exponent; the fixes are honest constraints, shallow trees, cached metadata, and **locks that run the search once**.
- **Edges**: pre-release exclusion, extras as graph multipliers, yanked-only-when-pinned, backtracking against a network, and the standing rule that resolved != runs.

**Cross-references.** Metadata → Chapter 111. Candidate filtering → Chapter 110. Artifacts → Chapter 109. The exponent discipline → Chapter 87. Environments → Chapter 113. Lockfiles → Chapter 114. The tag matrix → Chapter 115. The index → Chapter 116.
