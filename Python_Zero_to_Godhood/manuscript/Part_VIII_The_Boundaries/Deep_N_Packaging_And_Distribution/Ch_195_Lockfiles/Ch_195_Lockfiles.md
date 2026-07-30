# Chapter 114: Lockfiles

Chapter 112 closed with advice, run the search once, and this chapter is the file that holds the answer. A **lockfile** records the survivors: exact versions, exact artifacts, exact **hashes**, so that installation stops being resolution and becomes *verification plus extraction*. For two decades the ecosystem improvised this per tool (`requirements.txt` with `--hash`, Pipfile.lock, poetry.lock, uv.lock); **PEP 751** standardised the answer as `pylock.toml` in 2025, making the memoised search portable between tools.

The listing does the whole arc with the volume's own artifacts. It generates a `pylock.toml` pinning Chapter 109's `tinypkg` and Chapter 111's `contractpkg` with their real sha256 digests; proves generation **deterministic** (two runs, byte-identical, the lockfile itself hashable like source); installs *from* the lock, `hash verified` twice, imports work, no resolver in the loop; and then commits the volume's most instructive crime: **one byte flipped** in a wheel, and the lock refuses it. The hash pins *content*, not names or versions, a compromised mirror and a swapped upload fail identically.

The benchmark keeps the claims honest: on a *happy* 100-package graph, locked install ties resolve-and-install (24.7 vs 24.4 ms, extraction dominates), the lock's true value is Chapter 112's *adversarial* table, where the saving is unbounded, plus every network round trip the search would make. And verification runs at **2.3 GB/s**: hashing everything, always, is free policy.

**This is a Deep N chapter**, and it closes the verification queue's open row on PEP 751: what the standard fixes is the *format and semantics* of the memoised answer, what remains tool-specific is how the answer is found.

## Section index

- **114.1** The lock, generated, verified, and violated
- **114.2** The model: memoisation, markers, and portability
- **114.3** Measurement: what the lock buys, what trust costs
- **114.4** Edges and failure modes
- **114.5** Connections
- **114.6** Exercises
- **114.7** Summary and cross-references

Listings live under `code/ch195/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 114.1 The lock, generated, verified, and violated

```python
# code/ch195/l01_the_lockfile.py
```

The generated lock first; all blocks are Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- the lock: survivors, artifacts, hashes ---
  lock-version = "1.0"
  created-by = "deepn (Chapter 114)"
  environments = ["python_version >= \"3.11\""]
  [[packages]]
  name = "contractpkg"
  version = "2.0.0"
  [[packages.wheels]]
  name = "contractpkg-2.0.0-py3-none-any.whl"
  hashes = { sha256 = "49f5931186b22b692ca68b2d6043500e16fa72c08f21d92a410b9796ab77f28c" }
```

Then the three proofs, likewise Verified output (CPython 3.13.5):

```text
--- generation is deterministic ---
  two generations byte-identical : True
  lockfile's own sha256 (prefix) : 813fb8de22ef6880
  sorted packages, exact pins, content hashes: nothing in the
  file depends on time, machine, or tool mood - so the lock
  itself can be reviewed, diffed, and hashed like source
--- installing FROM the lock: verify, then extract ---
  installed contractpkg==2.0.0 (hash verified)
  installed tinypkg==1.0.0 (hash verified)
  imports work : 42, 'built-by-contract'
  no resolver ran: Chapter 112's search was memoised into the
  file, and installation reduced to hash-check plus Chapter
  109's extraction - which is why locked installs are fast AND
  reproducible
--- the tamper test ---
  installed contractpkg==2.0.0 (hash verified)
  REFUSED tinypkg: hash mismatch
```

**The lock's shape is PEP 751's shape, and every field earns its place.**
`lock-version` makes the format itself versionable; `created-by` names the generating tool without granting it authority (any tool may install from any tool's lock, the PEP's entire point); `environments` records *unevaluated* markers, Chapter 112's cross-platform edge, solved by not evaluating; and each `[[packages]]` entry pins a version and, per artifact, a filename and content hash. Notably absent: *why* these survived. The lock is the answer, not the reasoning, and §114.2 takes up what that separation means.

**Determinism makes the lock a source file.**
Sorted packages, exact pins, content hashes, nothing time-, machine-, or mood-dependent, so two generations are byte-identical and the lockfile itself can be diffed in review, hashed in CI, and blamed in git. A lockfile that is not deterministic is a build log wearing a lockfile's name.

**Install-from-lock is Chapter 109 plus a comparison.**
Verify sha256, extract, done, no resolver, no metadata reads, no candidate filtering. The listing's wheels being byte-reproducible across the whole matrix (the digests in the output are identical on all three interpreters, which the harness verifies) is its own quiet demonstration of how much of this volume's machinery is deterministic when you insist.

**And the tamper test is the security model in four lines.**
Flip the last byte of `tinypkg`'s wheel: `REFUSED tinypkg: hash mismatch`, while the untouched neighbour installs normally. Nothing about names, versions, sources, or signatures participated, **content addressing alone** converts "trust the server" into "trust the reviewed lockfile", which is a thing a team can actually audit.

---

## 114.2 The model: memoisation, markers, and portability

**A lock is a memo, and memos have staleness semantics.**
The lock answers *the requirements as of when it was generated*; changing a requirement invalidates it, and regeneration re-runs Chapter 112's search. The workflow that follows is the modern default: requirements express *intent* (ranges, honest floors), the lock expresses *decision* (pins, hashes), environments are *derived* (Chapter 113's disposability), and only the first two are edited by humans. Every "works here, breaks there" story that lockfiles ended was a team letting environments drift from any recorded decision.

**Unevaluated markers are what make one lock serve many platforms.**
PEP 751 records environment constraints and per-package markers as *expressions*, evaluated at install time on the target (Chapter 112's evaluator, run late). A lock generated on macOS can therefore install correctly on Linux, *if* the generating resolver solved for both worlds, which is a resolver feature (universal resolution) the format enables but cannot supply. That division, **format standardised, strategy competitive**, is the PEP's design and the answer to the verification queue's question: `pylock.toml` fixes representation, verification, and install semantics; discovery, universality, and update policy remain the tools' arena.

**Hashes make the lock a supply-chain boundary, with a scope worth stating precisely.**
The hash guarantees *this content*, nothing more: not that the content is benign (Chapter 116), not that the build that produced it was honest (reproducible builds close that gap, and the listing's byte-reproducible wheels show the idea), and not anything about artifacts the lock does not list. Locks must therefore be *complete*, every package, every platform's artifacts, including build dependencies for sdists, or the unlisted remainder is resolved at install time, outside the memo, defeating both reproducibility and the audit.

**What of `requirements.txt`?** It survives as the *intent* layer and as a lowest-common-denominator export. The historical trick of using it as a lock (`pip freeze`, `--hash` mode) built this chapter's machinery by hand; PEP 751 is that practice given a spec, multi-platform semantics, and portability between tools.

---

## 114.3 Measurement: what the lock buys, what trust costs

**Methodology.** `code/ch195/bench_locked_install.py`.
A synthetic 100-package environment; `min` of 5; 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| operation | time |
|---|---|
| resolve (happy graph), then install | 24.4 ms |
| from the lock: verify + extract | 24.7 ms |
| sha256 over a 16 MB artifact | 7.4 ms (**2.3 GB/s**) |

**The tie in the first two rows is the honest headline.**
On a happy graph, offline, Chapter 112's search is a linear walk that costs nothing next to extraction, and the lock saves nothing measurable. The lock's value lives in what this benchmark *cannot* contain: the adversarial graphs where search is exponential (Chapter 112 measured 6.2 seconds at *ten* packages), and the network, where unlocked resolution pays metadata fetches per candidate. Locked installation's cost is bounded by artifact bytes; unlocked resolution's cost is bounded by nothing. The benchmark reports the floor precisely so the chapter's claims stay falsifiable.

**The throughput row settles verification policy by arithmetic.**
2.3 GB/s means hashing a fat environment costs milliseconds, three orders below downloading it. "Verify always" is therefore not paranoia but a free default, and every tool that made hash-checking opt-in was leaving the cheapest guarantee in the volume unclaimed. (The same arithmetic priced Chapter 109's RECORD audit and will price Chapter 116's upload checks; content addressing is cheap *everywhere*.)

**Book I**'s locks are container digests and `conan.lock`/vcpkg baselines, and its build chapter states this section's conclusion with different artifacts: pin by content, rebuild environments from pins, and treat any unpinned fetch as both a reproducibility bug and an attack surface.

---

## 114.4 Edges and failure modes

**A lock without hashes is a version pin, not a lock.**
Versions name intentions; hashes name bytes. An index compromise or a re-uploaded artifact defeats `==2.0.0` and cannot defeat `sha256=...`, the tamper test is the difference, executed. Treat hashless locks as legacy input, never as a guarantee.

**Partial locks leak resolution back in.**
An sdist in the lock without its build dependencies locked (Chapter 111's `requires`) resolves *those* at install time; a platform absent from the lock resolves *everything* there. Completeness is a generation-time property, check for it in review, because install time discovers it in production.

**Locks do not compose across projects.**
Two applications' locks may pin conflicting versions, correctly, locks answer *per-deployable-unit* questions. Libraries therefore ship *ranges* (intent) and leave locking to applications; a library that ships its own lock is confusing its tests' environment with its users'.

**Regeneration is the vulnerable moment.**
The lock's guarantees hold between generations; each `lock upgrade` re-opens Chapter 112's search against the live index and accepts new content into the trust boundary. Review lock *diffs* like code (new packages? surprising version jumps? hash churn without version change?), and prefer minimal-change upgrade modes; the deterministic format exists to make exactly this review possible.

**`created-by` is provenance, not protection.**
Any tool can write the field; nothing verifies it. Cross-tool portability (the PEP's goal) also means cross-tool *forgeability* of the annotation; the hashes, not the header, carry the security.

**And time is not pinned.**
A lock pins content, not the index's future: yanked artifacts (Chapter 112) may vanish from servers, leaving valid locks uninstallable. Teams with long support windows mirror their locked artifacts, the lock plus its blobs, not the lock alone, is the reproducibility unit at decade scale.

---

## 114.5 Connections

**Backward.**
The search this file memoises, and the markers it keeps unevaluated, Chapter 112. The extraction and RECORD hashing it reduces installation to, Chapter 109. The build dependencies a complete lock must reach, Chapter 111. The disposable environments it makes derivable, Chapter 113. The reproducible-build property the listing's byte-identical wheels quietly exhibit, Chapter 111's determinism carried to artifacts.

**Forward.**
Compiled artifacts multiply what a complete lock enumerates (one hash per platform wheel), Chapter 115. The index, mirrors, yanking, and the trust chain the hash anchors, Chapter 116, where this chapter's tamper test scales to the ecosystem.

**Across books.**
Lockfiles are packaging's arrival at ideas the systems world converged on independently: content-addressed storage (git, Nix, OCI digests), build-input pinning (Bazel's WORKSPACE locks), and the audit-the-diff workflow. **Book I** pins toolchains and containers by digest for the same two reasons in the same order, reproducibility first, then supply-chain, and both books land on the same operational sentence: humans edit intent, machines derive everything else.

---

## 114.6 Exercises

**1. Extend the generator.** Add per-package markers and multiple wheels per package (Chapter 110's tags) to the listing's generator, then make the installer choose the right wheel by tag before verifying. You now have a working miniature of a modern installer's locked path.

**2. Diff review drills.** Generate locks before and after (a) a version bump, (b) a new transitive dependency, (c) a hash change with no version change. Write the three-line review verdict for each; the third one is the drill that matters.

**3. Close the sdist gap.** Lock a project that includes one sdist: enumerate what a complete lock must additionally pin (build backend, its requires, their hashes), generate it, and demonstrate an offline locked build (Chapter 111 + this chapter, composed).

**4. Measure the real delta.** With network enabled, time `uv sync` (or `pip install -r` with hashes) against unlocked installation for a real project, cold caches. Attribute the difference among resolution, metadata fetches, and downloads; reconcile with §114.3's offline tie.

**5. Mirror for a decade.** Design the artifact mirror for a locked application with a ten-year support window: what is stored (blobs by hash), what is the restore drill, and what breaks if you stored only the lockfile. Execute the drill once with the listing's artifacts.

**6. The design question.** PEP 751 pins artifacts but not *policies* (Chapter 110's tie-breaks) or *reasoning* (Chapter 112's proofs). Argue whether a lock should carry the resolution proof, what auditors would gain (why is this pin here?), what it costs (locks become resolver-version-coupled, exactly what the PEP avoided), and whether the `created-by` field's honest-provenance gap is better closed by proofs or by signatures (Chapter 116's tools). Commit to one design and defend it against the review-the-diff workflow this chapter established.

---

## 114.7 Summary and cross-references

- **A lockfile is Chapter 112's search, memoised**: survivors, artifacts, and content hashes, in PEP 751's portable `pylock.toml` (format standardised; discovery strategy still the tools' arena, closing the verification queue's open row).
- **Generated deterministically, byte-identical across runs and the whole matrix**, so the lock reviews, diffs, and hashes like source; markers stay *unevaluated* so one lock can serve many platforms if the resolver solved for them.
- **Installation becomes verify-plus-extract**: hash check, Chapter 109's extraction, imports work, no resolver in the loop; and the tamper test shows the model's teeth, **one flipped byte, REFUSED**, content addressing defeating swapped artifacts by construction.
- **Measured honestly**: happy-graph locked install ties unlocked (24.7 vs 24.4 ms, extraction dominates), the lock's value is the exponential and networked cases; verification runs at **2.3 GB/s**, making "verify always" free policy.
- **The discipline**: humans edit intent, locks record decisions, environments are derived; locks are complete or they leak resolution; regeneration is the vulnerable moment, review the diff; and at decade scale, mirror the blobs, not just the file.

**Cross-references.** The search and markers → Chapter 112. Extraction and RECORD → Chapter 109. Build dependencies → Chapter 111. Disposable environments → Chapter 113. Per-platform artifacts → Chapters 110, 115. The index and trust → Chapter 116.
