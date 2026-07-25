"""Check that output quoted in the prose matches what the listings actually print.

`verify.py` proves the listings still produce their recorded output. This module
proves the *book* quotes that output correctly. They are different failure modes:
a listing can pass verification while the chapter beside it quotes a stale copy
of its output from three edits ago.

A chapter claims an output block like this:

    Verified output (CPython 3.13.5):

    ```text
    ...
    ```

Every such block must appear, contiguously, in one of that chapter's recorded
`expected/<ver>/*.out` files. Blocks may be excerpts: the book routinely quotes
part of a listing's output, so the test is containment, not equality.

Usage:
    python3 -m _harness.crosscheck                 # every chapter
    python3 -m _harness.crosscheck ch18            # one chapter
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent.parent
BOOK = CODE.parent / "manuscript"

# "Verified output (CPython 3.13.5):" followed by a fenced block.
BLOCK = re.compile(
    r"Verified output \(CPython (?P<ver>\d+\.\d+)[^)]*\):\s*\n+```(?:text|pycon)?\n"
    r"(?P<body>.*?)```",
    re.DOTALL,
)

# Must match verify.py exactly; see the note there on why this is address-only.
SCRUB = [(re.compile(r"(?<=at )0x[0-9a-fA-F]{6,}"), "0xADDR"),
         (re.compile(r'(file ")[^"]*(")'), r"\1<path>\2")]


def scrub(text: str) -> str:
    for pat, rep in SCRUB:
        text = pat.sub(rep, text)
    return text


def norm(text: str) -> list[str]:
    """Compare on stripped non-empty lines: indentation in prose is not content."""
    return [ln.rstrip() for ln in scrub(text).splitlines() if ln.strip()]


def contains(haystack: list[str], needle: list[str]) -> bool:
    if not needle:
        return True
    for i in range(len(haystack) - len(needle) + 1):
        if haystack[i:i + len(needle)] == needle:
            return True
    return False


def chapter_dirs(only: str | None) -> list[tuple[str, Path]]:
    out = []
    for d in sorted(CODE.glob("ch*")):
        if not d.is_dir() or not (d / "expected").exists():
            continue
        if only and d.name != only:
            continue
        # Chapter dirs are zero-padded Ch_NNN; pad the code number to match
        # EXACTLY (so ch18 -> Ch_018, not the substring match Ch_118).
        num = re.sub(r"\D", "", d.name).zfill(3)
        hits = sorted(BOOK.rglob(f"Ch_{num}_*/*.md"))
        if hits:
            out.append((d.name, hits[0]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("chapter", nargs="?")
    args = ap.parse_args()

    pairs = chapter_dirs(args.chapter)
    if not pairs:
        print("no chapter/prose pairs found", file=sys.stderr)
        return 1

    ok = bad = 0
    for code_dir, prose in pairs:
        text = prose.read_text(encoding="utf-8")
        pools: dict[str, list[str]] = {}
        for vdir in (CODE / code_dir / "expected").iterdir():
            if vdir.is_dir():
                pools[vdir.name] = [
                    ln for f in sorted(vdir.glob("*.out"))
                    for ln in norm(f.read_text(encoding="utf-8"))
                ]

        blocks = list(BLOCK.finditer(text))
        print(f"{prose.relative_to(BOOK.parent)}: {len(blocks)} quoted output block(s)")
        for m in blocks:
            ver, body = m.group("ver"), norm(m.group("body"))
            line = text[:m.start()].count("\n") + 1
            pool = pools.get(ver)
            if pool is None:
                print(f"  FAIL  line {line}: claims CPython {ver}, "
                      f"no expected/{ver}/ recorded")
                bad += 1
            elif contains(pool, body):
                ok += 1
            else:
                print(f"  FAIL  line {line}: block not found in expected/{ver}/")
                for ln in body[:4]:
                    print(f"          | {ln}")
                bad += 1

    print(f"\n{ok} block(s) matched, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
