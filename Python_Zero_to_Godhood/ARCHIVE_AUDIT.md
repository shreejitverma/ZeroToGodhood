# Archive Audit (Step 2)

Tests whether the 72 files under `Volume_*/Chapter_*/_archive/` were genuinely mined into the
finished chapters, as `MASTER_COVERAGE_MATRIX.md` claims. Scope: the 36 `.md` archive files
against their 16 corresponding finished chapters. (Chapter 17's directory has no `_archive`.)

## Result

**The coverage matrix's claim holds at the prose level.** The finished chapters restructured their
sources rather than dropping them. The residue is narrower and more specific than expected: it is
almost entirely **C-level API surface**, and it has a designated home under the two-track structure.

## Method and why the first test was discarded

**Test 1, heading comparison** (60% token overlap): flagged **261** archive headings as unmatched
across all 16 chapters. Spot-checking 9 of them at content level found **8 covered** in the
finished prose under different headings: `ProcessPoolExecutor` IPC serialization, the `MATCH_*`
opcodes, the deallocation pipeline, dunder-to-slot mapping, PEP 383 `surrogateescape`,
`PyCoroObject`, variance, `__slots__`. An ~89% false-positive rate. **This test is unusable and its
261 figure should not be cited.** Good editing rewrites headings; heading identity is not content
identity.

**Test 2, distinctive-token comparison**: extract C identifiers, opcodes, dunders, and PEP numbers
from each archive file and subtract the finished chapter's token set. 202 distinct archive-only
tokens, then classified:

| Class | Count | Verdict |
|---|---|---|
| C-API / struct identifiers | **94** | **Real residue.** Needs a home. |
| Dunder methods | **17** | **Real residue.** Needs a home. |
| Python-2-era opcodes | 30 | **Correctly dropped.** `CALL_FUNCTION`, `JUMP_ABSOLUTE`, `SETUP_LOOP`, `DUP_TOP`, `BINARY_DIVIDE` and similar. The finished chapters use 3.13 bytecode; retaining these would be an error, not a saving. |
| Title words / prose noise | 70 | Test artifact (`INCEPTION`, `PIPELINE`, `ADVANCED`). Not content. |

## The real residue: 111 identifiers, concentrated in four chapters

| Chapter | Identifiers | Subject |
|---|---|---|
| Ch 4 — Type/Class Unification, Descriptors, C3 MRO | 33 | `PyTypeObject` slot table, `PyClassObject`/`PyInstanceObject`, `tp_as_number`/`tp_as_sequence`/`tp_as_mapping`, `PyGetSetDef`, `PyObject_GenericGetAttr`/`SetAttr` |
| Ch 7 — The Unicode Paradigm Shift | 18 | `PyASCIIObject`, `PyCompactUnicodeObject`, pre-PEP-393 layout, `Py_buffer` |
| Ch 11 — Native Async/Await | 17 | `PyCoro_Type`, `PyCoroWrapper`, `PyAsyncMethods`, event loop and OS selectors |
| Ch 5 — Decorators and Context Managers | 13 | `PyDictEntry`, `PySetEntry`, `PyFunctionObject`, container struct layouts |

Remaining 12 chapters: 3 to 12 identifiers each.

## Interpretation

The finished chapters made a consistent editorial trade: **C-level struct detail for prose
clarity**. That is defensible on its own terms and consistent with `STYLE.md` §7, which assigns
runtime internals to dedicated volumes rather than to the historical chapters.

The material is therefore **not lost and not misplaced** — it is waiting for volumes that do not
exist yet:

| Residue | Owning Deep Volume |
|---|---|
| `PyObject`, `PyObject_HEAD`, `ob_refcnt`, `ob_type`, `tp_*` core slots | **Deep A** — The Object Model |
| `PyTypeObject` slot table, descriptors, `PyGetSetDef`, MRO internals | **Deep C** — Types, Descriptors, Metaclasses |
| `PyASCIIObject`, `PyCompactUnicodeObject`, `Py_buffer` | **Deep D** — Text, Bytes, Encodings |
| `PyEval_SaveThread`/`RestoreThread`, `PyThreadState`, `Py_MUTEX_T` | **Deep E** — Concurrency I |
| `PyGenObject`, `PyCoro_Type`, `PyAsyncMethods`, selectors | **Deep F / Deep H** — Generators; asyncio |
| `PyArg_ParseTupleAndKeywords`, `PyErr_SetString`, `PyType_Ready` | **Deep M** — The C-API, ABI, FFI |

## Manifest amendment

The ARCHIVE disposition is **confirmed safe**, with one change: archive files are not provenance
only. They are a **named source for the Deep Volumes**, and the migration must carry them forward
as such rather than freezing them as history. Deliverable 3's per-chapter source lists for Deep
Volumes A, C, D, E, F, H, and M gain these 36 files.

## Correction to the Stage B response

I predicted this test would surface substantial unmined material, on the strength of the root-draft
subset test failing 3 of 3. That prediction was wrong for the archives: the root drafts and the
archives are different populations, and the archives were in fact mined. The residue is real but
narrow, and it is a structural gap rather than an editorial loss.
