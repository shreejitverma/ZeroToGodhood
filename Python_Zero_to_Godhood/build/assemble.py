#!/usr/bin/env python3
"""Assemble the full ordered book into a single Markdown stream for pandoc (PDF).

Reads build/structure.py (the explicit Part -> Volume -> chapter-id order),
resolves every chapter id to exactly one manuscript file, normalises each
chapter on the way through (never in place), and emits build/book_body.md with
raw-LaTeX blocks for the front matter, part pages, and volume dividers.
Also writes build/manifest.tsv for review.

Resolution is strict: a volume directory that does not exist, or a chapter id
that matches 0 or 2+ files, aborts the build.
"""
import re
import sys
import pathlib
from structure import PARTS

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANU = ROOT / "manuscript"
OUT = ROOT / "build" / "book_body.md"
MANIFEST = ROOT / "build" / "manifest.tsv"
BOM = "﻿"


def fail(msg):
    sys.exit(f"ERROR: {msg}")


def resolve_chapter(voldir, cid):
    """Return the single .md file for chapter id `cid` inside `voldir`."""
    dirs = [d for d in voldir.iterdir() if d.is_dir() and d.name.startswith(cid + "_")]
    if len(dirs) != 1:
        fail(f"{cid} resolved to {len(dirs)} directories under {voldir}: {dirs}")
    mds = [m for m in dirs[0].glob("*.md")]
    if len(mds) != 1:
        fail(f"{cid} resolved to {len(mds)} .md files in {dirs[0]}: {mds}")
    return mds[0]


def normalise(text):
    """Per-chapter normalisation applied to the assembled stream only."""
    text = text.lstrip(BOM)
    lines = []
    in_fence = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            # An untagged opening fence gets `text` so the highlighter styles it
            # like every other output block.
            if in_fence and line.strip() == "```":
                line = "```text"
        if not in_fence and line.startswith("#"):
            line = quote_bare_dunders(line)
        lines.append(line.rstrip())
    return "\n".join(lines).rstrip() + "\n"


def quote_bare_dunders(heading):
    """Wrap an unquoted __name__ in a heading in backticks.

    Markdown otherwise reads the underscores as emphasis and the heading, the
    table of contents, and the running head all lose them ("__slots__" became
    "slots"). Existing code spans are left untouched.
    """
    parts = re.split(r"(`[^`]*`)", heading)
    return "".join(p if p.startswith("`") else re.sub(r"(?<!`)(__\w+__)(?!`)", r"`\1`", p)
                   for p in parts)


def check_manuscript_coverage():
    """Fail if the manuscript tree holds anything structure.py does not list.

    Every manuscript/<Part>/<Volume> directory that contains Ch_* directories
    must be named by some volume in PARTS, and every Ch_* directory under any
    such volume must map to a listed chapter id. The _archive tree is ignored.
    """
    listed_dirs = {MANU / vdir for part in PARTS for _, _, _, vdir, _ in part[3]}
    listed_ids = {cid for part in PARTS for vol in part[3] for cid in vol[4]}
    unlisted_dirs = []
    unlisted_chapters = []
    for partdir in sorted(d for d in MANU.iterdir() if d.is_dir() and d.name != "_archive"):
        for voldir in sorted(d for d in partdir.iterdir() if d.is_dir() and d.name != "_archive"):
            chdirs = sorted(d for d in voldir.iterdir()
                            if d.is_dir() and d.name.startswith("Ch_"))
            if not chdirs:
                continue
            if voldir not in listed_dirs:
                unlisted_dirs.append(str(voldir.relative_to(ROOT)))
                continue
            for d in chdirs:
                m = re.match(r"(Ch_\d+)_", d.name)
                if not m or m.group(1) not in listed_ids:
                    unlisted_chapters.append(str(d.relative_to(ROOT)))
    if unlisted_dirs:
        fail(f"volume directories not listed in structure.py: {unlisted_dirs}")
    if unlisted_chapters:
        fail(f"chapter directories not listed in structure.py: {unlisted_chapters}")


def chapters():
    """Yield (part, volume, display_number, chapter_id, path, text) in reading order."""
    for part in PARTS:
        pnum, ptitle, psub, vols = part
        for label, kind, vtitle, vdir, ids in vols:
            voldir = MANU / vdir
            if not voldir.is_dir():
                fail(f"volume {label} directory missing: {voldir}")
            stray = sorted(d.name for d in voldir.iterdir()
                           if d.is_dir() and d.name.startswith("Ch_")
                           and not any(d.name.startswith(c + "_") for c in ids))
            if stray:
                fail(f"volume {label} has chapter dirs not listed in structure.py: {stray}")
            for cid in ids:
                md = resolve_chapter(voldir, cid)
                text = normalise(md.read_text(encoding="utf-8"))
                m = re.match(r"#\s*Chapter\s+(\d+)", text)
                if not m:
                    fail(f"{cid}: first line is not a '# Chapter N' heading ({md})")
                yield part, (label, kind, vtitle), int(m.group(1)), cid, md, text


def volume_heading(label, kind):
    if kind == "timeline":
        return f"Volume {int(label.split('_')[1])}"
    return f"Deep Volume {label.split('_')[1]}"


def latex_block(code):
    return "\n```{=latex}\n" + code.strip("\n") + "\n```\n\n"


def esc(s):
    return s.replace("&", r"\&").replace("_", r"\_").replace("#", r"\#")


def preface_text():
    pref = ROOT / "build" / "preface.md"
    txt = normalise(pref.read_text(encoding="utf-8"))
    if not re.match(r"^\s*#\s", txt):
        txt = "# Preface {.unnumbered}\n\n" + txt
    return txt


def main():
    check_manuscript_coverage()
    out = [latex_block(r"\frontmatter"),
           latex_block(r"\maketitlepage"),
           latex_block(r"\makecopyrightpage"),
           "\n" + preface_text() + "\n",
           latex_block(r"\cleardoublepage\tableofcontents\cleardoublepage\mainmatter")]
    manifest = ["part\tvolume_label\tvolume_title\tchapter_id\tdisplay\tmd"]
    seen_vol = None
    seen_part = None
    total = 0
    for part, vol, disp, cid, md, text in chapters():
        pnum, ptitle, psub, _ = part
        label, kind, vtitle = vol
        if part is not seen_part:
            out.append(latex_block(rf"\bookpart{{{esc(ptitle)}}}{{{esc(psub)}}}"))
            seen_part = part
        if vol != seen_vol:
            macro = "booktimelinevol" if kind == "timeline" else "bookdeepvol"
            out.append(latex_block(
                rf"\{macro}{{{esc(volume_heading(label, kind))}}}{{{esc(vtitle)}}}"))
            seen_vol = vol
        out.append("\n" + text + "\n")
        manifest.append(f"{pnum}\t{label}\t{vtitle}\t{cid}\t{disp}\t{md.relative_to(ROOT)}")
        total += 1
    out.append(latex_block(r"\backmatter\makecolophon"))
    OUT.write_text("".join(out), encoding="utf-8")
    MANIFEST.write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"Assembled {total} chapters across {len(PARTS)} parts "
          f"-> {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
