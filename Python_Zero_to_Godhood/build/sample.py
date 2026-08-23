#!/usr/bin/env python3
"""Assemble a small representative SAMPLE for fast design iteration.

Build it with the same options as the full PDF:
  python3 build/sample.py && pandoc build/sample_body.md -o build/sample.pdf <PDF_OPTS from Makefile>
"""
from assemble import latex_block, esc, preface_text, normalise, resolve_chapter, ROOT, MANU

OUT = ROOT / "build" / "sample_body.md"

# (part_title, part_sub, [ (macro, label, title, volume_dir, [chapter_ids]) ])
SAMPLE = [
    ("Origins", "1989 - 1995", [
        ("booktimelinevol", "Volume 1", "Before Python",
         "Part_I_Origins/Vol_01_Before_Python", ["Ch_216"]),
        ("bookdeepvol", "Deep Volume A", "The Object Model",
         "Part_I_Origins/Deep_A_The_Object_Model", ["Ch_105"]),
    ]),
    ("Ergonomics and Typing", "2016 - 2021", [
        ("booktimelinevol", "Volume 14", "Structure",
         "Part_V_Ergonomics_and_Typing/Vol_14_Structure", ["Ch_270"]),
    ]),
    ("The Break", "2008 - 2012", [
        ("bookdeepvol", "Deep Volume D", "Text, Bytes, Encodings",
         "Part_I_Origins/Deep_D_Text_Bytes_Encodings", ["Ch_056"]),
    ]),
]


def main():
    out = [latex_block(r"\frontmatter"), latex_block(r"\maketitlepage"),
           latex_block(r"\makecopyrightpage"), "\n" + preface_text() + "\n",
           latex_block(r"\cleardoublepage\tableofcontents\cleardoublepage\mainmatter")]
    for ptitle, psub, vols in SAMPLE:
        out.append(latex_block(rf"\bookpart{{{esc(ptitle)}}}{{{esc(psub)}}}"))
        for macro, label, vtitle, vdir, chids in vols:
            out.append(latex_block(rf"\{macro}{{{esc(label)}}}{{{esc(vtitle)}}}"))
            for cid in chids:
                md = resolve_chapter(MANU / vdir, cid)
                out.append("\n" + normalise(md.read_text(encoding="utf-8")) + "\n")
    out.append(latex_block(r"\backmatter\makecolophon"))
    OUT.write_text("".join(out), encoding="utf-8")
    print("sample ->", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
