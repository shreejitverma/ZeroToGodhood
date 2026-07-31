"""Benchmark 197.1 - the capstone: what the safety layers cost, end to end.

One hundred packages installed through Listing 197.1's full pipeline
(discover from index pages, normalise, tag-filter, hash-verify, extract),
against the same hundred extracted bare. The delta is everything this volume
added on top of Chapter 109's unzip: the naming discipline, the
compatibility check, and the trust anchor.

The result is the volume's closing argument in one number: the entire
correctness-and-security apparatus of modern Python packaging costs a few
percent of the extraction it protects - offline. Online, where the wire
dominates everything, it costs nothing at all. There is no performance
excuse for an unverified install, and there never was.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402
from ch197.l01_the_index_and_the_pipeline import build_index, install  # noqa: E402

PACKAGES = 100


def make_pool(pool: Path) -> list[Path]:
    wheels = []
    for i in range(PACKAGES):
        name = f"pkg{i:03}"
        wheel = pool / f"{name}-1.0.0-py3-none-any.whl"
        with zipfile.ZipFile(wheel, "w") as zf:
            zf.writestr(zipfile.ZipInfo(f"{name}.py"),
                        f"NAME = {name!r}\n" * 40)
            zf.writestr(zipfile.ZipInfo(f"{name}-1.0.0.dist-info/METADATA"),
                        f"Metadata-Version: 2.4\nName: {name}\nVersion: 1.0.0\n")
        wheels.append(wheel)
    return wheels


def main():
    print("=== 197.1  100 packages: full pipeline vs bare extraction ===")
    print(provenance())
    print("method      : min of 5 runs per row")
    print()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        pool = work / "pool"
        pool.mkdir()
        wheels = make_pool(pool)
        index_root = work / "simple"
        build_index(index_root, wheels)

        def bare():
            site = Path(tempfile.mkdtemp(dir=work))
            for wheel in wheels:
                with zipfile.ZipFile(wheel) as zf:
                    zf.extractall(site)

        def pipeline():
            site = Path(tempfile.mkdtemp(dir=work))
            for i in range(PACKAGES):
                install(f"PKG{i:03}", index_root, pool, site)

        results = {}
        for label, fn in (("bare extraction", bare),
                          ("full pipeline", pipeline)):
            runs = []
            for _ in range(5):
                t0 = time.perf_counter()
                fn()
                runs.append(time.perf_counter() - t0)
            results[label] = min(runs) * 1000
            print(f"  {label:<16} : {results[label]:7.1f} ms")
        overhead = results["full pipeline"] / results["bare extraction"] - 1
        print(f"  safety overhead  : {overhead:+.0%}")

    print()
    print("Reading this. Discovery, normalisation, tag filtering, and sha256")
    print("verification together add a modest fraction to the unzip they")
    print("guard - offline, against wheels already on disk. Add a network and")
    print("the fraction vanishes into the first round trip. Deep N closes on")
    print("that arithmetic: 109 the artifact, 110 the claim, 111 the build,")
    print("112 the search, 113 the destination, 114 the memo and the anchor,")
    print("115 the hard artifacts, 116 the pipeline - and the whole apparatus")
    print("costs less than the download progress bar. Verify always; lock")
    print("always; prefer wheels; and know which stages run code.")


if __name__ == "__main__":
    main()
