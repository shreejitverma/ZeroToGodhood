#!/usr/bin/env python3
"""Assemble the full ordered book into a single Markdown stream for pandoc.

Reads the canonical structure (build/structure.py), resolves each volume label to
its directory, orders chapters within each volume, and emits build/book_body.md
with raw-LaTeX blocks injected for the front matter, part pages, and volume
dividers. Also writes build/manifest.tsv (for review) and prints stats.
"""
import re
import sys
import pathlib
from structure import PARTS

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANU = ROOT / "manuscript"
OUT = ROOT / "build" / "book_body.md"
MANIFEST = ROOT / "build" / "manifest.tsv"

ROMAN = {"Deep_A": "A", "Deep_B": "B", "Deep_C": "C", "Deep_D": "D", "Deep_E": "E",
         "Deep_F": "F", "Deep_G": "G", "Deep_H": "H", "Deep_I": "I", "Deep_J": "J",
         "Deep_K": "K", "Deep_L": "L", "Deep_M": "M", "Deep_N": "N", "Deep_O": "O",
         "Deep_P": "P", "Deep_Q": "Q", "Deep_R": "R", "Deep_S": "S", "Deep_T": "T",
         "Deep_U": "U", "Deep_V": "V", "Deep_W": "W"}


def find_volume_dir(label):
    hits = [d for d in MANU.rglob(f"{label}_*") if d.is_dir()
            and re.match(rf"{label}_", d.name)]
    # exclude nested chapter dirs (Ch_) accidentally matching
    hits = [d for d in hits if not d.name.startswith("Ch_")]
    if len(hits) != 1:
        sys.exit(f"ERROR: volume {label} resolved to {len(hits)} dirs: {hits}")
    return hits[0]


def chapter_files(voldir):
    """Return chapter (display_num, stable_id, md_path) ordered for reading."""
    rows = []
    for ch in voldir.iterdir():
        if not (ch.is_dir() and ch.name.startswith("Ch_")):
            continue
        md = next(ch.glob("*.md"), None)
        if md is None:
            sys.exit(f"ERROR: no .md in {ch}")
        txt = md.read_text(encoding="utf-8", errors="replace").lstrip("﻿")
        m = re.search(r'^#\s*Chapter\s+(\d+)', txt, re.M)
        disp = int(m.group(1)) if m else 10**6
        sid = re.match(r'(Ch_\d+)', ch.name).group(1)
        rows.append((disp, sid, md))
    return sorted(rows, key=lambda r: (r[0], r[1]))


def latex_block(code):
    return "\n```{=latex}\n" + code.strip("\n") + "\n```\n\n"


def esc(s):
    return s.replace("&", r"\&").replace("_", r"\_").replace("#", r"\#")


def main():
    parts_out = []
    manifest = ["part\tvolume_label\tvolume_title\tchapter_id\tdisplay\tmd"]
    total_ch = 0

    # ---- front matter ----
    parts_out.append(latex_block(r"\frontmatter"))
    parts_out.append(latex_block(r"\maketitlepage"))
    parts_out.append(latex_block(r"\makecopyrightpage"))

    preface = ROOT / "build" / "preface.md"
    if not preface.exists():
        preface = ROOT / "00_Preface.md"
    if preface.exists():
        ptxt = preface.read_text(encoding="utf-8", errors="replace").lstrip("﻿")
        if not re.match(r'^\s*#\s', ptxt):
            ptxt = "# Preface {.unnumbered}\n\n" + ptxt
        parts_out.append("\n" + ptxt.strip() + "\n\n")

    parts_out.append(latex_block(r"\cleardoublepage\tableofcontents\cleardoublepage\mainmatter"))

    # ---- body ----
    for pnum, ptitle, psub, vols in PARTS:
        parts_out.append(latex_block(
            rf"\bookpart{{{esc(ptitle)}}}{{{esc(psub)}}}"))
        for label, kind, vtitle in vols:
            voldir = find_volume_dir(label)
            if kind == "timeline":
                vol_no = str(int(label.split("_")[1]))
                vol_label = f"Volume {vol_no}"
                macro = "booktimelinevol"
            else:
                vol_label = f"Deep Volume {ROMAN[label]}"
                macro = "bookdeepvol"
            parts_out.append(latex_block(
                rf"\{macro}{{{esc(vol_label)}}}{{{esc(vtitle)}}}"))
            for disp, sid, md in chapter_files(voldir):
                txt = md.read_text(encoding="utf-8", errors="replace").lstrip("﻿")
                txt = txt.rstrip() + "\n"
                parts_out.append("\n" + txt + "\n")
                manifest.append(f"{pnum}\t{label}\t{vtitle}\t{sid}\t{disp}\t"
                                f"{md.relative_to(ROOT)}")
                total_ch += 1

    # ---- back matter ----
    parts_out.append(latex_block(r"\backmatter\makecolophon"))

    OUT.write_text("".join(parts_out), encoding="utf-8")
    MANIFEST.write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"Assembled {total_ch} chapters across {len(PARTS)} parts "
          f"-> {OUT.relative_to(ROOT)} ({OUT.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
