"""Benchmark 44.1 - random access: mmap (memory read) vs seek+read (syscall each).

Reading one byte at each of many random offsets in a 64 MB file, two ways. With
seek+read, each access is a seek plus a read() syscall: a user/kernel crossing
per byte. With mmap, the file is mapped once and each access is a memory read;
the OS page-faults a 4 KB page in on first touch and serves the rest from the
page cache, so there is no per-access syscall. For scattered random access the
difference is large.

Within a single interpreter; min is the headline. See _harness/bench.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import measure, report  # noqa: E402

SETUP = """
import mmap, os, tempfile, random
SIZE = 64 * 1024 * 1024
d = tempfile.mkdtemp()
path = os.path.join(d, "big.bin")
with open(path, "wb") as f:
    f.write(os.urandom(SIZE))
random.seed(0)
offsets = [random.randrange(SIZE) for _ in range(50000)]

def via_seek():
    total = 0
    with open(path, "rb") as f:
        for off in offsets:
            f.seek(off)
            total += f.read(1)[0]
    return total

def via_mmap():
    total = 0
    with open(path, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        for off in offsets:
            total += mm[off]
        mm.close()
    return total
"""


def main() -> None:
    results = [
        measure("mmap (memory read)", "via_mmap()", SETUP, number=1),
        measure("seek+read (syscall each)", "via_seek()", SETUP, number=1),
    ]
    report("44.1  50,000 random 1-byte reads in a 64 MB file",
           results, baseline="mmap (memory read)")

    print()
    print("Reading this. seek+read makes a read() syscall per access, a user/")
    print("kernel crossing for every byte. mmap maps the file once and each access")
    print("is a memory read; the OS pages data in on demand and caches it, so there")
    print("is no per-access syscall. For scattered random access over a large file")
    print("mmap is several times faster. Use mmap for random access and for")
    print("sharing a file between processes; use plain buffered reads for")
    print("sequential streaming, where the read-ahead buffer already amortizes the")
    print("syscalls.")


if __name__ == "__main__":
    main()
