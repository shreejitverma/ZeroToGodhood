"""Listing 44.1 - mmap: a file as memory, indexed and sliced like bytes.

mmap maps a file's contents into the process address space. After that, the file
IS a bytes-like object: index it, slice it, search it with .find, and (on a
writable map) assign to it to change the file, all as memory operations, with the
OS paging data in on demand and writing it back. No per-access read() syscall,
which is why random access is far cheaper than seek+read (the benchmark). This
listing shows read access, search, and write-through on a small temp file so the
output is deterministic.
"""

import mmap
import os
import tempfile


def main() -> None:
    d = tempfile.mkdtemp()
    path = os.path.join(d, "data.bin")
    with open(path, "wb") as f:
        f.write(b"GET /index.html HTTP/1.1\r\nHost: example.com\r\n\r\n")

    print("--- map the file read-only; it behaves like bytes ---")
    with open(path, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        print(f"  length              : {len(mm)}")
        print(f"  mm[0:3]  (slice)    : {mm[0:3]!r}")     # a memory read, no syscall
        print(f"  mm[4]    (index)    : {mm[4]} ({chr(mm[4])!r})")
        idx = mm.find(b"Host:")                            # search in the mapping
        print(f"  find(b'Host:')      : offset {idx}")
        print(f"  slice at match      : {mm[idx:idx+18]!r}")
        mm.close()

    print("--- map read-write; assigning to a slice writes through to the file ---")
    with open(path, "r+b") as f:
        mm = mmap.mmap(f.fileno(), 0)                      # default: read-write
        mm[0:3] = b"PUT"                                   # overwrite in place
        mm.flush()                                         # ensure it reaches the file
        mm.close()
    print(f"  file after write     : {open(path, 'rb').read(3)!r} (was b'GET')")


if __name__ == "__main__":
    main()
