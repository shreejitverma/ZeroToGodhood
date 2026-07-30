# Python Zero to Godhood — Book II

The evolutionary history of Python, from Guido van Rossum's Christmas 1989 prototype to the
current release, told at the level of the implementation. Every feature is traced to the release
that introduced it, the PEP that argued for it, the problem it solved, and what it cost.

This is a mastery guide for senior engineers. It assumes fluency in at least one of C++, Java, Go,
or Rust, comfort with operating-system and memory concepts, and working Python. It does not
explain what a `for` loop is; it explains what the interpreter does when it runs one.

## Status: in progress, and honestly so

**17 of roughly 295 chapters are written.** That is about 6%. The structure is settled and
recorded in [`CANONICAL_TOC.md`](CANONICAL_TOC.md); most of the book is not yet drafted.

The finished chapters are `Ch_001` through `Ch_017`, covering Python 1.0 through 3.11. They are
publication-grade. Everything else in this tree is source material, planning, or infrastructure.

| Path | What it is |
|---|---|
| `manuscript/` | The book. Parts, volumes, chapters. |
| `code/` | Runnable listings, the verification harness, benchmarks. |
| `_source/track_b/` | 128 topic drafts, not yet written up. Notes, not prose. |
| `_source/appendices/` | Reference appendices, uneven depth. |
| `CANONICAL_TOC.md` | The authoritative structure. Supersedes five earlier maps. |
| `STYLE.md` | Binding style guide: voice, terminology, code conventions. |
| `ARCHIVE_AUDIT.md` | Verification that archived sources were mined into the chapters. |

## Running the code

Every "Verified output" block in the prose was produced by a program in `code/`, and `make verify`
re-runs all of them and diffs against what the book prints. When CPython changes an opcode name or
a repr, this fails and names the listing. Version drift is a failing test here, not a reader's bug
report.

```bash
cd code
make verify          # check every listing on both interpreters
make verify CH=ch18  # one chapter
make bench           # run benchmarks
make interpreters    # report the verification matrix
```

No third-party dependencies. The harness is stdlib-only on purpose: a benchmark you cannot run is
not a benchmark.

### Verification interpreters

| | |
|---|---|
| Primary | CPython **3.13.5** (`/opt/anaconda3/bin/python3`) |
| Secondary | CPython **3.14.6** |
| Free-threaded | CPython **3.14.6t** (PEP 703 build, `Py_GIL_DISABLED=1`); keyed `3.14t`, checked only for chapters that record output for it |
| Hardware | Apple M3 Pro, 12 cores, 36 GB, macOS 27.0, arm64 |

Override with `make verify PY313=... PY314=... PY314T=...`.

Listings that need a newer interpreter declare it and are skipped, not failed:

```python
# requires: 3.14+
```

Listings that only make sense without the GIL declare `# requires: free-threaded`
and are skipped on ordinary builds; their expected output is recorded with
`make record-314t CH=chNNN` and lives under `expected/3.14t/`.

### Two things about the numbers in this book

**Transcripts are pinned to the release under discussion, not to one interpreter.** A chapter
about Python 3.4's bytecode showing 3.14's output would be false, and the whole argument of this
book is that these things changed. Historical transcripts are labelled with the interpreter that
produced them. Where that interpreter is no longer buildable on current hardware — which is the
case for everything before 2.7 — the transcript is sourced to the *What's New* entry or the PEP
and marked `UNVERIFIED-HISTORICAL`. It is never silently regenerated on a modern interpreter.

**Timing comparisons are made within a single interpreter, never across builds.** The two
interpreters above differ in optimisation level and in whether computed gotos are enabled, and
either difference swamps the effects this book measures. `make interpreters` reports whether two
builds are comparable; the harness refuses to rank rows that are not. Benchmarks report `min` as
the headline statistic, because microbenchmark noise is one-sided, with median and relative
standard deviation as diagnostics for how quiet the machine was.

## Reading order

Front to back. The book interleaves two kinds of volume:

- **Timeline volumes** are narrative. They ask what problem the core developers faced in a given
  release window, what they considered, what they shipped, and what it broke.
- **Deep volumes** are topical. Each owns one mechanism — the object model, the allocator, the
  import system, the C-API, the type system — and teaches it completely, once.

A timeline chapter may *use* a mechanism and must cross-reference the Deep volume that owns it. It
may not re-derive it. Deep volumes are placed at the point in the timeline where their mechanism
first becomes load-bearing, so a front-to-back reader always meets a mechanism before the releases
that depend on it.

## The other books

Book II connects deliberately to its siblings through a shared example, a limit order book:

- **[Book I, C++](../CPP_Zero_to_Godhood/)** owns the matching engine. Book II takes its tick
  stream zero-copy across the buffer protocol and calls back into it for the hot path.
- **[Book III, Agentic AI](../Agentic_AI_Zero_to_Godhood/)** consumes the same tick stream as a
  corpus for a retrieval index.

Seam code lives in `code/seams/`.

## Contributing corrections

Factual errors matter more than typos. If a claim in this book is wrong, the useful report names
the file, quotes the claim, and gives the command that disproves it. Several corrections have
already been made this way, and the ones that stuck all came with a reproduction.
