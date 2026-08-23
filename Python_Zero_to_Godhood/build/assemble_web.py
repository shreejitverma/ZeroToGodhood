#!/usr/bin/env python3
"""Assemble the book for EPUB/HTML: Markdown dividers instead of raw LaTeX."""
import re
from assemble import ROOT, chapters, preface_text, volume_heading

OUT = ROOT / "build" / "book_web.md"


def main():
    out = [re.sub(r"\{\.unnumbered\}", "", preface_text()).strip() + "\n\n"]
    seen_part = seen_vol = None
    total = 0
    for part, vol, disp, cid, md, text in chapters():
        pnum, ptitle, psub, _ = part
        label, kind, vtitle = vol
        if part is not seen_part:
            sub = f" ({psub})" if psub.strip() else ""
            out.append(f"\n# Part {pnum}: {ptitle}{sub} {{.part}}\n\n")
            seen_part = part
        if vol != seen_vol:
            out.append(f"\n# {volume_heading(label, kind)}: {vtitle} {{.volume}}\n\n")
            seen_vol = vol
        out.append("\n" + text + "\n")
        total += 1
    OUT.write_text("".join(out), encoding="utf-8")
    print(f"Assembled {total} chapters -> {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
