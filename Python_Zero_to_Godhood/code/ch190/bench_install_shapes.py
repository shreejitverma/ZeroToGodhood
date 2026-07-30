"""Benchmark 190.1 - what installation shape costs at import and lookup time.

190.1a  importing the same module from an extracted directory, and straight
        from the wheel itself sitting on sys.path (a wheel is a zip, and
        zipimport has been in Python since 2.3). Fresh subprocess per
        measurement, because imports cache (Deep G).

190.1b  the metadata scan: importlib.metadata.distribution(name) and
        entry_points() against a site directory containing 10, 100, and 500
        installed distributions. distribution() is a directory probe;
        entry_points() reads EVERY dist-info on the path - the classic
        startup cost that plugin systems rediscover at scale.

Run under each interpreter separately, as in ch174.
Does its own timing, guarded by __main__. See _harness/bench.py.
"""

import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _harness.bench import provenance  # noqa: E402
from ch190.l01_anatomy_of_an_installed_package import build_wheel  # noqa: E402

FRESH_IMPORT = (
    "import sys, time; sys.path.insert(0, {path!r}); "
    "t0 = time.perf_counter(); import tinypkg; "
    "print((time.perf_counter() - t0) * 1e6)"
)


def fresh_import_us(path, repeat=9):
    runs = []
    for _ in range(repeat):
        out = subprocess.run(
            [sys.executable, "-c", FRESH_IMPORT.format(path=str(path))],
            capture_output=True, text=True, check=True)
        runs.append(float(out.stdout))
    return min(runs)


def make_site(directory: Path, dists: int):
    for i in range(dists):
        info = directory / f"pkg{i:03}-1.0.dist-info"
        info.mkdir(parents=True)
        (info / "METADATA").write_text(
            f"Metadata-Version: 2.4\nName: pkg{i:03}\nVersion: 1.0\n")
        (info / "entry_points.txt").write_text(
            f"[console_scripts]\ntool{i:03} = pkg{i:03}:main\n")


def main():
    print("=== 190.1a  first import, by installation shape ===")
    print(provenance())
    print("method      : fresh subprocess per run, min of 9")
    print()
    with tempfile.TemporaryDirectory() as tmp:
        site = Path(tmp)
        wheel = build_wheel(site)
        extracted = site / "unpacked"
        with zipfile.ZipFile(wheel) as zf:
            zf.extractall(extracted)
        print(f"  from extracted directory : {fresh_import_us(extracted):7,.0f} us")
        print(f"  from the wheel, zipimport: {fresh_import_us(wheel):7,.0f} us")
        print("  both work; extraction is the norm because C extensions, mmap,")
        print("  and __file__-relative data all want real files (Chapter 115)")

    print()
    print("=== 190.1b  metadata lookups vs installed-distribution count ===")
    for dists in (10, 100, 500):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            make_site(site, dists)
            code = (
                "import sys, time, importlib.metadata as im; "
                f"sys.path.insert(0, {str(site)!r}); "
                "t0=time.perf_counter(); im.distribution('pkg000'); "
                "one=(time.perf_counter()-t0)*1e3; "
                "t0=time.perf_counter(); eps=im.entry_points(); "
                "scan=(time.perf_counter()-t0)*1e3; "
                "print(one, scan, len(eps))")
            best = [float("inf"), float("inf"), 0]
            for _ in range(5):
                out = subprocess.run([sys.executable, "-c", code],
                                     capture_output=True, text=True, check=True)
                one, scan, count = out.stdout.split()
                best[0] = min(best[0], float(one))
                best[1] = min(best[1], float(scan))
                best[2] = int(count)
            print(f"  {dists:>4} dists : distribution() {best[0]:6.2f} ms   "
                  f"entry_points() {best[1]:7.2f} ms  ({best[2]} eps)")

    print()
    print("Reading this. The zip shape pays several times the directory shape")
    print("on first import - opening the archive, reading the directory,")
    print("decompressing - which is amortised across many modules in a real")
    print("zipapp but real per-archive; extraction stays the norm for that")
    print("and for C extensions, mmap, and __file__-relative data (Ch 115).")
    print("The scaling story is metadata: distribution(name) probes for one")
    print("directory and stays near-flat, while entry_points() reads EVERY")
    print("dist-info on the path and grows with the environment. Plugin")
    print("systems that call it at startup inherit that scan per process;")
    print("cache it, query one group, and remember that a small environment")
    print("(Chapter 113) is a performance feature, not just hygiene.")


if __name__ == "__main__":
    main()
