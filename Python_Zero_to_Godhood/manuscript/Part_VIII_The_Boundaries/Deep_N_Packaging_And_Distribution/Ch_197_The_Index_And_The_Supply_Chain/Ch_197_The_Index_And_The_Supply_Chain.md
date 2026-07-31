# Chapter 116: The Index and the Supply Chain

Deep N closes by assembling its chapters into the thing they describe. The listing builds a local index in PEP 503's shape, a directory of normalised names, a page of filename anchors with hash fragments, from wheels this volume created, and then one function runs the full client pipeline, offline: **discover** (the page), **normalise** (this chapter), **filter** (Chapter 110's tag selector), **verify** (Chapter 114's hash anchor), **extract** (Chapter 109's install). Five chapters, one function, zero network, `import tinypkg; answer() : 42`. **An installer is nothing else.**

Around that composition, the chapter supplies the two things only the closing chapter can: the *threat model*, printed as the execution-surface audit (wheel extraction runs nothing; an sdist build runs the publisher's code, always; `.pth` import-lines run at every startup after; entry-point scripts run as you), and the *arithmetic* that ends every excuse: the entire safety apparatus, naming, tags, hashes, adds **+18%** to bare extraction offline, and vanishes into the first round trip online. There is no performance case for an unverified install, and there never was.

**This is a Deep N chapter, and it closes Deep N.**
Chapters 109 to 115 built the mechanisms; this chapter is the ecosystem they compose into, the index's contract, the names' discipline, and the trust chain's honest boundaries.

## Section index

- **116.1** The pipeline, composed
- **116.2** The model: the index's contract and the trust chain
- **116.3** Measurement: what safety costs
- **116.4** Edges and failure modes
- **116.5** Connections, and the volume closed
- **116.6** Exercises
- **116.7** Summary and cross-references

Listings live under `code/ch197/` and are re-executed by `make verify` on the full matrix: CPython 3.13, 3.14, and the free-threaded 3.14t build.

---

## 116.1 The pipeline, composed

```python
# code/ch197/l01_the_index_and_the_pipeline.py
```

Verified output (CPython 3.13.5, identical on 3.14.6 and on 3.14t):

```text
--- name normalisation: one namespace, many spellings ---
  My.Package     -> my-package
  my-package     -> my-package
  MY__PACKAGE    -> my-package
  PEP 503 folds case and runs of separators, so these are ONE
  project - and a squatter cannot register a spelling variant
--- the index: a directory of names, a page of hashed links ---
  /simple/tinypkg/ : <a href="../../pool/tinypkg-1.0.0-py3-none-any.whl#sha256=<64 hex>">tinypkg-1.0.0-py3-none-any.whl</a>
  filenames carry the tags (Chapter 110), fragments carry the
  hashes (Chapter 114): the whole contract fits in an anchor
--- the pipeline, composed from this volume's chapters ---
  normalise 'TinyPkg'        -> 'tinypkg'
  discover  1 candidate file(s) on the page
  filter    tag-compatible best: tinypkg-1.0.0-py3-none-any.whl
  verify    sha256 matches index fragment : True
  extract   installed (Chapter 109's operation)
  import tinypkg; answer() : 42
  discover, normalise, filter, verify, extract: five chapters,
  one function, zero network - an installer is nothing else
--- where installing can run code: the surfaces ---
  wheel extract        : never (Chapter 109's asymmetry)
  sdist build          : always - the backend is code (Ch 111)
  .pth import lines    : at every startup after (Chapter 113)
  entry-point scripts  : at first use, as you (Chapter 109)
```

**The normalisation block earned its own bug during authoring.**
`My.Package`, `my-package`, and `MY__PACKAGE` fold to one name, so a squatter cannot register a spelling variant of an existing project. But the folding has edges the author of this listing hit live: `Tiny.Pkg` normalises to `tiny-pkg`, which is *not* `tinypkg`, separators fold into each other, they do not vanish, and the pipeline correctly failed to find the package until the request was spelled as a case variant. The rule protects against separator games *within* a name; it does not make `tinypkg` and `tiny-pkg` one project, and both facts are the design.

**The index block shows how little "the index" is.**
A name maps to a page; a page is anchors; an anchor's text is a filename (carrying Chapter 110's whole compatibility claim) and its fragment is a hash (carrying Chapter 114's whole trust claim). That the contract fits in an `<a>` tag is why mirrors are trivial, why `--index-url` can point anywhere, and why the listing can stand up a spec-shaped index in eight lines. (The modern JSON simple API is the same contract with better parsing; the shape is identical.)

**And the pipeline trace is the volume's table of contents, executing.**
Each line names its chapter, and the composition is literal: the functions imported are the earlier listings' functions. The volume did not describe an installer and then build a toy; the descriptions *were* the installer, assembled here.

---

## 116.2 The model: the index's contract and the trust chain

**The index is a dumb content server, on purpose.**
It stores what publishers upload, serves names, filenames, and hashes, and *decides nothing*: no compatibility logic (the client's tags), no resolution (the client's solver), no trust beyond transport (the client's hash checks). Every intelligent operation happens client-side against cheap metadata, which is why the whole ecosystem can run on static file hosting plus an upload endpoint, and why supply-chain security is necessarily a *client and publisher* discipline rather than a server feature.

**The trust chain has exactly three links, with named gaps.**
*Transport*: TLS to the index, defeating on-path tampering, and nothing else. *Content*: the hash, from index fragment or lockfile, guaranteeing these-bytes, Chapter 114's anchor, defeating swapped artifacts and compromised mirrors, and saying nothing about whether the bytes are benign. *Provenance*: attestations (PEP 740, trusted publishing) binding an artifact to the source repository and CI workflow that built it, defeating account-takeover uploads, and saying nothing about the source being honest. Each link closes its predecessor's gap; the remaining gap, malicious source, is closed by nothing but review, which is why the execution-surface map matters: it says *what* needs review and *when* it runs.

**The surfaces rank the artifacts.**
A wheel installs without running code; its risks activate at *import*, visible in review. An sdist runs its build backend at install, arbitrary code, as the publisher, on the installing machine, which is why resolvers prefer wheels, why CI pins `--only-binary` where it can, and why Chapter 115's matrix work is security work. `.pth` files run at every subsequent startup (Chapter 113's audit), and entry-point scripts are ordinary programs. The operational summary in the listing's last lines is a complete policy: prefer wheels, lock and hash everything, audit `.pth`, and treat an sdist build as running the publisher's code, because it is.

**Publishing is the chain in reverse**: build deterministically (Chapter 111; the volume's own wheels are byte-reproducible), upload over an authenticated channel with attestations, and the index's normalisation plus first-come naming does the rest. The classic attacks, typosquats (`reqeusts`), dependency confusion (internal names shadowed on the public index), hostile maintainer handovers, all target the *naming and publishing* steps, and their mitigations (reserved internal prefixes, index priority rules, lockfile review per Chapter 114) are all client-and-process, per the dumb-server design.

---

## 116.3 Measurement: what safety costs

**Methodology.** `code/ch197/bench_pipeline_overhead.py`.
One hundred packages, full pipeline against bare extraction, offline; `min` of 5; 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| operation, 100 packages | time |
|---|---|
| bare extraction | 24.8 ms |
| full pipeline (discover + normalise + filter + verify + extract) | 29.2 ms |
| safety overhead | **+18%** |

**Eighteen percent, offline, is the closing argument.**
The naming discipline, the tag filter (206 ns per candidate, Chapter 110), and sha256 at 2.3 GB/s (Chapter 114) together add a few milliseconds to the unzip they guard, measured in the *worst case for the overhead*: local wheels, no network, nothing else to hide behind. Online, the first TCP round trip costs more than the entire apparatus. Every stage of this volume's machinery is cheap because it was *designed* to be checkable from strings and digests, and this table is that design's receipt.

**The comparison that matters is with the alternative's cost**, which this book has measured in other forms all volume: an unverified artifact is Chapter 114's tamper test un-run, an sdist-by-default policy is Chapter 111's arbitrary execution at install scale, and a bloated environment is Chapters 109 and 113's compounding scan taxes. Safety here is not a tax on speed; mostly it *is* the speed (locks skip resolution, wheels skip builds, hashes skip trust meetings).

**Book I** closes its packaging chapter with the same table shape, signature verification as a rounding error on package install, and the same sentence serves both: the expensive part of supply-chain security was never the cryptography; it is the human review the cryptography focuses.

---

## 116.4 Edges and failure modes

**Normalisation protects within, not across.** §116.1.
`tiny-pkg` and `tinypkg` are distinct projects; one-character typos are distinct projects; visually-confusable names are distinct projects. The index's name rules stop separator games only; typosquatting defence is lockfile review (new names in the diff, Chapter 114) and dependency counts kept small (Chapter 112).

**Dependency confusion is an index-priority bug you configure yourself.**
A client consulting both a private and the public index for an internal name may prefer the public squatter's higher version. Mitigations are mechanical: reserved prefixes on the public index, per-package index pinning, or a single proxy index, and a lockfile turns the mistake from silent to reviewable.

**Yanked, deleted, and re-uploaded artifacts stress different links.**
Yank (Chapter 112) is honest: ranges skip it, pins keep it. Deletion breaks valid locks (mirror your blobs, Chapter 114). Re-upload of *changed bytes under the same filename* is forbidden by the index precisely because hashes would scream, when a hash mismatch appears, believe the hash, not the filename.

**Attestations bind provenance, not intent.**
PEP 740 proves "built from repo X, workflow Y". A malicious commit in repo X attests perfectly. The chain's last gap is closed by code review and by minimising what needs reviewing, fewer dependencies, wheels over sdists, and the surface map's priorities.

**The build backend is inside your trust boundary.**
`[build-system] requires` (Chapter 111) is installed and *executed* to build any sdist, including transitively during resolution's metadata builds (Chapter 112). Lock build dependencies too, or `--only-binary` the world; the surface map's "always" row is reached more often than install logs make visible.

**And the volume's offline discipline is itself the security posture.**
Everything this volume demonstrated ran without a network: builds (111), resolution (112), locks (114), installs (109, 116). A pipeline that *can* run offline from mirrored, hashed artifacts is a pipeline whose every online step is an explicit, reviewable choice, which is the supply chain's end state, and the reason this book's own harness (`make verify`) runs air-gapped.

---

## 116.5 Connections, and the volume closed

**Backward, through the volume this chapter assembled.**
The artifact and its extraction, 109. The compatibility claim in the filename, 110. The build contract behind every sdist, 111. The search the lockfile memoises, 112. The prefix the extraction lands in, 113. The hash that anchors all of it, 114. The compiled matrix that multiplies artifacts, 115. This chapter added only the index's shape and the threat model, and then let the chapters compose, which is what a volume about *contracts* should be able to do.

**Beyond the volume.**
The hashes are Deep P's algorithms; the zip and HTML mechanics are Deep R's; the import that finishes every install is Deep G's; execution-surface auditing joins Deep O's security chapters. And the ecosystem's history, distutils to setuptools to PEP 517's settlement, belongs to the timeline volumes, where packaging appears as the release-by-release argument it was.

**Across books, one last time for Deep N.**
Content addressing, dumb servers, client-side policy, provenance attestation, and the review-focusing role of cryptography: the same five ideas organise **Book I**'s chapter on system packages and container registries, with OCI digests for hashes and SLSA for attestations. The shared system ships through both pipelines from one CI, and its security runbook, verify by content, pin by lock, review the diff, know what executes, does not mention which language it is protecting.

---

## 116.6 Exercises

**1. Extend the mini-index.** Add multiple versions and a yanked flag to the listing's index; teach `install` the yank rule (skipped by ranges, honoured by pins). Verify against Chapter 112's semantics.

**2. Stage a confusion attack.** Two local indexes, an "internal" package on one and a higher-versioned impostor on the other; show the naive multi-index client choosing wrong, then fix with index pinning and show the lockfile diff that would have caught it.

**3. Audit a real environment's surfaces.** For an environment you use: count sdists in its lock (the "always" row), executable `.pth` lines (Chapter 113's auditor), and entry points (Chapter 109's scan). Write the three-line risk summary.

**4. Verify a real attestation.** Pick a PyPI package with PEP 740 attestations; fetch and verify one; write down exactly what it proved and the two things it did not.

**5. Go fully air-gapped.** Using this volume's tools only, mirror a small real project (wheels + lock + index pages) and install it on a networkless machine. Time it against the online install and file the difference under §116.3's argument.

**6. The design question.** The index is dumb by design; a smart index could refuse malware, scan uploads, verify reproducibility, and break every mirror, cache, and air-gap in this chapter. Argue the dumb-server position from this volume's evidence (every check that matters ran client-side, offline, in milliseconds), then identify the one server-side check you would add anyway, and reconcile it with the mirrors.

---

## 116.7 Summary and cross-references

- **An installer is five composed contracts**: discover (a page of anchors), normalise (PEP 503, folding within a name, not across names), filter (tags), verify (hashes), extract (unzip), demonstrated by running this volume's own listings as one offline function.
- **The index is a dumb content server**: filenames carry compatibility, fragments carry trust, all policy is client-side, which is why mirrors are trivial and why supply-chain security is a client-and-publisher discipline.
- **The trust chain is three links with named gaps**: TLS (transport), hashes (content, Chapter 114's anchor), attestations (provenance, PEP 740), and the last gap, malicious source, is closed only by review, focused by the execution-surface map: **wheels never execute at install; sdist builds always do; `.pth` runs at every startup; scripts run as you**.
- **Measured**: the full safety apparatus adds **+18% to bare extraction offline** and vanishes online, there is no performance case against verification, and mostly the safety *is* the speed (locks skip searches, wheels skip builds).
- **Deep N, closed**: 109 the artifact, 110 the claim, 111 the build, 112 the search, 113 the destination, 114 the memo and anchor, 115 the hard artifacts, 116 the pipeline. Verify always, lock always, prefer wheels, keep environments lean, and know which stages run code.

**Cross-references.** The artifact → Chapter 109. Tags → Chapter 110. Builds → Chapter 111. Resolution → Chapter 112. Environments and `.pth` → Chapter 113. Locks and hashes → Chapter 114. The compiled matrix → Chapter 115. Hash algorithms → Deep P. Imports → Deep G. Security auditing → Deep O.
