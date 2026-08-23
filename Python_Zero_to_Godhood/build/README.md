# Book build system

Compiles the manuscript into a professionally designed book in three formats:
a print-quality **PDF**, a navigable **EPUB**, and a self-contained **HTML** edition.

## Quick start

Run from the book root (`Python_Zero_to_Godhood/`):

```
make -f build/Makefile all      # PDF + EPUB + HTML
make -f build/Makefile pdf      # print-quality PDF only
make -f build/Makefile epub     # EPUB only
make -f build/Makefile html     # HTML only
```

Outputs land in `build/`:

| File | What |
|---|---|
| `Python_Zero_to_Godhood.pdf`  | print-quality PDF, about 2270 pages (LuaLaTeX + KOMA scrbook) |
| `Python_Zero_to_Godhood.epub` | reflowable e-book with full nav and cover |
| `Python_Zero_to_Godhood.html` | single self-contained HTML (dark-mode aware) |
| `cover.png`                   | cover image rendered from the PDF title page |

## Requirements

- **pandoc** 3.x
- **LuaLaTeX** (TeX Live) with: `koma-script`, `microtype`, `tcolorbox`, `fvextra`,
  `unicode-math`, `ragged2e`, `enumitem`, `needspace`, `ulem`, `parskip`, `pdfcol`,
  `upquote`, `xurl`, `footnotehyper`, `selnolig`.
- **Python 3** (assembly scripts, no third-party deps)
- **poppler** (`pdftoppm`) for the cover image
- Fonts: **Charter** (body), **Noto Sans** (headings), **JetBrains Mono** (code),
  with **Noto Sans CJK SC** and **Noto Color Emoji** as glyph fallbacks.

## Verification

```
python3 build/check_pdf_toc.py build/Python_Zero_to_Godhood.pdf   # every chapter heading once
python3 build/check_html.py   build/Python_Zero_to_Godhood.html  # no broken anchors, no external assets
epubcheck build/Python_Zero_to_Godhood.epub                       # EPUB conformance
grep -c "Overfull\|Missing character" build/build_full.log        # must be 0
```

`BUILD_REPORT.md` records the results of the last full verification.

## How it works

1. `structure.py` is the single source of truth for reading order: a hand-checked
   transcription of `CANONICAL_TOC.md` listing every Part, every Volume with its
   manuscript directory, and every chapter id (`Ch_NNN`) in order. Nothing is inferred
   from directory names; two Deep Volume directories carry swapped letters in the
   manuscript tree (`Deep_H_...` holds Deep Volume J and `Deep_J_...` holds Deep
   Volume H), and `structure.py` is where that is corrected.
2. `assemble.py` walks that structure, resolves every chapter id to exactly one file
   (aborting on 0 or 2+ matches, or on chapter directories not listed in
   `structure.py`), normalises each chapter on the way through (BOM, trailing
   whitespace, untagged code fences), and emits `book_body.md`: one Markdown stream
   with raw-LaTeX blocks injected for the title page, copyright, preface, table of
   contents, part pages, and volume dividers.
3. `assemble_web.py` does the same for EPUB/HTML, emitting Markdown headings for the
   part/volume dividers instead of raw LaTeX.
4. `preamble.tex` is the book design: fonts and glyph fallback, colour palette, page
   geometry, code/output box styling, part/volume/chapter typography, running heads,
   the title/copyright/colophon macros, and the multi-level table of contents.
5. `code.theme` is the syntax-highlighting palette; `epub.css` and `html.css` style
   the reflowable editions; `preface.md` is the front-matter preface.
6. `check_pdf_toc.py` and `check_html.py` are the post-build verifiers.

## Design notes

- **Numbering.** Chapters keep the numbers they were written and cross-referenced
  under (roughly 4,500 cross-references key off them), so LaTeX does not renumber
  them. The manuscript's two numbering schemes (foundational chapters and deep
  volumes) share some numbers, so a few chapter labels repeat across volumes; the
  Part/Volume table of contents is the authoritative reading order. A clean editorial
  renumber would require rewriting every cross-reference and is out of scope for a
  compile step.
- **Glyphs.** Emoji, CJK, Greek, and box-drawing characters in verified-output blocks
  render via LuaLaTeX's `luaotfload` font fallback (Noto CJK + Noto Color Emoji).
- **Code.** `fvextra` wraps long lines inside coloured boxes. `breakcode.lua`
  (PDF only) supplies the break opportunities TeX cannot find on its own: inline
  code splits after dots, slashes, commas, and brackets; a `/` joining words or code
  spans in prose becomes breakable; pipe tables without width specs get proportional
  wrapping columns; and unhighlighted `text` blocks are emitted as bare Verbatim lines
  so `breakanywhere` can split a single over-wide token. With `\tolerance=1500` and
  a 3em emergency stretch the full PDF builds with zero overfull boxes; the count is
  audited from `build_full.log` (see Verification) rather than asserted.
- **Fonts.** Noto Sans is installed as a variable font; its bold faces are the
  `wght=700` instance, declared explicitly because fontspec cannot discover them.
- **Table of contents.** The page-number box is widened to 2.6em so four-digit page
  numbers do not overflow.
