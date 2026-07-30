"""Benchmark 192.1 - what a pure-Python build actually spends.

The listing's backend, driven over synthetic source trees of 10, 100, and
1,000 modules (4 KB each): read, hash, deflate, zip. This is the mechanical
floor of every pure-Python build - what remains after a real backend's
discovery and configuration - and it prices the pipeline's stages honestly:
building is hashing plus compression, and both scale with bytes, not with
tooling ceremony.

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
from ch190.l01_anatomy_of_an_installed_package import record_line  # noqa: E402

MODULE = ("def f(x):\n    return x\n" * 170).encode()   # ~4 KB


def build(source_files, out_dir, compress):
    dist_info = "big-1.0.dist-info"
    method = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    record_lines = []
    with zipfile.ZipFile(out_dir / "big-1.0-py3-none-any.whl", "w",
                         compression=method) as zf:
        for name, data in source_files.items():
            zf.writestr(name, data)
            record_lines.append(record_line(name, data))
        meta = b"Metadata-Version: 2.4\nName: big\nVersion: 1.0\n"
        zf.writestr(f"{dist_info}/METADATA", meta)
        record_lines.append(record_line(f"{dist_info}/METADATA", meta))
        zf.writestr(f"{dist_info}/RECORD",
                    "\n".join(record_lines) + f"\n{dist_info}/RECORD,,\n")


def main():
    print("=== 192.1  the mechanical floor of a pure build ===")
    print(provenance())
    print("method      : min of 5 builds per row; ~4 KB per module")
    print()
    for count in (10, 100, 1_000):
        files = {f"big/mod_{i:04}.py": MODULE for i in range(count)}
        files["big/__init__.py"] = b""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for compress, label in ((True, "deflated"), (False, "stored")):
                runs = []
                for _ in range(5):
                    t0 = time.perf_counter()
                    build(files, out, compress)
                    runs.append(time.perf_counter() - t0)
                best = min(runs) * 1000
                if compress:
                    line = f"  {count:>5} modules : {label} {best:7.1f} ms"
                else:
                    line += f"   {label} {best:6.1f} ms"
            print(line)

    print()
    print("Reading this. A thousand-module pure wheel builds in tens of")
    print("milliseconds, and most of that is deflate - the stored column is")
    print("the hash-and-zip floor. When a real 'pip install' of a pure")
    print("package takes seconds, the time is not here: it is resolution")
    print("(Chapter 112), network, and build-environment setup (Chapter 113's")
    print("isolation), which is exactly why lockfiles and wheels (Chapters")
    print("109, 114) attack those stages and not this one.")


if __name__ == "__main__":
    main()
