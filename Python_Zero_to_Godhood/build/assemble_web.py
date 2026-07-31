#!/usr/bin/env python3
"""Assemble the book for EPUB/HTML: markdown dividers instead of raw LaTeX."""
import re
import pathlib
from structure import PARTS
from assemble import find_volume_dir, chapter_files, ROMAN, ROOT

OUT = ROOT / "build" / "book_web.md"


def main():
    out = []
    # Preface
    pref = ROOT / "build" / "preface.md"
    if not pref.exists():
        pref = ROOT / "00_Preface.md"
    if pref.exists():
        t = pref.read_text(encoding="utf-8").lstrip("﻿")
        t = re.sub(r'\{\.unnumbered\}', '', t)
        out.append(t.strip() + "\n\n")

    for pnum, ptitle, psub, vols in PARTS:
        sub = f" ({psub})" if psub.strip() else ""
        out.append(f"\n# Part {pnum}: {ptitle}{sub} {{.part}}\n\n")
        for label, kind, vtitle in vols:
            voldir = find_volume_dir(label)
            if kind == "timeline":
                vlabel = f"Volume {int(label.split('_')[1])}"
            else:
                vlabel = f"Deep Volume {ROMAN[label]}"
            out.append(f"\n# {vlabel}: {vtitle} {{.volume}}\n\n")
            for disp, sid, md in chapter_files(voldir):
                t = md.read_text(encoding="utf-8").lstrip("﻿").rstrip()
                out.append("\n" + t + "\n\n")

    OUT.write_text("".join(out), encoding="utf-8")
    print("web body ->", OUT.relative_to(ROOT), f"({OUT.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
