# Chapter 110: The Tag System

Chapter 109 built a wheel named `tinypkg-1.0.0-py3-none-any.whl` and promised that the filename is the compatibility claim. This chapter is the claim's grammar: three tags, `{python}-{abi}-{platform}`, answering three independent questions, *which interpreter may run this code, which C ABI does it bind, which OS and CPU is it compiled for*, and a fifteen-line selector that shows how an installer ranks every candidate on the string alone.

This chapter's listing is the one place in the book where the verification matrix itself becomes the exhibit. The block that computes the running interpreter's tag prints `cp313`, `cp314`, and **`cp314t`** across the three legs, and the selector's ranking *changes with it*: on the free-threaded build, the `cp311-abi3` wheel that ranked "better" on both GIL builds flips to **REJECT**, because the stable ABI's forward-compatibility promise does not cross into the free-threaded universe. That flip, recorded and verified per-build, is Chapter 82's flags and Chapter 93's wheel-adoption bottleneck rendered as installer behaviour.

The benchmark closes the argument Chapter 109 opened: parsing and ranking 10,000 candidate filenames costs **206 ns each**, ~2 ms for an index page. Compatibility decided by string comparison is the design's achievement, an installer can reject the world's wheels without downloading any of them.

**This is a Deep N chapter.**
Chapter 82 owns the ABI flags and the limited API underneath; Chapter 115 owns building compiled wheels that carry the hard tags. This chapter owns the grammar and the selection.

## Section index

- **110.1** The grammar, decoded and computed
- **110.2** The model: three questions, three tags
- **110.3** Measurement: the filter at index scale
- **110.4** Edges and failure modes
- **110.5** Connections
- **110.6** Exercises
- **110.7** Summary and cross-references

Listings live under `code/ch191/` and are re-executed by `make verify` on the full matrix, where this chapter's per-build differences are the subject itself.

---

## 110.1 The grammar, decoded and computed

```python
# code/ch191/l01_the_tag_system.py
```

The matrix differences are quoted after this block, which is Verified output (CPython 3.13.5):

```text
--- the grammar: python tag - abi tag - platform tag ---
  requests     python=py3    abi=none   platform=any
  numpy        python=cp313  abi=cp313  platform=macosx_14_0_arm64
  cryptography python=cp311  abi=abi3   platform=manylinux_2_28_x86_64
  numpy        python=cp314  abi=cp314t platform=macosx_14_0_arm64
  py3-none-any : pure Python, no ABI, any OS - one wheel for the
    whole world (Chapter 109's tinypkg)
  cp313-cp313  : CPython 3.13's full ABI - one wheel PER minor
    version per platform (Chapter 82's flags, as a filename)
  cp311-abi3   : the stable ABI - built once against 3.11's limited
    API, installable on every CPython >= 3.11 (Chapter 82's trade)
  cp314-cp314t : the free-threaded ABI - a separate wheel universe,
    because Py_INCREF is compiled differently (Chapter 94)
--- this interpreter's own tags, computed ---
  interpreter/abi tag : cp313
```

On 3.14 the computed tag line reads `cp314`; on the free-threaded build it is Verified output (CPython 3.14t):

```text
  interpreter/abi tag : cp314t
```

and the selector's verdict on the same three candidates changes with the build. On both GIL builds the exact-ABI wheel ranks **best**, the `cp311-abi3` wheel **better**, and `py3-none-any` **ok**; on 3.14t the abi3 candidate is **REJECT**ed outright and only the `cp314t` and pure-Python wheels survive.

**Four example filenames cover the whole design space.**
Pure Python (`py3-none-any`): one wheel serves every interpreter and OS, which is why Chapter 109's hand-built wheel chose it. Version-locked native (`cp313-cp313-macosx_...`): the full C ABI, one wheel *per minor version per platform*, the build-matrix explosion Chapter 115 tames. Stable-ABI native (`cp311-abi3-...`): built once against the limited API, installable on 3.11 and everything after. And the new fourth quadrant, `cp314t`: the free-threaded ABI, disjoint from all of the above.

**The computed-tag block derives the claim from first principles**: `cp{major}{minor}` plus a `t` exactly when `Py_GIL_DISABLED` is compiled in, the same `sysconfig` probe Chapter 93's listing used for build identity, now producing the string that names an entire wheel universe.

**And the selector is small because the design is good.**
Score 0 rejects; higher scores are more *specific* compatible claims; most-specific wins. Real installers rank hundreds of tag combinations (platform fallback chains, `manylinux` hierarchies), but the ordering principle, and the abi3 floor check with its free-threaded exclusion, fit in fifteen readable lines, and the listing's per-build verdict flip proves they are the *load-bearing* fifteen.

---

## 110.2 The model: three questions, three tags

**The python tag answers "which interpreter?"**
`py3` means any Python 3; `cp313` means CPython 3.13 specifically (PyPy has `pp` tags). Pure-Python wheels stop here, one build artifact, universal reach, and everything below this line exists only because C code binds tighter.

**The ABI tag answers "which binary contract?"**
`none` for no native code; `cp313` for the full per-minor-version ABI, every structure layout and symbol Chapter 82 catalogued; `abi3` for the limited API's frozen subset, the trade of some C-API surface (and some speed, Chapter 82 measured it) for one-wheel-many-versions; and `cp314t` for the free-threaded build, where even `Py_INCREF` compiles differently (Chapter 94's split refcount), making the ABI disjoint rather than versioned, no floor rule can bridge it, hence the REJECT.

**The platform tag answers "which OS and CPU?"**
`any` for none; otherwise OS, version floor, and architecture (`macosx_14_0_arm64`, `win_amd64`). Linux's entries encode the *glibc* floor (`manylinux_2_28_x86_64`) or musl (`musllinux_1_2`), because on Linux the C library is the real platform, a story Chapter 115 owns, along with why `linux_x86_64` wheels are forbidden on the index.

**Independence is the design's power.**
Three orthogonal axes mean an index can serve compatibility decisions for every platform from one flat list of filenames, and an installer's context (its interpreter, its OS) picks the compatible subset by string comparison, §110.3's 206 ns. The cost of the orthogonality is the build matrix: a native package supporting four Python versions, both build flavours, and five platforms ships dozens of wheels, and Chapter 115's tooling exists to generate them.

---

## 110.3 Measurement: the filter at index scale

**Methodology.** `code/ch191/bench_candidate_filtering.py`.
10,000 synthetic wheel filenames spanning the tag space, parsed and ranked against the running interpreter; `min` of 7; 3.13 shown.
CPython 3.13.5, Apple M3 Pro, macOS 27.0, arm64.

| operation | cost |
|---|---|
| parse + rank one candidate | 206 ns |
| a 10,000-file index page | 2.06 ms |

**The number's job is to license the architecture.**
Two milliseconds to triage a page larger than any real package's file list means the tag filter is *free* relative to everything it gates: a single wheel download is tens of milliseconds to seconds; a single sdist build (Chapter 111) is seconds to minutes; a resolution round (Chapter 112) multiplies both. The pipeline is shaped like every good pipeline in this book, cheapest filter first, and the tag system is what makes the cheapest filter *possible*: compatibility as pure syntax.

**The same shape appears twice more in this volume**, deliberately: version specifiers filter candidate *versions* by string-adjacent comparison before resolution explores them (112), and hash pins reject artifacts before installation trusts them (114). Filename tags, version specifiers, content hashes: three string-checkable gates, in increasing order of what they cost to verify and what they guarantee, and the volume's architecture chapter (116) is largely about keeping expensive trust behind cheap gates.

**Book I**'s parallel is the ELF header check before `dlopen`: reject on four magic bytes and a machine field before relocating anything. Same principle, compatibility metadata cheap enough to check always, and its packaging chapter's build matrix (triplets, `-march` variants) is the same orthogonal explosion with the same tooling answer.

---

## 110.4 Edges and failure modes

**The abi3 exclusion on free-threaded builds is temporary policy, not eternal law.** §110.1.
The limited API is being extended toward free-threaded compatibility; when a stable ABI spans both flavours, the REJECT row will change, and this chapter's recorded per-build outputs will need re-recording. That is the harness working as designed (Chapter 85's drift-detection), and the listing is the regression test for the ecosystem event.

**Tags claim; they do not certify.**
A wheel tagged `py3-none-any` can still contain `ctypes` calls into bundled binaries, platform-specific paths, or `os.uname` branches. The tag system is honest metadata honestly filtered, and Chapter 116's trust story begins where tag honesty ends.

**Normalisation applies to the name segment, not the tags.**
`My-Pkg` and `my_pkg` collide (PEP 503, Chapter 109's edge); `cp313` and `CP313` do not, tags are case-sensitive, exact grammar. Hand-rolled tooling that lowercases whole filenames breaks the tag match; split first, normalise only the name.

**The platform tag's version is a floor, checked against the running OS.**
`macosx_14_0_arm64` refuses to install on macOS 13, even if the binary would run; conversely an old floor runs anywhere newer. Publishers set the floor with build-time deployment targets (Chapter 115), and "works on my machine, no wheel for yours" is usually a floor set carelessly high.

**Multiple compatible wheels can tie, and the tiebreak is installer policy.**
Given equal specificity (say, two platform variants both acceptable), installers apply their own preference orders. The *rejection* rules are spec; the *preference* rules are convention, one of the few places the ecosystem's tools can legitimately disagree.

**And `pip debug --verbose` prints the full accepted-tag list**, hundreds of entries, the fallback chains this chapter's fifteen lines abstract. When a wheel mysteriously will not install, diff its tag triple against that list; the answer is always in the strings.

---

## 110.5 Connections

**Backward.**
The wheel the tags decorate is Chapter 109. The ABI reality underneath, flags, the limited API, why `Py_DEBUG` and `Py_GIL_DISABLED` change layouts, is Chapter 82; the split refcount that makes `cp314t` disjoint is Chapter 94; the adoption bottleneck the disjointness creates is Chapter 93.

**Forward.**
Who *writes* the tags: build backends compute them at build time, Chapter 111. The resolver consumes the filtered candidate list, Chapter 112. The full hard-tag story, `manylinux`, floors, matrices, `cibuildwheel`, is Chapter 115, and the index that serves filenames-first is Chapter 116.

**Across books.**
Target triples (`aarch64-apple-darwin`), SONAMEs, and symbol versioning are C++'s tag system, richer, messier, and solving the identical problem: name binary compatibility so it can be checked without loading. **Book I**'s chapter on ABI stability reads as this chapter with the string grammar swapped for linker lore, and its conclusion is the same sentence: the cheapest compatibility check is the one in the name.

---

## 110.6 Exercises

**1. Extend the selector.** Add platform-tag checking (exact + `any`) and a `manylinux_2_X` floor rule to the fifteen lines. Validate against five real wheels from your own cache.

**2. Diff the truth.** Run `pip debug --verbose` on two of the matrix interpreters; diff the accepted-tag lists and annotate five lines of the diff with the chapter section that explains each.

**3. Reproduce the flip.** Take any real abi3 wheel; attempt installation on a GIL build and the t-build; capture both outcomes and match them to the listing's verdict lines.

**4. Break a floor.** Build a trivial native wheel (Chapter 115's tooling, or `zipfile` plus a prebuilt dylib) tagged with a too-new macOS floor; show the installer's rejection and the one-line fix.

**5. Price the alternative.** Simulate compatibility-by-download: measure fetching and opening 50 small wheels to read their `WHEEL` files, against tag-filtering the same 50 filenames. Report the ratio and write the sentence the tag system saves.

**6. The design question.** Tags encode *compatibility* but not *preference*: nothing in the grammar says a `cp314` wheel should beat `abi3` when both fit, installers just do. Argue whether preference belongs in the spec: what pinning it would buy (bit-identical resolution across tools, Chapter 114's goal), what it costs (freezing performance folklore, like "specific beats stable", into standards), and which existing tie the ecosystem has actually been bitten by. Then check your answer against how PEP 751 lockfiles sidestep the whole question by pinning artifacts, not policies.

---

## 110.7 Summary and cross-references

- **Three tags, three questions**: python (`py3`/`cp313`, which interpreter), ABI (`none`/`cpXY`/`abi3`/`cpXYt`, which binary contract), platform (`any`/OS-floor-arch, which machine). The filename is the whole claim, and selection is string comparison, most-specific compatible wins.
- **The matrix is the exhibit**: the computed tag prints `cp313`/`cp314`/**`cp314t`** across the legs, and the selector's abi3 verdict flips to REJECT on the t-build, the stable ABI's forward promise does not cross the free-threaded boundary (Chapters 82, 93, 94), recorded and verified per build.
- **Priced**: 206 ns per candidate, ~2 ms per 10,000-file page, compatibility filtering is free relative to everything it gates, the volume's cheapest-filter-first architecture in one number.
- **The quadrants**: pure (`py3-none-any`, one wheel for the world), version-locked native (one per minor per platform, the matrix Chapter 115 tames), stable-ABI (`abi3`, build once, GIL builds only for now), free-threaded (`cp314t`, a disjoint universe).
- **Edges**: tags claim rather than certify; platform versions are floors; name normalisation stops at the tags; ties resolve by installer convention; and the abi3/t exclusion is policy with an expiry date, guarded by this chapter's recordings.

**Cross-references.** The wheel → Chapter 109. ABI flags and the limited API → Chapter 82. The split refcount → Chapter 94. The adoption bottleneck → Chapter 93. Build backends → Chapter 111. Resolution → Chapter 112. `manylinux` and build matrices → Chapter 115. The index → Chapter 116.
