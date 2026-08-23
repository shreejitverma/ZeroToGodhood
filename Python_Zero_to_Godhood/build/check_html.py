#!/usr/bin/env python3
"""Verify the HTML edition: every internal anchor resolves, no external resources.

Usage: python3 build/check_html.py build/Python_Zero_to_Godhood.html
Exit 0 on success; prints counts either way.
"""
import re
import sys
import pathlib

path = pathlib.Path(sys.argv[1])
html = path.read_text(encoding="utf-8")
ids = set(re.findall(r'\sid="([^"]+)"', html))
hrefs = re.findall(r'href="#([^"]+)"', html)
broken = sorted({h for h in hrefs if h not in ids})
external = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
ext_assets = [u for u in external if re.search(r'<(?:link|script|img)[^>]*' + re.escape(u), html)]
print(f"ids={len(ids)} internal_links={len(hrefs)} broken={len(broken)} "
      f"external_assets={len(ext_assets)} size={path.stat().st_size // 1024} KB")
for b in broken[:20]:
    print("  broken:", b)
for u in ext_assets[:20]:
    print("  external asset:", u)
sys.exit(1 if broken or ext_assets else 0)
