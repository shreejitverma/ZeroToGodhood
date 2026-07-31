#!/usr/bin/env python3
"""Assemble a small representative SAMPLE for fast design iteration."""
import pathlib
from assemble import latex_block, esc, ROOT, MANU

OUT = ROOT / "build" / "sample_body.md"


def find(chid):
    hits = [p for p in MANU.rglob(f"{chid}_*/*.md") if "_archive" not in str(p)]
    return sorted(hits)[0]


# (part_title, part_sub, [ (macro,label,title,[chapter_ids]) ])
SAMPLE = [
    ("Origins", "1989 - 1995", [
        ("booktimelinevol", "Volume 1", "Before Python", ["Ch_216"]),
        ("bookdeepvol", "Deep Volume A", "The Object Model", ["Ch_105"]),
    ]),
    ("Ergonomics and Typing", "2016 - 2021", [
        ("booktimelinevol", "Volume 14", "Structure", ["Ch_270"]),
    ]),
    ("The Standard Library", "", [
        ("bookdeepvol", "Deep Volume D", "Text, Bytes, Encodings", ["Ch_252"]),
    ]),
]


def main():
    out = []
    out.append(latex_block(r"\frontmatter"))
    out.append(latex_block(r"\maketitlepage"))
    out.append(latex_block(r"\makecopyrightpage"))
    pref = ROOT / "00_Preface.md"
    if pref.exists():
        import re
        t = pref.read_text(encoding="utf-8").lstrip("﻿")
        t = re.sub(r'^\s*#\s.*$', "# Preface {.unnumbered}", t, count=1, flags=re.M)
        out.append("\n" + t.strip() + "\n\n")
    out.append(latex_block(r"\cleardoublepage\tableofcontents\cleardoublepage\mainmatter"))
    for ptitle, psub, vols in SAMPLE:
        out.append(latex_block(rf"\bookpart{{{esc(ptitle)}}}{{{esc(psub)}}}"))
        for macro, label, vtitle, chids in vols:
            out.append(latex_block(rf"\{macro}{{{esc(label)}}}{{{esc(vtitle)}}}"))
            for chid in chids:
                md = find(chid)
                out.append("\n" + md.read_text(encoding="utf-8").lstrip("﻿").rstrip() + "\n\n")
    out.append(latex_block(r"\backmatter\makecolophon"))
    OUT.write_text("".join(out), encoding="utf-8")
    print("sample ->", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
