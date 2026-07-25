"""Benchmark 46.1 - os.scandir caches entry type; listdir + isdir stats each.

Walking a directory of 5200 entries and classifying each as file or directory.
With os.listdir you get names only, so os.path.isdir does a stat() syscall per
entry. With os.scandir each DirEntry carries the type cached from the single
directory read, so is_dir()/is_file() answer from that cache, no per-entry
syscall. For a type-check walk over a large directory the difference is large.

Directory I/O is OS-bound and noisy; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import os, tempfile
d = tempfile.mkdtemp()
for i in range(5000):
    open(os.path.join(d, f"file{i:05}.txt"), "w").close()
for i in range(200):
    os.mkdir(os.path.join(d, f"dir{i:03}"))

def via_listdir():
    files = dirs = 0
    for name in os.listdir(d):
        if os.path.isdir(os.path.join(d, name)):   # stat() per entry
            dirs += 1
        else:
            files += 1
    return files, dirs

def via_scandir():
    files = dirs = 0
    with os.scandir(d) as it:
        for e in it:
            if e.is_dir():                          # cached type, usually no syscall
                dirs += 1
            else:
                files += 1
    return files, dirs
"""


def main() -> None:
    results = [
        measure("os.scandir (cached type)", "via_scandir()", SETUP, number=1),
        measure("listdir + os.path.isdir", "via_listdir()", SETUP, number=1),
    ]
    report("46.1  classifying 5200 directory entries by type",
           results, baseline="os.scandir (cached type)")

    print()
    print("Reading this. os.listdir gives names only, so os.path.isdir must stat()")
    print("each entry: 5200 syscalls. os.scandir returns DirEntry objects that")
    print("carry the type from the one directory read, so is_dir()/is_file() answer")
    print("from cache with no per-entry syscall. For walking large directories and")
    print("filtering by type, use os.scandir (or os.walk, which is built on it),")
    print("not listdir plus stat. Call entry.stat() only for the entries whose full")
    print("metadata you actually need.")


if __name__ == "__main__":
    main()
