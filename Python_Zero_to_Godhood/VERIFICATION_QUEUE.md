# Verification Queue

Claims used in the manuscript that are **not yet confirmed to this book's standard**, and must be
before the relevant chapter is called final. A claim lives here rather than in the prose as fact.
The discipline: an honest "needs checking" outranks a confident error.

Status: `OPEN` (unverified), `SOURCED` (primary source found, transcribe), `CLOSED` (verified, with
how).

## From the Phase 0 audit (carried forward)

| # | Claim | Chapter | Status |
|---|---|---|---|
| 1 | PEP 779 free-threading support-status wording in 3.14 | Vol 18 | OPEN |
| 2 | Single-threaded overhead of the free-threaded build vs default | Deep L | OPEN |
| 3 | Whether the 3.14 JIT is a net speedup on any published suite | Deep J | OPEN |
| 4 | Whether the 3.14 tail-call interpreter gains survived the LLVM-19 artifact correction | Deep J | OPEN |
| 5 | PEP 649 interaction with dataclasses and get_type_hints | Ch 13, 16, Vol 18 | OPEN |
| 7 | Full inventory of 3.14 opcode renames beyond LOAD_FAST_BORROW | sweep | OPEN |
| 8 | Exact `_PyAttrCache` layout in current CPython | Ch 17 | OPEN |
| 9 | `Py_GIL_DISABLED` C-API rules; which top extensions ship ft wheels | Deep M, L | OPEN |
| 11 | What PEP 751 lockfiles standardised vs tool-specific | Deep N | OPEN |
| 12 | `sys.monitoring` (PEP 669) as profiling substrate; what it deprecates | Deep K, Vol 16 | OPEN |
| 13 | Provenance of arena=1MB / pool=16KB: the release each changed, in obmalloc.c | Ch 19, appendices | OPEN |
| 14 | Python 3.15 timing and feature set relative to publication | Vol 19 | PARTIAL - PEP 686 (UTF-8 mode default) verified Final and scheduled for 3.15 (peps.python.org), used in Ch 7. Full 3.15 feature set still open. |

## Release-history facts (Part I, Part II) — highest fabrication risk

| # | Claim | Chapter | Status |
|---|---|---|---|
| 15 | Release managers for 2.4, 2.5, 2.6, 3.0, 3.1, 3.2, 3.3 | Part II, III | OPEN |
| 16 | Python 1.4 / 1.5.2 exact dates and feature attributions | Ch 2 | OPEN |
| 17 | 1.6 / CNRI / BeOpen / PSF licence sequence and dates | Vol 3 | PARTIAL (1.6 = 5 Sep 2000, CNRI 1995, BeOpen 2000, PSF 2001 per Wikipedia; needs a primary source) |
| 18 | PEP 3003 moratorium exact scope and which releases it bound | Part IV | OPEN |
| 19 | Specific bpo/GitHub issue numbers for any micro release covered | various | OPEN |
| 20 | Whether MASTER_COVERAGE_MATRIX "mined" claim holds file-by-file | archives | CLOSED (ARCHIVE_AUDIT.md: upheld; residue is C-API only) |

## Opened while writing

| # | Claim | Chapter | Status |
|---|---|---|---|
| 21 | `tuple.__basicsize__` grew 24 -> 32 bytes: which release, and why | Ch 19 (Ch_019) | OPEN — measured on both interpreters; not traced to a commit or What's New |
| 22 | Python 0.9.0 vs 0.9.1 as the first alt.sources posting | Ch 1 (Ch_020) | SOURCED — Guido's history blog says 0.9.0; secondary sources say 0.9.1. Book follows primary (0.9.0) and flags the conflict in §1.6. A preserved 0.9.x source tree or archived posting would close it. |
| 23 | 0.9.0 exact feature list (as opposed to the 0.9.x line) | Ch 1 (Ch_020) | OPEN — accounts agree on classes/exceptions/modules/list/dict/str; Guido does not itemise 0.9.0 specifically. Prose claims only what the record supports. |

## Primary sources used so far

- Guido van Rossum, *The History of Python: Personal History, part 1, CWI*,
  python-history.blogspot.com (2009). Authority for the 0.9.0 date and distribution.
- Guido van Rossum, *The Making of Python*, artima.com interview. Authority for ABC's flaws and the
  extensibility rationale.
- *History of Python*, en.wikipedia.org. Cross-check only, never sole authority.
