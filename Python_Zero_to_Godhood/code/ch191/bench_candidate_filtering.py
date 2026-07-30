"""Benchmark 191.1 - the filename filter at index scale.

A resolver confronting a popular package sees hundreds of candidate files per
version and thousands per page; the tag filter must reject most of them on
the NAME, before any download (Chapter 109). This benchmark parses and ranks
10,000 synthetic wheel filenames - a large index page - and reports the cost
per candidate and per page.

The absolute numbers are small; the point is the shape they license: filename
filtering is nanoseconds per candidate, which is why installers can afford to
consider everything and why the expensive stages (download, build, resolve -
Chapter 112) are gated behind this free one.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402
from ch191.l01_the_tag_system import acceptable_score, this_interpreter_tag  # noqa: E402

COUNT = 10_000


def synth_filenames():
    pythons = ["py3", "cp310", "cp311", "cp312", "cp313", "cp314", "cp314t"]
    abis = {"py3": "none", "cp311": "abi3"}
    platforms = ["any", "macosx_14_0_arm64", "manylinux_2_28_x86_64",
                 "win_amd64", "musllinux_1_2_aarch64"]
    names = []
    for i in range(COUNT):
        python = pythons[i % len(pythons)]
        abi = abis.get(python, python)
        platform = platforms[i % len(platforms)]
        names.append(f"pkg-{i % 40}.0-{python}-{abi}-{platform}.whl")
    return names


def main():
    names = synth_filenames()
    mine = this_interpreter_tag()

    def run():
        best, best_score = None, 0
        for filename in names:
            stem = filename.removesuffix(".whl")
            _, _, python, abi, _ = stem.split("-")
            score = acceptable_score(python, abi, mine)
            if score > best_score:
                best, best_score = filename, score
        return best

    runs = []
    for _ in range(7):
        t0 = time.perf_counter()
        run()
        runs.append(time.perf_counter() - t0)
    total = min(runs)

    print("=== 191.1  parse + rank 10,000 candidate filenames ===")
    print(provenance())
    print()
    print(f"  whole page : {total * 1e3:6.2f} ms")
    print(f"  per name   : {total / COUNT * 1e9:6,.0f} ns")
    print()
    print("Reading this. A few hundred nanoseconds per candidate: the tag")
    print("filter is effectively free at index scale, which is the design's")
    print("achievement - compatibility decided by string comparison, so an")
    print("installer can reject the world's wheels without downloading any")
    print("of them, and every expensive stage downstream (Chapter 112's")
    print("resolution, Chapter 111's builds) starts from a short list.")


if __name__ == "__main__":
    main()
