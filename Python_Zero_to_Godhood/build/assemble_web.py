#!/usr/bin/env python3
"""Assemble the book for EPUB/HTML: Markdown dividers instead of raw LaTeX.

Heading hierarchy mirrors the PDF table of contents (part > volume > chapter):
parts are H1, volumes are H2, and every heading inside a chapter is shifted
down two levels, so the chapter opener becomes an H3 (tagged `.chapter`) and
its sections become H4/H5. Preface subsections are shifted below H3 so the
nav tree lists parts, volumes, and chapters only.
"""
import re
from assemble import ROOT, chapters, preface_text, volume_heading

OUT = ROOT / "build" / "book_web.md"

_HEADING = re.compile(r"^#{1,6}\s")
_FENCE = re.compile(r"^(`{3,})")


def shift_headings(text, keep_h1=False):
    """Demote every Markdown heading outside code fences by two levels."""
    out = []
    fence = None
    for line in text.splitlines():
        m = _FENCE.match(line)
        if m:
            if fence is None:
                fence = m.group(1)
            elif line.strip().startswith(fence):
                fence = None
        elif fence is None and _HEADING.match(line):
            if not (keep_h1 and not line.startswith("##")):
                line = "##" + line
        out.append(line)
    return "\n".join(out)


def main():
    preface = re.sub(r"\{\.unnumbered\}", "", preface_text()).strip()
    out = [shift_headings(preface, keep_h1=True) + "\n\n"]
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
            out.append(f"\n## {volume_heading(label, kind)}: {vtitle} {{.volume}}\n\n")
            seen_vol = vol
        body = shift_headings(text.strip())
        body = re.sub(r"^###(\s*Chapter\s+\d+:[^\n]*)", r"###\1 {.chapter}",
                      body, count=1)
        out.append("\n" + body + "\n")
        total += 1
    OUT.write_text("".join(out), encoding="utf-8")
    print(f"Assembled {total} chapters -> {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
