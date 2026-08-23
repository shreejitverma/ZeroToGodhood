#!/usr/bin/env python3
"""Verify that every chapter in build/structure.py appears in the PDF exactly twice:
once as its table-of-contents entry and once as the chapter opener heading.

Text is extracted with pdftotext and collapsed to single spaces so headings that
wrap across lines still match. Inline code markup is stripped from the source
heading because the PDF renders it without backticks.
"""
import re
import subprocess
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from assemble import chapters  # noqa: E402

pdf = sys.argv[1]
raw = subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True,
                     check=True).stdout
pages = raw.count("\f")
# pdftotext emits a stray "^" before underscores set in the monospace face.
flat = re.sub(r"\s+", " ", raw.replace("^", ""))
bad = []
n_checked = 0
for part, vol, disp, cid, md, body in chapters():
    title = re.match(r"#\s*(Chapter\s+\d+:.*)", body).group(1)
    title = re.sub(r"`([^`]*)`", r"\1", title)
    title = re.sub(r"\s+", " ", title).strip()
    n = flat.count(title)
    n_checked += 1
    if n != 2:
        bad.append((cid, n, title))
print(f"pages={pages} chapters_checked={n_checked} not_exactly_twice={len(bad)}")
for b in bad[:40]:
    print("  ", b)
sys.exit(1 if bad else 0)
