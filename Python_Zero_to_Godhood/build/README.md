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
| `Python_Zero_to_Godhood.pdf`  | 2262-page print-quality PDF (LuaLaTeX + KOMA scrbook) |
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

## How it works

1. `structure.py` transcribes the canonical Part -> Volume -> Chapter order from
   `CANONICAL_TOC.md` (the manuscript directory tree is not a reliable order).
2. `assemble.py` walks that structure, resolves each volume label to its directory,
   orders chapters within each volume, and emits `book_body.md`: one Markdown stream
   with raw-LaTeX blocks injected for the title page, copyright, preface, table of
   contents, part pages, and volume dividers.
3. `assemble_web.py` does the same for EPUB/HTML, emitting Markdown headings for the
   part/volume dividers instead of raw LaTeX.
4. `preamble.tex` is the book design: fonts and glyph fallback, colour palette, page
   geometry, code/output box styling, part/volume/chapter typography, running heads,
   the title/copyright/colophon macros, and the multi-level table of contents.
5. `code.theme` is the syntax-highlighting palette; `epub.css` and `html.css` style
   the reflowable editions; `preface.md` is the front-matter preface.

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
- **Code.** `fvextra` wraps long lines inside coloured boxes; the full 2262-page PDF
  builds with zero overfull boxes.
