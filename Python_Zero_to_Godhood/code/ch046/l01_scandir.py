"""Listing 46.1 - os.scandir: directory entries that already know their type.

os.listdir returns names only, so to learn whether each is a file or directory
you call os.path.isdir/isfile, a stat() syscall per entry. os.scandir returns
DirEntry objects that carry the type (and often the full stat) cached from the
single directory read, so entry.is_dir()/is_file()/entry.stat() usually answer
WITHOUT another syscall. os.walk is built on scandir and inherits the benefit.
This listing shows the API on a small temp tree (output sorted, so deterministic).
"""

import os
import tempfile
from pathlib import Path


def build_tree() -> str:
    d = Path(tempfile.mkdtemp())
    (d / "a.txt").write_text("a", encoding="utf-8")
    (d / "b.log").write_text("bb", encoding="utf-8")
    (d / "sub").mkdir()
    (d / "sub" / "c.txt").write_text("ccc", encoding="utf-8")
    return str(d)


def main() -> None:
    d = build_tree()

    print("--- scandir: each entry knows its name, type, and (cached) stat ---")
    rows = []
    with os.scandir(d) as it:
        for e in it:
            kind = "dir " if e.is_dir() else "file"     # cached type: no stat syscall
            size = e.stat().st_size if e.is_file() else 0
            rows.append((e.name, kind, size))
    for name, kind, size in sorted(rows):
        print(f"    {kind}  {name:8} size={size}")

    print("--- os.walk: built on scandir, yields (dirpath, dirnames, filenames) ---")
    for dirpath, dirnames, filenames in os.walk(d):
        rel = os.path.relpath(dirpath, d)
        print(f"    {rel:6} dirs={sorted(dirnames)} files={sorted(filenames)}")

    print("--- the type is available without a separate stat() ---")
    with os.scandir(d) as it:
        files = sorted(e.name for e in it if e.is_file())
    print(f"    files only (is_file, cached): {files}")


if __name__ == "__main__":
    main()
