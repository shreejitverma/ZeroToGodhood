# Build report: Python: Zero to Godhood

Date: 2026-08-23 (re-verification and web navigation fix; first full build 2026-08-22).
Toolchain: pandoc 3.10.2, LuaHBTeX 1.22.0 (TeX Live 2025), EPUBCheck 5.3.0, poppler 26.08.0, Python 3.
Build command: `make -f build/Makefile all` from `Python_Zero_to_Godhood/`, from a clean `build/`.

## Outputs

| File | Result |
|---|---|
| `build/Python_Zero_to_Godhood.pdf` | 2266 pages, 6.2 MB |
| `build/Python_Zero_to_Godhood.epub` | 2.2 MB, 350 content documents |
| `build/Python_Zero_to_Godhood.html` | 5.0 MB, single file, no external assets |
| `build/cover.png` | rendered from PDF page 1 at 200 dpi |

## Phase 0: reconnaissance

- Manuscript: 331 Markdown files under `manuscript/`; 295 are chapters, 36 are `_archive/` copies of superseded drafts (documented in `ARCHIVE_AUDIT.md`).
- Structure: 10 Parts, 19 timeline volumes, 23 deep volumes, 295 chapters.
- Authoritative order: `CANONICAL_TOC.md`.
  Its per-volume chapter counts were checked against the manuscript for all 42 volumes; all match once the Deep H/J swap below is corrected.
- Directory tree versus `CANONICAL_TOC.md`: volumes are filed under the wrong Part directories in several places (for example `Deep_D` under `Part_I_Origins`, `Deep_O` under `Part_X_Applied_Python`, `Deep_G` under a `Part_III_The_Standardization` directory that is not a Part).
  The build never infers order from the tree, so these are harmless to the book; they are listed as a follow-up.
- Defect found in the previously published build: the manuscript directories for Deep Volumes H and J carry each other's letter.
  `Deep_H_The_Interpreter_Ceval_Bytecode_JIT` holds the nine interpreter chapters (Ch_135 to Ch_159, which `CANONICAL_TOC.md` assigns to Deep J), and `Deep_J_Asyncio_And_Structured_Concurrency` holds the eight asyncio chapters (Ch_182 to Ch_189, Deep H).
  The old `structure.py` resolved volumes by letter glob, so the previous PDF placed the interpreter chapters under a "Concurrency II: asyncio" divider in Part IV and the asyncio chapters under "The Interpreter" in Part VI.
- Glyph classes in use: Latin extended, arrows and math operators, box drawing, Greek, CJK (`世界`), emoji including a ZWJ family sequence, Cyrillic (a homoglyph example), U+FEFF and U+FFFD (both deliberate, in the encoding chapters), fullwidth parenthesis (one, a manuscript typo, see follow-ups).
- Stale artifacts in the book root: `Python_Zero_to_Godhood.tex` and `00_Preface.tex`, an abandoned pdflatex approach from June 2026 that referenced only each other.

## Decisions

1. Reading order is now explicit.
   `structure.py` lists every volume with its manuscript directory and every chapter id in order; it is a transcription of `CANONICAL_TOC.md`, with the H/J directory swap corrected there rather than by renaming manuscript directories (the `code/` tree and cross-references key off the existing names).
2. Chapter numbers are preserved as written.
   The two numbering schemes overlap (86 display numbers appear twice, with different titles), but the stable `Ch_NNN` id is unique, and roughly 4,500 cross-references use the display numbers.
   Renumbering is an editorial project, not a compile step.
3. Orphans: the 36 `_archive/` files are excluded by design and are not listed in any TOC.
   No other orphan exists.
4. Normalisation is applied at assembly time only, never to the manuscript: BOM and trailing whitespace removal, `text` tag on the one untagged code fence, and backticks around a bare `__slots__` in the Ch_230 heading (without them Markdown read the underscores as emphasis and the heading, TOC entry, and running head all said "slots").
5. Removed `Python_Zero_to_Godhood.tex` and `00_Preface.tex` from the book root after confirming the pipeline reproduces the book without them.

## Changes

Added: `build/breakcode.lua`, `build/check_pdf_toc.py`, `build/check_html.py`, `build/BUILD_REPORT.md`.
Modified: `build/structure.py`, `build/assemble.py`, `build/assemble_web.py`, `build/sample.py`, `build/preamble.tex`, `build/Makefile`, `build/README.md`, `build/.gitignore`.
Removed: `Python_Zero_to_Godhood.tex`, `00_Preface.tex`.

Design fixes made while verifying:

- Overfull lines.
  The previous README claimed zero overfull boxes; the log showed 582 per pass.
  Causes and fixes: inline code cannot break (filter inserts `\allowbreak` after punctuation in spans of 14+ characters); `/` joining words or code spans in prose (filter makes it breakable); pipe tables with no width spec set as non-wrapping `l` columns and pre-sized tables whose columns were narrower than their longest code token (filter assigns widths that respect each column's longest unbreakable token, measured at mono or body width); unhighlighted `text` blocks with one token wider than the measure, which fvextra cannot split inside pandoc's `\NormalTok{}` wrapper (filter emits them as bare Verbatim lines in the same box); and `\tolerance=1500` with a 3em emergency stretch so TeX prefers a loose line to an overfull one.
- Table of contents: 325 entries overflowed the page-number box once page numbers reached four digits; `\@pnumwidth` widened to 2.6em.
- Bold Noto Sans: installed as a variable font, so fontspec silently substituted regular for bold on the title page, part and volume dividers, and TOC part entries; the bold faces are now declared as the `wght=700` instance.
- Cover: `pdftoppm` 26.x zero-pads page numbers; the cover target now uses `-singlefile`.
- The LaTeX log is now kept (`build/build_full.log`) so the overfull and missing-glyph counts can be audited.
- Volume divider title leading opened from 30pt to 32pt for the bold 26pt face.

## Verification

All commands run from `Python_Zero_to_Godhood/` against the final clean build.

```
$ make -f build/Makefile all
make all exit 0                      (6m23s wall)

$ N=$(grep -c 'This is LuaHBTeX' build/build_full.log); awk -v N=$N '/This is LuaHBTeX/{n++} n==N' build/build_full.log > /tmp/last.log
$ grep -c Overfull /tmp/last.log;  grep -c 'Missing character' /tmp/last.log;  grep -ci undefined /tmp/last.log;  grep -c '^!' /tmp/last.log
0
0
0
0
(all four LuaLaTeX passes combined: Overfull 0, Missing character 0)
Output written on input.pdf (2266 pages, 6240735 bytes).

$ python3 build/check_pdf_toc.py build/Python_Zero_to_Godhood.pdf
pages=2266 chapters_checked=295 not_exactly_twice=0        exit 0
(every chapter heading appears exactly twice in the PDF text: its TOC entry and its opener)

$ python3 build/check_html.py build/Python_Zero_to_Godhood.html
ids=6640 internal_links=3664 broken=0 external_assets=0 size=5164 KB   exit 0

$ epubcheck build/Python_Zero_to_Godhood.epub
Messages: 0 fatals / 0 errors / 0 warnings / 0 infos      exit 0
```

Underfull boxes in the final pass: 283 (loose lines; not margin violations, reported for completeness).

Glyph spot checks, rendered to PNG and inspected: CJK and box drawing (page 564, UTF codec table), emoji ZWJ family sequence (page 538), Greek and arrows (throughout code boxes), `__slots__` in headings and TOC.
Visual pass, rendered and inspected: title page (bold now correct), Part II divider, Volume 3 divider, Deep Volume H divider (now asyncio), TOC page xii (four-digit page numbers fit), a dense code page with an output box, the byte-literal and JSON output lines that previously overflowed, and the accidental-quadratics table.

## Re-verification, 2026-08-23

The full pipeline was rebuilt from a clean `build/` and every check re-run; all pass (see Verification, updated below where numbers changed).
One deliverable gap was found and fixed: the EPUB nav and HTML table of contents were flat (parts, volumes, and chapters all at one level), while the PDF TOC is a part > volume > chapter tree.
`assemble_web.py` now emits parts as H1, volumes as H2, and shifts every heading inside a chapter down two levels (the opener becomes an H3 tagged `.chapter`); preface subsections are shifted below H3 so the nav lists front matter as a single entry.
The Makefile builds the EPUB with `--toc-depth=3 --split-level=3` and the HTML with `--toc-depth=3`, and `epub.css`/`html.css` style the new hierarchy (`h1.part`, `h2.volume`, `h3.chapter`, with H4/H5 taking the former section styles).
Verified for this change: EPUB nav depth 3 with 10 parts, 42 volumes, 295 chapters (352 items, 350 content documents); HTML TOC depth 3 with 348 entries and all 295 chapter ids linked; every heading level H2 to H5 carries an id; body cross-links 1064, broken 0; epubcheck 0 fatals / 0 errors / 0 warnings; `check_html.py` ids=4388 internal_links=1412 broken=0 external_assets=0.
The id and link counts are lower than the 2026-08-22 numbers because the old depth-2 HTML TOC contributed its own 2,252 section anchors and links; body content is unchanged.
Browser pass (chrome-devtools-axi, dark mode): TOC nesting, a TOC link resolving to Chapter 15's opener, chapter/section/volume/part heading styles, code and output boxes.
PDF spot checks re-rendered and inspected: title page, Part II divider, Volume 3 divider, TOC page viii, dense code page 129, CJK codec table (page 564), ZWJ family emoji (page 538), Cyrillic homoglyph and NFKC ligature page (page 552), box-drawing diagram (page 81).

## Follow-ups (manuscript, not fixed here)

1. `Ch_001` is headed "Chapter 2: Inception and the Executable Pipeline"; `Ch_002` is also "Chapter 2".
   The TOC shows two "Chapter 2" entries at the top of Volume 2. Almost certainly `Ch_001` should be "Chapter 1".
2. Three chapter titles are reused across tracks: "Abstract Base Classes" (Deep C Ch_116, Vol 5 Ch_235), "The Iterator Protocol" (Vol 4 Ch_225, Deep F Ch_069), "Enumerations" (Deep C Ch_118, Deep Q Ch_038).
   The timeline/deep pairs are by design; the Deep C / Deep Q "Enumerations" pair is two deep volumes claiming the same topic and deserves an editorial look.
3. `Ch_218` has a fullwidth `（` inside a code span: `` `[（lambda x: ...)(y) ...` ``; should be ASCII `(`.
4. Manuscript directory names for Deep H and Deep J are swapped relative to `CANONICAL_TOC.md`; several volumes sit under the wrong Part directory, and `Part_III_The_Standardization`, `Part_IV_The_Modern_Language`, `Part_VI_The_Type_System_Era` are directory names for Parts that do not exist in the canonical structure.
   Renaming is safe only after the `code/` references and any path-based links are audited.
5. `00_Preface.md` in the book root is a superseded document (it says so in its first line) and is no longer read by the build; consider archiving it.
6. Dual chapter numbering (86 duplicated display numbers) remains the largest reader-facing rough edge; a renumber needs a cross-reference rewrite across roughly 4,500 sites.
