"""Listing 43.1 - pathlib: paths as objects, joined with / , parsed by property.

The old way builds paths by string concatenation and os.path.* calls, which is
error-prone (separators, os differences, manual splitting). pathlib.Path makes a
path an object: join with the / operator, read parts by property (.name, .stem,
.suffix, .parent), and do I/O as methods (.read_text, .exists, .glob). This
listing shows the API on a PurePath (no filesystem needed, so the output is
deterministic) plus a small real-filesystem round-trip in a temp dir.
"""

import tempfile
from pathlib import Path, PurePosixPath


def main() -> None:
    print("--- joining: the / operator, not string concatenation ---")
    p = PurePosixPath("/srv/app") / "data" / "report.tar.gz"
    print(f"  built path          : {p}")

    print("--- parsing: parts by property, no manual splitting ---")
    print(f"  .name               : {p.name}")
    print(f"  .stem               : {p.stem}")        # name without the last suffix
    print(f"  .suffix             : {p.suffix}")
    print(f"  .suffixes           : {p.suffixes}")    # all of them
    print(f"  .parent             : {p.parent}")
    print(f"  .parts              : {p.parts}")

    print("--- manipulation: derive new paths without string surgery ---")
    print(f"  with_suffix('.txt') : {p.with_suffix('.txt')}")
    print(f"  with_name('x.log')  : {p.with_name('x.log')}")
    print(f"  relative_to(/srv)   : {p.relative_to('/srv')}")

    print("--- a real round-trip on the filesystem (temp dir) ---")
    d = Path(tempfile.mkdtemp())
    (d / "notes.txt").write_text("hello\n", encoding="utf-8")
    (d / "sub").mkdir()
    (d / "sub" / "more.txt").write_text("world\n", encoding="utf-8")
    txts = sorted(str(q.relative_to(d)) for q in d.rglob("*.txt"))
    print(f"  rglob('*.txt')      : {txts}")
    print(f"  read_text           : {(d / 'notes.txt').read_text(encoding='utf-8')!r}")
    print(f"  exists / is_dir     : {(d / 'sub').exists()} / {(d / 'sub').is_dir()}")


if __name__ == "__main__":
    main()
